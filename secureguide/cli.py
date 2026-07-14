"""Command-line presentation adapter for the SecureGuide profile workflow."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .database import Database
from .blueprints import BlueprintEngine, load_rule_pack
from .errors import SecureGuideError
from .services import SecureGuideService


def emit(value: Any) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SecureGuide enterprise-profile workflow")
    parser.add_argument("--db", default="catalog_work.db", help="SQLite database path")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("migrate", help="apply pending migrations")

    blueprint = commands.add_parser("blueprint-generate")
    blueprint.add_argument("artifact_id")
    blueprint.add_argument("--profile")
    blueprint.add_argument("--rule-pack")

    create = commands.add_parser("profile-create")
    create.add_argument("--id")
    create.add_argument("--name", required=True)
    create.add_argument("--kind")
    create.add_argument("--industry")
    create.add_argument("--country")
    create.add_argument("--description")
    create.add_argument("--activate", action="store_true")

    commands.add_parser("profile-list")
    activate = commands.add_parser("profile-activate")
    activate.add_argument("profile_id")

    search = commands.add_parser("catalog-search")
    search.add_argument("--profile")
    search.add_argument("--query")
    search.add_argument("--locale", default="en")
    search.add_argument("--type")
    search.add_argument("--domain")
    search.add_argument("--sub-domain")
    search.add_argument("--source")
    search.add_argument("--priority")
    search.add_argument("--implementation-status")
    search.add_argument("--verification-status")
    search.add_argument("--exception-status")
    search.add_argument("--tag-type")
    search.add_argument("--tag-value")
    search.add_argument("--selected-only", action="store_true")
    search.add_argument("--limit", type=int, default=100)

    select = commands.add_parser("profile-select")
    select.add_argument("artifact_ids", nargs="+")
    select.add_argument("--profile")
    select.add_argument("--by", required=True)
    select.add_argument("--inclusion-status")
    select.add_argument("--reason")

    template = commands.add_parser("template-apply")
    template.add_argument("template_id")
    template.add_argument("--profile")
    template.add_argument("--by", required=True)
    template.add_argument(
        "--include",
        nargs="+",
        default=["MANDATORY", "RECOMMENDED"],
        choices=["MANDATORY", "RECOMMENDED", "OPTIONAL", "CONDITIONAL"],
    )
    template.add_argument("--note")

    assess = commands.add_parser("assess")
    assess.add_argument("artifact_id")
    assess.add_argument("--profile")
    assess.add_argument("--assessor", required=True)
    assess.add_argument("--implementation-status")
    assess.add_argument("--verification-status")
    assess.add_argument("--effectiveness")
    assess.add_argument("--owner")
    assess.add_argument("--due-date")
    assess.add_argument("--priority")
    assess.add_argument("--review-frequency")
    assess.add_argument("--score", type=float)
    assess.add_argument("--notes")
    assess.add_argument("--comments")

    evidence = commands.add_parser("evidence-add")
    evidence.add_argument("artifact_id")
    evidence.add_argument("--profile")
    evidence.add_argument("--type", required=True)
    evidence.add_argument("--assessment")
    evidence.add_argument("--url")
    evidence.add_argument("--description")
    evidence.add_argument("--title")
    evidence.add_argument("--by", required=True)
    evidence.add_argument("--sha256")
    evidence.add_argument("--mime-type")

    exc_create = commands.add_parser("exception-create")
    exc_create.add_argument("artifact_id")
    exc_create.add_argument("--profile")
    exc_create.add_argument("--status", required=True)
    exc_create.add_argument("--justification", required=True)

    exc_submit = commands.add_parser("exception-submit")
    exc_submit.add_argument("exception_id")
    exc_submit.add_argument("--profile")

    exc_approve = commands.add_parser("exception-approve")
    exc_approve.add_argument("exception_id")
    exc_approve.add_argument("--profile")
    exc_approve.add_argument("--by", required=True)
    exc_approve.add_argument("--approval-date", required=True)
    exc_approve.add_argument("--expiry-date", required=True)
    exc_approve.add_argument("--risk-accepted-by")

    exc_close = commands.add_parser("exception-close")
    exc_close.add_argument("exception_id")
    exc_close.add_argument("--profile")
    exc_close.add_argument("--by", required=True)
    exc_close.add_argument("--note", required=True)
    exc_close.add_argument(
        "--status", default="CLOSED", choices=["CLOSED", "REVOKED", "EXPIRED"]
    )

    dashboard = commands.add_parser("dashboard")
    dashboard.add_argument("--profile")
    dashboard.add_argument("--gap-limit", type=int, default=20)

    report = commands.add_parser("report")
    report.add_argument("--profile")
    report.add_argument("--output")
    return parser


def run(args: argparse.Namespace) -> Any:
    database = Database(args.db)
    if args.command == "migrate":
        return {"database": str(database.path), "applied_migrations": database.migrate()}

    blueprint_engine = None
    if args.command == "blueprint-generate" and args.rule_pack:
        blueprint_engine = BlueprintEngine(load_rule_pack(args.rule_pack))
    service = SecureGuideService(database, blueprint_engine=blueprint_engine)
    if args.command == "blueprint-generate":
        return service.generate_blueprint(args.artifact_id, profile_id=args.profile)
    if args.command == "profile-create":
        return service.create_profile(
            profile_id=args.id,
            name=args.name,
            profile_kind=args.kind,
            industry=args.industry,
            country=args.country,
            description=args.description,
            activate=args.activate,
        )
    if args.command == "profile-list":
        return service.list_profiles()
    if args.command == "profile-activate":
        return service.activate_profile(args.profile_id)
    if args.command == "catalog-search":
        filters = {
            key: value
            for key, value in {
                "type": args.type,
                "primary_domain": args.domain,
                "sub_domain": args.sub_domain,
                "source": args.source,
                "priority": args.priority,
                "implementation_status": args.implementation_status,
                "verification_status": args.verification_status,
                "exception_status": args.exception_status,
                "tag_type": args.tag_type,
                "tag_value": args.tag_value,
            }.items()
            if value is not None
        }
        return service.search_catalog(
            profile_id=args.profile,
            query=args.query,
            locale=args.locale,
            filters=filters,
            selected_only=args.selected_only,
            limit=args.limit,
        )
    if args.command == "profile-select":
        return service.select_artifacts(
            args.artifact_ids,
            profile_id=args.profile,
            selected_by=args.by,
            inclusion_status=args.inclusion_status,
            selection_reason=args.reason,
        )
    if args.command == "template-apply":
        return service.apply_template(
            args.template_id,
            profile_id=args.profile,
            applied_by=args.by,
            include_statuses=args.include,
            note=args.note,
        )
    if args.command == "assess":
        return service.assess_artifact(
            args.artifact_id,
            profile_id=args.profile,
            assessor_name=args.assessor,
            implementation_status=args.implementation_status,
            verification_status=args.verification_status,
            effectiveness=args.effectiveness,
            assigned_owner=args.owner,
            due_date=args.due_date,
            priority_override=args.priority,
            review_frequency_override=args.review_frequency,
            score=args.score,
            notes=args.notes,
            comments=args.comments,
        )
    if args.command == "evidence-add":
        return service.add_evidence(
            args.artifact_id,
            profile_id=args.profile,
            evidence_type=args.type,
            assessment_id=args.assessment,
            evidence_url=args.url,
            description=args.description,
            title=args.title,
            collected_by=args.by,
            content_hash=args.sha256,
            mime_type=args.mime_type,
        )
    if args.command == "exception-create":
        return service.create_exception(
            args.artifact_id,
            profile_id=args.profile,
            exception_status=args.status,
            justification=args.justification,
        )
    if args.command == "exception-submit":
        return service.submit_exception(args.exception_id, profile_id=args.profile)
    if args.command == "exception-approve":
        return service.approve_exception(
            args.exception_id,
            profile_id=args.profile,
            approved_by=args.by,
            approval_date=args.approval_date,
            expiry_date=args.expiry_date,
            risk_accepted_by=args.risk_accepted_by,
        )
    if args.command == "exception-close":
        return service.close_exception(
            args.exception_id,
            profile_id=args.profile,
            closed_by=args.by,
            closure_note=args.note,
            workflow_status=args.status,
        )
    if args.command == "dashboard":
        return service.dashboard(profile_id=args.profile, gap_limit=args.gap_limit)
    if args.command == "report":
        result = service.report(profile_id=args.profile)
        if args.output:
            output = Path(args.output)
            output.write_text(
                json.dumps(result, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )
            return {"output": str(output), "profile_id": result["profile"]["id"]}
        return result
    raise RuntimeError(f"unsupported command: {args.command}")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        result = run(args)
    except SecureGuideError as exc:
        emit({"error": exc.__class__.__name__, "message": str(exc)})
        return 2
    emit(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
