"""Generate the golden read-model contract fixtures.

This is the single source of truth for the ``read-model-v1`` sample payloads.
It seeds a throwaway database, drives one deterministic end-to-end workflow,
renders every :class:`~secureguide.read_models.ReadModel` surface, scrubs the
inevitably-volatile values (generated ids and timestamps) to stable
placeholders, and writes the results under ``tests/fixtures/read_models/``.

``tests/test_read_models.py`` imports :data:`SURFACES`, :func:`scrub`, and
:func:`build_read_model_dataset` from here and re-renders the same surfaces, so
the fixtures and the test can never drift. Regenerate after an intentional
contract change with::

    python -m scripts.dump_read_model_contract
"""

from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path
from typing import Any, Callable

from secureguide import Database, ReadModel, SecureGuideService, apply_migrations
from tests.test_profile_workflow import seed_catalog

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures" / "read_models"

# Values that legitimately change every run and must not appear in a golden.
_GENERATED_ID = re.compile(r"^(ABP|ABA|ABO|ABE|ABF|BPE|TSK|ASM|EVD|EXC|PRA|ORG|PTA|PRF)-[0-9A-F]{8,}$")
_ISO_TS = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(\+\d{2}:\d{2}|Z)?$")
_SQLITE_TS = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")


def scrub(value: Any) -> Any:
    """Replace generated ids and timestamps with placeholders, recursively.

    Human-set ids (``P-HQ``, ``A-IDENTITY``) and set dates (``2026-12-31``) are
    stable inputs and are preserved, so the golden still asserts real structure.
    """
    if isinstance(value, dict):
        return {key: scrub(item) for key, item in value.items()}
    if isinstance(value, list):
        return [scrub(item) for item in value]
    if isinstance(value, str):
        if _GENERATED_ID.match(value):
            return "<id>"
        if _ISO_TS.match(value) or _SQLITE_TS.match(value):
            return "<ts>"
    return value


def normalize(value: Any) -> Any:
    """Order-normalize object collections for a stable golden, recursively.

    Several service views tie-break equal rows by a random generated id (the
    task queue, same-type blueprint evidence, ...), so item *order* varies run
    to run even after scrubbing. Sorting every list of objects by its canonical
    JSON removes that noise while leaving scalar lists (e.g. ``reasonCodes``)
    untouched. Run this *after* :func:`scrub` so placeholders sort stably.
    """
    if isinstance(value, dict):
        return {key: normalize(item) for key, item in value.items()}
    if isinstance(value, list):
        items = [normalize(item) for item in value]
        if items and all(isinstance(item, dict) for item in items):
            items = sorted(items, key=lambda i: json.dumps(i, sort_keys=True, ensure_ascii=False))
        return items
    return value


def finalize(payload: Any) -> Any:
    """Deterministic wire form for goldens: scrub volatile values, then order."""
    return normalize(scrub(payload))


def build_read_model_dataset(service: SecureGuideService) -> dict[str, str]:
    """Drive one deterministic governance workflow across two profiles.

    Returns the identifiers a caller needs to render the parameterized surfaces.
    """
    service.create_profile(
        name="المقر الرئيسي",
        profile_id="P-HQ",
        profile_kind="organization",
        organization_size="LARGE",
        industry="Financial services",
        country="SA",
        target_maturity_level="MANAGED",
        activate=True,
    )
    service.create_profile(name="Cloud Audit", profile_id="P-AUDIT", profile_kind="audit")

    service.select_artifacts(
        ["A-IDENTITY"],
        profile_id="P-HQ",
        selected_by="analyst",
        selection_reason="Critical identity scope",
    )
    service.apply_template("TPL-BASE", profile_id="P-HQ", applied_by="analyst")
    service.select_artifacts(["A-BACKUP"], profile_id="P-HQ", selected_by="analyst")

    service.assess_artifact(
        "A-IDENTITY",
        profile_id="P-HQ",
        assessor_name="auditor",
        implementation_status="STS-FULL",
        verification_status="VER-PASS",
        effectiveness="EFF-HIGH",
        assigned_owner="IAM Team",
        score=100,
        comments="Verified configuration and review records.",
    )
    service.add_evidence(
        "A-IDENTITY",
        profile_id="P-HQ",
        evidence_type="REPORT",
        evidence_url="evidence://iam-review.pdf",
        description="Quarterly access review report",
        title="IAM access review",
        collected_by="auditor",
    )

    deferred = service.create_exception(
        "A-LOGGING",
        profile_id="P-HQ",
        exception_status="EXC-DEFERRED",
        justification="SIEM procurement completes next quarter.",
    )
    service.submit_exception(deferred["id"], profile_id="P-HQ")
    service.approve_exception(
        deferred["id"],
        profile_id="P-HQ",
        approved_by="CISO",
        approval_date="2026-07-14",
        expiry_date="2026-12-31",
    )

    draft = service.create_blueprint_draft(
        "A-IDENTITY",
        profile_id="P-HQ",
        created_by="author",
        change_summary="Initial governed implementation plan",
    )
    service.submit_blueprint(draft["id"], profile_id="P-HQ", submitted_by="author")
    service.approve_blueprint(draft["id"], profile_id="P-HQ", approved_by="approver")
    tasks = service.materialize_blueprint_tasks(
        draft["id"],
        profile_id="P-HQ",
        created_by="approver",
        priority="PRI-HIGH",
        assigned_to="security-team",
    )
    service.update_task(
        tasks["task_ids"][0], profile_id="P-HQ", changed_by="operator", status="IN_PROGRESS"
    )
    return {"profile_id": "P-HQ", "blueprint_id": draft["id"]}


# name -> render a single wire payload from the read model + workflow context.
SURFACES: dict[str, Callable[[ReadModel, dict[str, str]], Any]] = {
    "profiles": lambda rm, ctx: rm.profiles(),
    "active_profile": lambda rm, ctx: rm.active_profile(),
    "dashboard": lambda rm, ctx: rm.dashboard(profile_id=ctx["profile_id"]),
    "catalog": lambda rm, ctx: rm.catalog(profile_id=ctx["profile_id"], locale="en", limit=50),
    "blueprints": lambda rm, ctx: rm.blueprints(profile_id=ctx["profile_id"]),
    "blueprint_detail": lambda rm, ctx: rm.blueprint(ctx["blueprint_id"], profile_id=ctx["profile_id"]),
    "tasks": lambda rm, ctx: rm.tasks(profile_id=ctx["profile_id"]),
    "report": lambda rm, ctx: rm.report(profile_id=ctx["profile_id"]),
}


def render_all() -> dict[str, Any]:
    """Build the dataset in a temp DB and return scrubbed wire payloads by name."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "contract.db"
        apply_migrations(db_path, ROOT / "migrations")
        seed_catalog(db_path)
        service = SecureGuideService(Database(db_path))
        context = build_read_model_dataset(service)
        read_model = ReadModel(service)
        return {name: finalize(render(read_model, context)) for name, render in SURFACES.items()}


def main() -> None:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    for name, payload in render_all().items():
        path = FIXTURES / f"{name}.json"
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
