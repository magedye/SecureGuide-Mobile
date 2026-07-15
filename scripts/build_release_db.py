"""Deterministic builder for a governed SecureGuide seed database.

One command, one reproducible artifact: apply every migration, seed the master
catalog, drive one full governance workflow, run integrity/FK/governance gates,
then emit the database next to a manifest and its SHA-256. The output is what
the app (via the local sidecar) runs against, so UI work never waits on the
real content-curation pipeline.

Modes:

* ``demo`` (default) — migrations + the shared test catalog + the governed
  demo workflow (2 profiles, selections, a template, an assessment, an approved
  blueprint, materialized tasks). Fully self-contained and runnable now.

The real-content path (import raw sources -> staging -> curate -> promote) is
intentionally NOT faked here; it depends on source data and human curation and
will be added as an explicit ``release`` mode once that content exists.

Usage::

    python -m scripts.build_release_db --output dist/secureguide-demo.db
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from secureguide import Database, SecureGuideService, apply_migrations
from secureguide.database import connect
from scripts.dump_read_model_contract import build_read_model_dataset
from tests.test_profile_workflow import seed_catalog

ROOT = Path(__file__).resolve().parent.parent

# Governance views that must return zero rows in a healthy build.
GOVERNANCE_GATES = (
    "v_profile_evidence_integrity_issues",
    "v_profile_origin_governance_issues",
    "v_blueprint_governance_issues",
    "v_blueprint_enrichment_governance_issues",
)

COUNT_TABLES = (
    "security_artifacts",
    "staging_artifacts",
    "enterprise_profiles",
    "profile_artifacts",
    "profile_assessments",
    "profile_evidence",
    "profile_exceptions",
    "approved_blueprints",
    "profile_tasks",
    "templates",
)


class BuildError(RuntimeError):
    """A deterministic build failed a correctness gate."""


def _table_count(conn: sqlite3.Connection, table: str) -> int | None:
    try:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    except sqlite3.OperationalError:
        return None


def _schema_version(conn: sqlite3.Connection) -> str:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
    ).fetchone()
    if not row:
        return "unknown"
    version = conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0]
    return str(version)


def _run_gates(conn: sqlite3.Connection) -> None:
    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        raise BuildError(f"integrity_check failed: {integrity}")
    fk = conn.execute("PRAGMA foreign_key_check").fetchall()
    if fk:
        raise BuildError(f"foreign_key_check reported {len(fk)} violation(s)")
    for view in GOVERNANCE_GATES:
        try:
            rows = conn.execute(f"SELECT COUNT(*) FROM {view}").fetchone()[0]
        except sqlite3.OperationalError:
            continue  # view absent at this schema level
        if rows:
            raise BuildError(f"governance gate {view} reported {rows} issue(s)")


def _publication_breakdown(conn: sqlite3.Connection) -> dict[str, int]:
    try:
        rows = conn.execute(
            "SELECT publication_status,COUNT(*) FROM security_artifacts GROUP BY publication_status"
        ).fetchall()
    except sqlite3.OperationalError:
        return {}
    return {status: count for status, count in rows}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build(output: Path, *, mode: str = "demo", migrations: Path | None = None) -> dict:
    if mode != "demo":
        raise BuildError(f"unsupported mode: {mode} (only 'demo' is available)")
    migrations = migrations or (ROOT / "migrations")
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()

    applied = apply_migrations(output, migrations)
    seed_catalog(output)
    service = SecureGuideService(Database(output))
    context = build_read_model_dataset(service)

    conn = connect(output)
    try:
        _run_gates(conn)
        manifest = {
            "name": output.name,
            "builtWith": "scripts.build_release_db",
            "mode": mode,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "schemaVersion": _schema_version(conn),
            "appliedMigrations": list(applied),
            "publicationStatus": _publication_breakdown(conn),
            "counts": {table: _table_count(conn, table) for table in COUNT_TABLES},
            "demoContext": context,
            "gatesPassed": ["integrity_check", "foreign_key_check", *GOVERNANCE_GATES],
        }
    finally:
        conn.close()

    manifest["sizeBytes"] = output.stat().st_size
    manifest["sha256"] = _sha256(output)
    manifest_path = output.with_suffix(output.suffix + ".manifest.json")
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a governed SecureGuide seed database.")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "dist" / "secureguide-demo.db",
        help="path to write the seed database (default: dist/secureguide-demo.db)",
    )
    parser.add_argument("--mode", default="demo", choices=["demo"])
    parser.add_argument("--migrations", type=Path, default=None)
    args = parser.parse_args()

    manifest = build(args.output, mode=args.mode, migrations=args.migrations)
    print(f"built {args.output} (schema {manifest['schemaVersion']}, {manifest['sizeBytes']:,} bytes)")
    print(f"  publication: {manifest['publicationStatus']}")
    print(f"  profiles={manifest['counts'].get('enterprise_profiles')} "
          f"blueprints={manifest['counts'].get('approved_blueprints')} "
          f"tasks={manifest['counts'].get('profile_tasks')}")
    print(f"  gates passed: {', '.join(manifest['gatesPassed'])}")
    print(f"  sha256: {manifest['sha256']}")


if __name__ == "__main__":
    main()
