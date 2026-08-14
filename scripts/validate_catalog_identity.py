"""Fail when the retired source identity leaks beyond compatibility evidence."""

from __future__ import annotations

import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
RETIRED_TOKEN = "".join(chr(code) for code in (97, 109, 97, 110, 105))
EXCLUDED_PARTS = {
    ".git", ".claude", "old", "_Archive", "outputs", "dist",
    ".dart_tool", "build", "__pycache__", "promotion", "blocks", "results",
}
ALLOWED_FILES = {
    *(f"migrations/{number:03d}_{name}.sql" for number, name in (
        (7, "content_enrichment"),
        (8, "app_entities"),
        (9, "reference_extensions"),
        (10, f"{RETIRED_TOKEN}_alias_subdomains"),
        (11, "sadp_conformance"),
        (12, "threat_and_provenance"),
        (13, "threat_reference"),
        (14, "staging_sadp"),
        (15, "platform_ext"),
    )),
    "migrations/034_neutral_catalog_identity.sql",
    "mobile/lib/core/database/generated_migrations.dart",
    "SecureGuide_Mobile_Docs/Raw_Catalogs/legacy_catalog_v4_recovered.json",
}


def scan(root: Path = ROOT) -> list[str]:
    violations: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if any(part in EXCLUDED_PARTS for part in path.relative_to(root).parts):
            continue
        if RETIRED_TOKEN in relative.lower() and relative not in ALLOWED_FILES:
            violations.append(f"path:{relative}")
            continue
        if relative in ALLOWED_FILES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if RETIRED_TOKEN in text.lower():
            violations.append(f"content:{relative}")
    return violations


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    violations = scan(args.root.resolve())
    if violations:
        raise SystemExit("Retired identity outside compatibility boundary:\n" + "\n".join(violations))
    print("PASS: retired identity is isolated to immutable migration/source compatibility evidence")


if __name__ == "__main__":
    main()
