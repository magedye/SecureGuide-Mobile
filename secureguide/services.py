"""Profile-aware service and state layer for the SecureGuide MVP workflow."""

from __future__ import annotations

import sqlite3
import uuid
from collections import defaultdict
from datetime import date, datetime, timezone
from typing import Any, Callable, Iterable

from scripts import scoring

from .blueprints import BlueprintEngine, ClassificationContext
from .database import Database
from .errors import ActiveProfileRequiredError, NotFoundError, ValidationError
from .repositories import CatalogRepository, ProfileRepository, TemplateRepository


IMPLEMENTATION_STATUSES = {
    "STS-NOT-APPLIED",
    "STS-PARTIAL",
    "STS-FULL",
    "STS-PLANNED",
    "STS-NEEDS-IMPROVEMENT",
}
VERIFICATION_STATUSES = {"VER-NOT-VERIFIED", "VER-PASS", "VER-FAIL"}
EFFECTIVENESS_VALUES = {"EFF-LOW", "EFF-MEDIUM", "EFF-HIGH", "EFF-UNKNOWN"}
PRIORITIES = {"PRI-CRITICAL", "PRI-HIGH", "PRI-MEDIUM", "PRI-LOW"}
REVIEW_FREQUENCIES = {
    "DAILY",
    "WEEKLY",
    "MONTHLY",
    "QUARTERLY",
    "SEMI-ANNUAL",
    "ANNUAL",
    "BIENNIAL",
    "AD-HOC",
    "CONTINUOUS",
}
INCLUSION_STATUSES = {"MANDATORY", "RECOMMENDED", "OPTIONAL", "CONDITIONAL"}
EXCEPTION_STATUSES = {
    "EXC-NOT-APPLICABLE",
    "EXC-RISK-ACCEPTED",
    "EXC-DEFERRED",
    "EXC-UNAVAILABLE",
}
EVIDENCE_TYPES = {
    "DOCUMENT",
    "SCREENSHOT",
    "LOG",
    "REPORT",
    "CONFIG",
    "ATTESTATION",
    "LINK",
    "OTHER",
}

INCLUSION_RANK = {"OPTIONAL": 1, "CONDITIONAL": 2, "RECOMMENDED": 3, "MANDATORY": 4}
PRIORITY_RANK = {"PRI-LOW": 1, "PRI-MEDIUM": 2, "PRI-HIGH": 3, "PRI-CRITICAL": 4}
REVIEW_RANK = {
    "CONTINUOUS": 1,
    "DAILY": 2,
    "WEEKLY": 3,
    "MONTHLY": 4,
    "QUARTERLY": 5,
    "SEMI-ANNUAL": 6,
    "ANNUAL": 7,
    "BIENNIAL": 8,
    "AD-HOC": 9,
}


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex.upper()}"


def _stronger(current: str | None, candidate: str | None, ranks: dict[str, int]) -> str | None:
    if candidate is None:
        return current
    if current is None:
        return candidate
    return candidate if ranks[candidate] > ranks[current] else current


def _more_frequent(current: str | None, candidate: str | None) -> str | None:
    if candidate is None:
        return current
    if current is None:
        return candidate
    return candidate if REVIEW_RANK[candidate] < REVIEW_RANK[current] else current


