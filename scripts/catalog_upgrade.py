"""Apply a verified SecureGuide catalog candidate to an installed database."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from secureguide.catalog_upgrade import CatalogUpgradeError, upgrade_catalog


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installed-db", type=Path, required=True)
    parser.add_argument("--candidate-db", type=Path, required=True)
    parser.add_argument("--actor", default="codex")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        result = upgrade_catalog(args.installed_db, args.candidate_db, actor=args.actor)
    except CatalogUpgradeError as exc:
        print(f"UPGRADE BLOCKED: {exc}", file=sys.stderr)
        return 2
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8", newline="\n")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
