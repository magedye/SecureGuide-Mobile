"""Validate SecureGuide minimum catalog, strict USACM, and source closure."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from secureguide.catalog_validation import DEFAULT_CONTRACT, validate_catalog


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--require-strict", action="store_true")
    args = parser.parse_args(argv)
    report = validate_catalog(args.db, args.contract)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8", newline="\n")
    else:
        print(rendered, end="")
    minimum_ok = report["summary"]["minimumValid"] == report["summary"]["canonicalTotal"]
    strict_ok = report["summary"]["strictConformant"] == report["summary"]["canonicalTotal"]
    required_ok = minimum_ok and report["closure"]["valid"] and report["integrity"]["valid"]
    if args.require_strict:
        required_ok = required_ok and strict_ok
    return 0 if required_ok else 1


if __name__ == "__main__":
    sys.exit(main())
