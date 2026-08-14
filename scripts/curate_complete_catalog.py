"""Build and globally reconcile a complete SecureGuide working catalog."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from secureguide.catalog_curation import (
    CurationInputError,
    backfill_source_provenance,
    curate_complete_catalog,
    prepare_curation_database,
)
from secureguide.catalog_validation import canonical_hash, validate_catalog
from secureguide.database import connect


ROOT = Path(__file__).resolve().parent.parent


def write_json(path: Path, value: dict) -> None:
    value = dict(value)
    value["reportSha256"] = canonical_hash(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-db", type=Path, default=ROOT / "catalog.db")
    parser.add_argument("--db", type=Path, default=ROOT / "dist" / "catalog-curated.db")
    parser.add_argument("--checkpoint", type=Path, default=ROOT / "consolidation" / "curation_checkpoint.json")
    parser.add_argument("--validation", type=Path, default=ROOT / "consolidation" / "catalog_validation.json")
    parser.add_argument("--reuse-working-db", action="store_true")
    args = parser.parse_args(argv)
    try:
        if not args.reuse_working_db:
            prepare_curation_database(args.base_db, args.db)
        conn = connect(args.db)
        try:
            provenance = backfill_source_provenance(conn)
            curation = curate_complete_catalog(conn)
        finally:
            conn.close()
        validation = validate_catalog(args.db)
        checkpoint = {"status": "COMPLETE", "database": args.db.name, "provenance": provenance, **curation}
        write_json(args.checkpoint, checkpoint)
        write_json(args.validation, validation)
        valid = (
            validation["summary"]["minimumValid"] == validation["summary"]["canonicalTotal"]
            and validation["closure"]["valid"] and validation["integrity"]["valid"]
            and set(curation["domains"]) == {f"SD-{number:02d}" for number in range(1, 9)}
        )
        print(json.dumps({"status": "PASS" if valid else "FAIL", **curation}, ensure_ascii=False, indent=2))
        return 0 if valid else 1
    except CurationInputError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
