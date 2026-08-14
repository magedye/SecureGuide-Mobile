"""Classify retired-product references and reject active-current occurrences."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
RETIRED_TOKEN = "".join(chr(code) for code in (97, 109, 97, 110, 105))
RECOVERED_SOURCE = "SecureGuide_Mobile_Docs/Raw_Catalogs/legacy_catalog_v4_recovered.json"
EXCLUDED_PARTS = {
    ".git", ".claude", "old", "_Archive", "outputs", "dist",
    ".dart_tool", "build", "__pycache__", "promotion", "blocks", "results",
}
IMMUTABLE_HISTORY_FILES = {
    *(f"migrations/{number:03d}_{name}.sql" for number, name in (
        (7, "content_enrichment"), (8, "app_entities"), (9, "reference_extensions"),
        (10, f"{RETIRED_TOKEN}_alias_subdomains"), (11, "sadp_conformance"),
        (12, "threat_and_provenance"), (13, "threat_reference"),
        (14, "staging_sadp"), (15, "platform_ext"),
    )),
    "migrations/034_neutral_catalog_identity.sql",
    "mobile/lib/core/database/generated_migrations.dart",
}


def _source_history_violations(path: Path) -> list[str]:
    envelope = json.loads(path.read_text(encoding="utf-8"))
    violations: list[str] = []
    for index, artifact in enumerate(envelope.get("artifacts") or []):
        recovery = artifact.get("recovery_provenance") or {}
        allowed = {
            str(recovery.get("preserved_raw_id") or ""),
            str(recovery.get("staging_id") or ""),
            json.dumps(recovery.get("original_raw_record") or {}, ensure_ascii=False),
        }
        serialised = json.dumps(artifact, ensure_ascii=False)
        if RETIRED_TOKEN not in serialised.lower():
            continue
        residual = serialised
        for value in allowed:
            residual = residual.replace(value, "")
        if RETIRED_TOKEN in residual.lower():
            violations.append(f"active-source:{RECOVERED_SOURCE}:artifacts[{index}]")
    return violations


def scan(root: Path = ROOT) -> list[str]:
    """Return only ACTIVE_CURRENT source-tree occurrences."""

    violations: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if any(part in EXCLUDED_PARTS for part in path.relative_to(root).parts):
            continue
        if relative == RECOVERED_SOURCE:
            violations.extend(_source_history_violations(path))
            continue
        if relative in IMMUTABLE_HISTORY_FILES:
            continue
        if RETIRED_TOKEN in relative.lower():
            violations.append(f"path:{relative}")
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if RETIRED_TOKEN in text.lower():
            violations.append(f"content:{relative}")
    return violations


def audit_database(database: Path) -> dict[str, list[str]]:
    """Classify candidate-database occurrences without hiding active text."""

    result = {"ACTIVE_CURRENT": [], "IMMUTABLE_HISTORY": [], "COMPATIBILITY_ALIAS": []}
    conn = sqlite3.connect(database)
    try:
        tables = [row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )]
        for table in tables:
            columns = conn.execute(f'PRAGMA table_info("{table}")').fetchall()
            for _, column, declared_type, *_ in columns:
                if "TEXT" not in str(declared_type or "").upper():
                    continue
                count = conn.execute(
                    f'''SELECT COUNT(*) FROM "{table}"
                         WHERE lower(coalesce("{column}",'')) LIKE ?''',
                    (f"%{RETIRED_TOKEN}%",),
                ).fetchone()[0]
                if not count:
                    continue
                label = "ACTIVE_CURRENT"
                if table == "schema_migrations":
                    label = "IMMUTABLE_HISTORY"
                elif table == "raw_artifacts":
                    label = "IMMUTABLE_HISTORY"
                elif table == "catalog_artifact_id_aliases" and column == "old_artifact_id":
                    label = "COMPATIBILITY_ALIAS"
                result[label].append(f"{table}.{column}:{count}")
    finally:
        conn.close()
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--database", type=Path)
    args = parser.parse_args()
    violations = scan(args.root.resolve())
    database = audit_database(args.database.resolve()) if args.database else None
    if violations or (database and database["ACTIVE_CURRENT"]):
        raise SystemExit(json.dumps({"source": violations, "database": database}, indent=2))
    print(json.dumps({"source": [], "database": database}, indent=2))


if __name__ == "__main__":
    main()