class EventBus:
    """In-process event boundary for future UI/state subscribers."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable[[dict[str, Any]], None]]] = defaultdict(list)
        self.history: list[dict[str, Any]] = []

    def subscribe(self, event_name: str, callback: Callable[[dict[str, Any]], None]) -> None:
        self._subscribers[event_name].append(callback)

    def publish(self, event_name: str, **payload: Any) -> dict[str, Any]:
        event = {
            "event": event_name,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            **payload,
        }
        self.history.append(event)
        for callback in self._subscribers.get(event_name, []):
            callback(event)
        return event


class SecureGuideService:
    """Application facade implementing the complete enterprise-profile slice."""

    def __init__(
        self,
        database: Database | str,
        event_bus: EventBus | None = None,
        blueprint_engine: BlueprintEngine | None = None,
    ):
        self.db = database if isinstance(database, Database) else Database(database)
        self.events = event_bus or EventBus()
        self.catalog = CatalogRepository()
        self.profiles = ProfileRepository()
        self.templates = TemplateRepository()
        self.blueprints = blueprint_engine

    @staticmethod
    def _translate_integrity(exc: sqlite3.Error) -> ValidationError:
        return ValidationError(str(exc))

    def _profile_id(self, conn: sqlite3.Connection, profile_id: str | None) -> str:
        if profile_id:
            if not self.profiles.get(conn, profile_id):
                raise NotFoundError(f"enterprise profile not found: {profile_id}")
            return profile_id
        active = self.profiles.active(conn)
        if not active:
            raise ActiveProfileRequiredError("select an active enterprise profile first")
        return active["id"]

    def create_profile(
        self,
        *,
        name: str,
        profile_id: str | None = None,
        description: str | None = None,
        profile_kind: str | None = None,
        organization_size: str | None = None,
        industry: str | None = None,
        country: str | None = None,
        target_maturity_level: str | None = None,
        activate: bool = False,
    ) -> dict[str, Any]:
        if not name or not name.strip():
            raise ValidationError("profile name is required")
        values = {
            "id": profile_id or new_id("PRF"),
            "name": name.strip(),
            "description": description,
            "profile_kind": profile_kind,
            "organization_size": organization_size,
            "industry": industry,
            "country": country,
            "target_maturity_level": target_maturity_level,
        }
        try:
            with self.db.transaction() as conn:
                profile = self.profiles.create(conn, values)
                if activate:
                    self.profiles.set_active(conn, profile["id"])
        except sqlite3.Error as exc:
            raise self._translate_integrity(exc) from exc
        self.events.publish("ProfileCreatedEvent", profile_id=profile["id"])
        if activate:
            self.events.publish("ProfileSelectedEvent", profile_id=profile["id"])
        return profile

    def list_profiles(self) -> list[dict[str, Any]]:
        with self.db.read() as conn:
            active = self.profiles.active(conn)
            active_id = active["id"] if active else None
            rows = self.profiles.list(conn)
        for row in rows:
            row["is_active"] = row["id"] == active_id
        return rows

    def activate_profile(self, profile_id: str) -> dict[str, Any]:
        try:
            with self.db.transaction() as conn:
                profile = self.profiles.get(conn, profile_id)
                if not profile:
                    raise NotFoundError(f"enterprise profile not found: {profile_id}")
                self.profiles.set_active(conn, profile_id)
        except sqlite3.Error as exc:
            raise self._translate_integrity(exc) from exc
        self.events.publish("ProfileSelectedEvent", profile_id=profile_id)
        return profile

    def active_profile(self) -> dict[str, Any] | None:
        with self.db.read() as conn:
            return self.profiles.active(conn)

    def generate_blueprint(
        self, artifact_id: str, *, profile_id: str | None = None
    ) -> dict[str, Any]:
        """Generate a transient, non-authoritative blueprint without DB writes."""
        with self.db.read() as conn:
            if profile_id is not None:
                self._profile_id(conn, profile_id)
            artifact = self.catalog.get(conn, artifact_id)
            if not artifact:
                raise NotFoundError(f"security artifact not found: {artifact_id}")
        citation = artifact.get("source_document")
        if artifact.get("source_section"):
            citation = f"{citation}, {artifact['source_section']}"
        engine = self.blueprints or BlueprintEngine()
        blueprint = engine.generate(ClassificationContext(
            artifact_id=artifact["id"],
            artifact_type=artifact["type"],
            primary_domain=artifact["primary_domain"],
            sub_domain=artifact.get("sub_domain"),
            obligation_level=artifact["obligation_level"],
            control_nature=artifact.get("control_nature"),
            control_function=artifact.get("control_function"),
            classification_confidence=artifact.get("classification_confidence"),
            ai_review_status=artifact.get("ai_review_status"),
            source_artifact_id=artifact.get("source_artifact_id") or artifact["id"],
            source_citation=citation,
        ))
        result = blueprint.to_dict()
        self.events.publish(
            "BlueprintGeneratedEvent",
            artifact_id=artifact_id,
            profile_id=profile_id,
            blueprint_id=blueprint.blueprint_id,
            rule_set_hash=blueprint.rule_set_hash,
        )
        return result

    def search_catalog(
        self,
        *,
        profile_id: str | None = None,
        locale: str = "en",
        query: str | None = None,
        filters: dict[str, Any] | None = None,
        selected_only: bool = False,
        publication_status: str | Iterable[str] | None = ("APPROVED", "PUBLISHED"),
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        with self.db.read() as conn:
            if profile_id:
                resolved = self._profile_id(conn, profile_id)
            else:
                active = self.profiles.active(conn)
                resolved = active["id"] if active else None
            return self.catalog.search(
                conn,
                profile_id=resolved,
                locale=locale,
                query=query,
                filters=filters,
                selected_only=selected_only,
                publication_status=publication_status,
                limit=limit,
                offset=offset,
            )

    def select_artifacts(
        self,
        artifact_ids: Iterable[str],
        *,
        profile_id: str | None = None,
        selected_by: str,
        inclusion_status: str | None = None,
        selection_reason: str | None = None,
    ) -> dict[str, Any]:
        ids = list(dict.fromkeys(artifact_ids))
        if not ids:
            raise ValidationError("at least one artifact is required")
        if not selected_by or not selected_by.strip():
            raise ValidationError("selected_by is required")
        if inclusion_status is not None and inclusion_status not in INCLUSION_STATUSES:
            raise ValidationError(f"invalid inclusion_status: {inclusion_status}")
        created = origins_added = 0
        selected_rows: list[str] = []
        try:
            with self.db.transaction() as conn:
                resolved = self._profile_id(conn, profile_id)
                selectable = self.catalog.selectable_ids(conn, ids)
                missing = [artifact_id for artifact_id in ids if artifact_id not in selectable]
                if missing:
                    raise ValidationError(
                        "artifacts are missing, inactive, or not approved: " + ", ".join(missing)
                    )
                for artifact_id in ids:
                    pa, was_created = self.profiles.add_artifact(
                        conn,
                        row_id=new_id("PRA"),
                        profile_id=resolved,
                        artifact_id=artifact_id,
                        inclusion_status=inclusion_status,
                    )
                    if not was_created and inclusion_status is not None:
                        effective_inclusion = _stronger(
                            pa["inclusion_status"], inclusion_status, INCLUSION_RANK
                        )
                        self.profiles.update_inclusion_status(
                            conn, pa["id"], effective_inclusion
                        )
                    created += int(was_created)
                    origin_added = self.profiles.add_origin(
                        conn,
                        {
                            "id": new_id("ORG"),
                            "profile_artifact_id": pa["id"],
                            "origin_type": "MANUAL",
                            "inclusion_status": inclusion_status,
                            "selection_reason": selection_reason,
                            "selected_by": selected_by.strip(),
                        },
                    )
                    origins_added += int(origin_added)
                    selected_rows.append(pa["id"])
        except sqlite3.Error as exc:
            raise self._translate_integrity(exc) from exc
        self.events.publish(
            "ProfileArtifactsSelectedEvent",
            profile_id=resolved,
            profile_artifact_ids=selected_rows,
            created=created,
        )
        return {
            "profile_id": resolved,
            "requested": len(ids),
            "created": created,
            "existing": len(ids) - created,
            "origins_added": origins_added,
            "profile_artifact_ids": selected_rows,
        }

    def apply_template(
        self,
        template_id: str,
        *,
        profile_id: str | None = None,
        applied_by: str,
        include_statuses: Iterable[str] = ("MANDATORY", "RECOMMENDED"),
        note: str | None = None,
    ) -> dict[str, Any]:
        statuses = list(dict.fromkeys(include_statuses))
        invalid = set(statuses) - INCLUSION_STATUSES
        if invalid:
            raise ValidationError(f"invalid template inclusion statuses: {sorted(invalid)}")
        if not applied_by or not applied_by.strip():
            raise ValidationError("applied_by is required")
        created = existing = origins_added = 0
        try:
            with self.db.transaction() as conn:
                resolved = self._profile_id(conn, profile_id)
                template = self.templates.get(conn, template_id)
                if not template:
                    raise NotFoundError(f"template not found: {template_id}")
                items = self.templates.items(conn, template_id, statuses)
                application, application_added = self.profiles.record_template_application(
                    conn,
                    {
                        "id": new_id("PTA"),
                        "profile_id": resolved,
                        "template_id": template_id,
                        "template_version": template["version"],
                        "applied_by": applied_by.strip(),
                        "note": note,
                    },
                )
                self.profiles.set_primary_template_if_empty(conn, resolved, template_id)
                for item in items:
                    pa, was_created = self.profiles.add_artifact(
                        conn,
                        row_id=new_id("PRA"),
                        profile_id=resolved,
                        artifact_id=item["artifact_id"],
                        template_item_id=item["id"],
                        inclusion_status=item["inclusion_status"],
                        template_priority_default=item["priority_override"],
                        template_review_frequency_default=item["review_frequency_override"],
                    )
                    created += int(was_created)
                    existing += int(not was_created)
                    current_inclusion = _stronger(
                        pa["inclusion_status"], item["inclusion_status"], INCLUSION_RANK
                    )
                    current_priority = _stronger(
                        pa["template_priority_default"], item["priority_override"], PRIORITY_RANK
                    )
                    current_review = _more_frequent(
                        pa["template_review_frequency_default"], item["review_frequency_override"]
                    )
                    self.profiles.update_template_defaults(
                        conn,
                        pa["id"],
                        template_item_id=item["id"],
                        inclusion_status=current_inclusion,
                        priority=current_priority,
                        review_frequency=current_review,
                    )
                    origins_added += int(
                        self.profiles.add_origin(
                            conn,
                            {
                                "id": new_id("ORG"),
                                "profile_artifact_id": pa["id"],
                                "origin_type": "TEMPLATE",
                                "template_item_id": item["id"],
                                "profile_template_id": application["id"],
                                "origin_reference": f"{template_id}@{template['version']}",
                                "inclusion_status": item["inclusion_status"],
                                "selection_reason": item["inclusion_reason"],
                                "selected_by": applied_by.strip(),
                            },
                        )
                    )
        except sqlite3.Error as exc:
            raise self._translate_integrity(exc) from exc
        self.events.publish(
            "TemplateAppliedEvent",
            profile_id=resolved,
            template_id=template_id,
            template_version=template["version"],
            created=created,
        )
        return {
            "profile_id": resolved,
            "template_id": template_id,
            "template_version": template["version"],
            "application_recorded": application_added,
            "eligible_items": len(items),
            "created": created,
            "existing": existing,
            "origins_added": origins_added,
        }

    def assess_artifact(
        self,
        artifact_id: str,
        *,
        assessor_name: str,
        profile_id: str | None = None,
        implementation_status: str | None = None,
        verification_status: str | None = None,
        effectiveness: str | None = None,
        current_maturity_level: str | None = None,
        assigned_owner: str | None = None,
        due_date: str | None = None,
        notes: str | None = None,
        priority_override: str | None = None,
        review_frequency_override: str | None = None,
        score: float | None = None,
        comments: str | None = None,
    ) -> dict[str, Any]:
        if not assessor_name or not assessor_name.strip():
            raise ValidationError("assessor_name is required")
        checks = (
            (implementation_status, IMPLEMENTATION_STATUSES, "implementation_status"),
            (verification_status, VERIFICATION_STATUSES, "verification_status"),
            (effectiveness, EFFECTIVENESS_VALUES, "effectiveness"),
            (priority_override, PRIORITIES, "priority_override"),
            (review_frequency_override, REVIEW_FREQUENCIES, "review_frequency_override"),
        )
        for value, allowed, name in checks:
            if value is not None and value not in allowed:
                raise ValidationError(f"invalid {name}: {value}")
        if score is not None and not 0 <= float(score) <= 100:
            raise ValidationError("score must be between 0 and 100")
        changes = {
            key: value
            for key, value in {
                "implementation_status": implementation_status,
                "verification_status": verification_status,
                "effectiveness": effectiveness,
                "current_maturity_level": current_maturity_level,
                "assigned_owner": assigned_owner,
                "due_date": due_date,
                "notes": notes,
                "priority_override": priority_override,
                "review_frequency_override": review_frequency_override,
            }.items()
            if value is not None
        }
        try:
            with self.db.transaction() as conn:
                resolved = self._profile_id(conn, profile_id)
                pa = self.profiles.profile_artifact(conn, resolved, artifact_id=artifact_id)
                if not pa:
                    raise NotFoundError(
                        f"artifact {artifact_id} is not selected in profile {resolved}"
                    )
                self.profiles.update_operational_state(conn, pa["id"], changes)
                current = self.profiles.profile_artifact(conn, resolved, artifact_id=artifact_id)
                assessment = self.profiles.add_assessment(
                    conn,
                    {
                        "id": new_id("ASM"),
                        "profile_artifact_id": pa["id"],
                        "assessor_name": assessor_name.strip(),
                        "score": score,
                        "implementation_status": current["implementation_status"],
                        "verification_status": current["verification_status"],
                        "effectiveness": current["effectiveness"],
                        "exception_status": current["exception_status"],
                        "comments": comments,
                    },
                )
        except sqlite3.Error as exc:
            raise self._translate_integrity(exc) from exc
        self.events.publish(
            "AssessmentUpdatedEvent",
            profile_id=resolved,
            artifact_id=artifact_id,
            assessment_id=assessment["id"],
        )
        return assessment

    def add_evidence(
        self,
        artifact_id: str,
        *,
        evidence_type: str,
        profile_id: str | None = None,
        assessment_id: str | None = None,
        evidence_url: str | None = None,
        description: str | None = None,
        title: str | None = None,
        collected_by: str | None = None,
        content_hash: str | None = None,
        mime_type: str | None = None,
    ) -> dict[str, Any]:
        if evidence_type not in EVIDENCE_TYPES:
            raise ValidationError(f"invalid evidence_type: {evidence_type}")
        if not evidence_url and not description:
            raise ValidationError("evidence_url or description is required")
        if not collected_by or not collected_by.strip():
            raise ValidationError("collected_by is required")
        if content_hash is not None and (
            len(content_hash) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in content_hash)
        ):
            raise ValidationError("content_hash must be a 64-character hexadecimal SHA-256")
        try:
            with self.db.transaction() as conn:
                resolved = self._profile_id(conn, profile_id)
                pa = self.profiles.profile_artifact(conn, resolved, artifact_id=artifact_id)
                if not pa:
                    raise NotFoundError(
                        f"artifact {artifact_id} is not selected in profile {resolved}"
                    )
                evidence = self.profiles.add_evidence(
                    conn,
                    {
                        "id": new_id("EVD"),
                        "profile_artifact_id": pa["id"],
                        "assessment_id": assessment_id,
                        "evidence_type": evidence_type,
                        "evidence_url": evidence_url,
                        "description": description,
                        "title": title,
                        "collected_by": collected_by.strip(),
                        "content_hash": content_hash,
                        "mime_type": mime_type,
                    },
                )
        except sqlite3.Error as exc:
            raise self._translate_integrity(exc) from exc
        self.events.publish(
            "EvidenceAddedEvent",
            profile_id=resolved,
            artifact_id=artifact_id,
            evidence_id=evidence["id"],
        )
        return evidence

    def create_exception(
        self,
        artifact_id: str,
        *,
        exception_status: str,
        justification: str,
        profile_id: str | None = None,
        exception_source: str = "USER",
    ) -> dict[str, Any]:
        if exception_status not in EXCEPTION_STATUSES:
            raise ValidationError(f"invalid exception_status: {exception_status}")
        if not justification or not justification.strip():
            raise ValidationError("exception justification is required")
        try:
            with self.db.transaction() as conn:
                resolved = self._profile_id(conn, profile_id)
                pa = self.profiles.profile_artifact(conn, resolved, artifact_id=artifact_id)
                if not pa:
                    raise NotFoundError(
                        f"artifact {artifact_id} is not selected in profile {resolved}"
                    )
                exception = self.profiles.add_exception(
                    conn,
                    {
                        "id": new_id("EXC"),
                        "profile_artifact_id": pa["id"],
                        "exception_status": exception_status,
                        "justification": justification.strip(),
                        "workflow_status": "DRAFT",
                        "exception_source": exception_source,
                    },
                )
        except sqlite3.Error as exc:
            raise self._translate_integrity(exc) from exc
        self.events.publish(
            "ExceptionCreatedEvent",
            profile_id=resolved,
            artifact_id=artifact_id,
            exception_id=exception["id"],
        )
        return exception

    def _transition_exception(
        self,
        exception_id: str,
        changes: dict[str, Any],
        *,
        profile_id: str | None = None,
    ) -> dict[str, Any]:
        try:
            with self.db.transaction() as conn:
                resolved = self._profile_id(conn, profile_id)
                current = self.profiles.exception_for_profile(conn, resolved, exception_id)
                if not current:
                    raise NotFoundError(
                        f"exception {exception_id} does not belong to profile {resolved}"
                    )
                exception = self.profiles.transition_exception(conn, exception_id, changes)
        except sqlite3.Error as exc:
            raise self._translate_integrity(exc) from exc
        self.events.publish(
            "ExceptionTransitionedEvent",
            profile_id=resolved,
            exception_id=exception_id,
            workflow_status=exception["workflow_status"],
        )
        return exception

    def submit_exception(
        self, exception_id: str, *, profile_id: str | None = None
    ) -> dict[str, Any]:
        return self._transition_exception(
            exception_id, {"workflow_status": "SUBMITTED"}, profile_id=profile_id
        )

    def return_exception_to_draft(
        self, exception_id: str, *, profile_id: str | None = None
    ) -> dict[str, Any]:
        return self._transition_exception(
            exception_id, {"workflow_status": "DRAFT"}, profile_id=profile_id
        )

    def approve_exception(
        self,
        exception_id: str,
        *,
        approved_by: str,
        approval_date: str,
        expiry_date: str,
        profile_id: str | None = None,
        risk_accepted_by: str | None = None,
    ) -> dict[str, Any]:
        if not approved_by:
            raise ValidationError("approved_by is required")
        return self._transition_exception(
            exception_id,
            {
                "workflow_status": "APPROVED",
                "approved_by": approved_by,
                "approval_date": approval_date,
                "expiry_date": expiry_date,
                "risk_accepted_by": risk_accepted_by,
            },
            profile_id=profile_id,
        )

    def close_exception(
        self,
        exception_id: str,
        *,
        closed_by: str,
        closure_note: str,
        workflow_status: str = "CLOSED",
        closed_at: str | None = None,
        profile_id: str | None = None,
    ) -> dict[str, Any]:
        if workflow_status not in {"CLOSED", "REVOKED", "EXPIRED"}:
            raise ValidationError("terminal exception status must be CLOSED, REVOKED, or EXPIRED")
        if not closed_by or not closure_note:
            raise ValidationError("closed_by and closure_note are required")
        return self._transition_exception(
            exception_id,
            {
                "workflow_status": workflow_status,
                "closed_by": closed_by,
                "closed_at": closed_at or datetime.now(timezone.utc).isoformat(),
                "closure_note": closure_note,
            },
            profile_id=profile_id,
        )

    def dashboard(
        self, *, profile_id: str | None = None, gap_limit: int = 20
    ) -> dict[str, Any]:
        with self.db.read() as conn:
            resolved = self._profile_id(conn, profile_id)
            profile = self.profiles.get(conn, resolved)
            controls = scoring.controls_from_catalog(conn, resolved)
            policy = scoring.load_policy(conn)
            settings = {"view_tier": "full", "platforms": []}
            score_result = scoring.score(controls, settings, policy)
            recommendations = scoring.recommend(controls, settings, policy)[:gap_limit]
            counts = self.profiles.dashboard_counts(conn, resolved)
            gaps = self.profiles.gaps(conn, resolved, gap_limit)
            items = self.profiles.operational_items(conn, resolved)
        today = date.today().isoformat()
        review_queue = [
            item
            for item in items
            if item["verification_status"] == "VER-FAIL"
            or item["effectiveness"] == "EFF-LOW"
            or (
                item["due_date"] is not None
                and item["due_date"] < today
                and item["implementation_status"] != "STS-FULL"
            )
        ]
        return {
            "profile": profile,
            "counts": counts,
            "score": score_result,
            "gaps": gaps,
            "recommendations": recommendations,
            "review_queue": review_queue,
        }

    def report(self, *, profile_id: str | None = None) -> dict[str, Any]:
        dashboard = self.dashboard(profile_id=profile_id, gap_limit=200)
        resolved = dashboard["profile"]["id"]
        with self.db.read() as conn:
            items = self.profiles.operational_items(conn, resolved)
            templates = [
                dict(row)
                for row in conn.execute(
                    """SELECT pt.*,t.name AS template_name
                         FROM profile_templates pt JOIN templates t ON t.id=pt.template_id
                        WHERE pt.profile_id=? ORDER BY pt.applied_at,pt.id""",
                    (resolved,),
                ).fetchall()
            ]
        return {
            "report_type": "SECUREGUIDE_PROFILE_OPERATIONAL_REPORT",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "formula_version": dashboard["score"]["formula_version"],
            "profile": dashboard["profile"],
            "templates": templates,
            "summary": {
                "counts": dashboard["counts"],
                "score": dashboard["score"],
                "gap_count": dashboard["counts"]["open_gaps"],
                "review_queue_count": len(dashboard["review_queue"]),
            },
            "items": items,
        }
