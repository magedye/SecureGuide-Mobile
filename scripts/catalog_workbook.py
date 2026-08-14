"""SecureGuide catalog workbook export, validate, plan, and apply CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from secureguide.catalog_workbook import (
    annotate_validation_errors,
    WorkbookConflict,
    WorkbookError,
    apply_workbook_plan,
    export_workbook,
    plan_workbook,
    validate_workbook,
)


def _write(value: dict, output: Path | None) -> None:
    rendered = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8", newline="\n")
    else:
        print(rendered, end="")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    export = sub.add_parser("export")
    export.add_argument("--db", type=Path, required=True)
    export.add_argument("--workbook", type=Path, required=True)
    export.add_argument("--actor", default="codex")
    export.add_argument("--artifact-type")
    export.add_argument("--primary-domain")
    export.add_argument("--sub-domain")
    export.add_argument("--source")
    export.add_argument(
        "--quality-profile", choices=("MINIMUM_VALID", "STRICT_USACM", "ENRICHED")
    )
    export.add_argument("--ai-review-status")
    export.add_argument(
        "--requires-human-review", action=argparse.BooleanOptionalAction, default=None
    )
    export.add_argument("--min-confidence", type=float)
    export.add_argument("--max-confidence", type=float)
    export.add_argument("--publication-status")
    validate = sub.add_parser("validate")
    validate.add_argument("--db", type=Path, required=True)
    validate.add_argument("--workbook", type=Path, required=True)
    validate.add_argument("--output", type=Path)
    validate.add_argument("--annotated-workbook", type=Path)
    plan = sub.add_parser("plan")
    plan.add_argument("--db", type=Path, required=True)
    plan.add_argument("--workbook", type=Path, required=True)
    plan.add_argument("--resolutions", type=Path)
    plan.add_argument("--output", type=Path, required=True)
    apply = sub.add_parser("apply")
    apply.add_argument("--plan", type=Path, required=True)
    apply.add_argument("--actor", default="codex")
    args = parser.parse_args(argv)
    try:
        if args.command == "export":
            filters = {
                "artifact_type": args.artifact_type,
                "primary_domain": args.primary_domain,
                "sub_domain": args.sub_domain,
                "source": args.source,
                "quality_profile": args.quality_profile,
                "ai_review_status": args.ai_review_status,
                "requires_human_review": args.requires_human_review,
                "min_confidence": args.min_confidence,
                "max_confidence": args.max_confidence,
                "publication_status": args.publication_status,
            }
            _write(
                export_workbook(
                    args.db, args.workbook, actor=args.actor, filters=filters
                ),
                None,
            )
        elif args.command == "validate":
            result = validate_workbook(args.workbook, args.db)
            if args.annotated_workbook:
                result["annotatedWorkbook"] = annotate_validation_errors(
                    args.workbook,
                    result["errors"],
                    args.annotated_workbook,
                )
            _write(result, args.output)
            return 0 if result["valid"] else 1
        elif args.command == "plan":
            resolutions = json.loads(args.resolutions.read_text(encoding="utf-8")) if args.resolutions else None
            result = plan_workbook(args.workbook, args.db, resolutions)
            _write(result, args.output)
            return 2 if result["conflicts"] else 0
        else:
            plan_value = json.loads(args.plan.read_text(encoding="utf-8"))
            _write(apply_workbook_plan(plan_value, actor=args.actor), None)
        return 0
    except WorkbookConflict as exc:
        print(f"CONFLICT: {exc}", file=sys.stderr)
        return 2
    except WorkbookError as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
