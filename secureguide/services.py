"""Profile-aware service and state layer for the SecureGuide MVP workflow."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from collections import defaultdict
from datetime import date, datetime, timezone
from typing import Any, Callable, Iterable

from scripts import scoring

from .blueprints import BlueprintEngine, ClassificationContext, OperationalPatternLibrary
from .database import Database
from .errors import ActiveProfileRequiredError, NotFoundError, ValidationError
from .repositories import (
    BlueprintRepository,
    CatalogRepository,
    ProfileRepository,
    TemplateRepository,
)


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
BLUEPRINT_STATUSES = {"DRAFT", "UNDER_REVIEW", "APPROVED", "SUPERSEDED", "CANCELLED"}
BLUEPRINT_ACTOR_ROLES = {"AUTHOR", "REVIEWER", "APPROVER"}
TASK_STATUSES = {"TODO", "IN_PROGRESS", "BLOCKED", "DONE", "CANCELLED"}

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
        operational_patterns: OperationalPatternLibrary | None = None,
    ):
        self.db = database if isinstance(database, Database) else Database(database)
        self.events = event_bus or EventBus()
        self.catalog = CatalogRepository()
        self.profiles = ProfileRepository()
        self.templates = TemplateRepository()
        self.approved_blueprints = BlueprintRepository()
        self.blueprints = blueprint_engine
        self.operational_patterns = operational_patterns

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

    def search_operational_patterns(
        self,
        *,
        query: str | None = None,
        artifact_type: str | None = None,
        primary_domain: str | None = None,
        sub_domain: str | None = None,
        safety_review_required: bool | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Search curated implementation examples without treating them as mandates."""
        try:
            library = self.operational_patterns or OperationalPatternLibrary()
            results = library.search(
                query=query,
                artifact_type=artifact_type,
                primary_domain=primary_domain,
                sub_domain=sub_domain,
                safety_review_required=safety_review_required,
                limit=limit,
            )
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        return {**library.metadata, "results": results}

    @staticmethod
    def _require_actor(actor: str, actor_role: str, allowed_roles: set[str]) -> str:
        if not actor or not actor.strip():
            raise ValidationError("actor is required")
        if actor_role not in BLUEPRINT_ACTOR_ROLES or actor_role not in allowed_roles:
            raise ValidationError(
                f"actor_role must be one of {sorted(allowed_roles)} for this operation"
            )
        return actor.strip()

    def create_blueprint_draft(
        self,
        artifact_id: str,
        *,
        created_by: str,
        profile_id: str | None = None,
        actor_role: str = "AUTHOR",
        change_summary: str | None = None,
    ) -> dict[str, Any]:
        """Snapshot a transient proposal into a profile-specific human draft."""
        actor = self._require_actor(created_by, actor_role, {"AUTHOR"})
        generated = self.generate_blueprint(artifact_id, profile_id=profile_id)
        stable_payload = dict(generated)
        stable_payload.pop("generatedAt", None)
        payload_hash = hashlib.sha256(
            json.dumps(
                stable_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
        ).hexdigest()
        try:
            with self.db.transaction() as conn:
                resolved = self._profile_id(conn, profile_id)
                pa = self.profiles.profile_artifact(conn, resolved, artifact_id=artifact_id)
                if not pa:
                    raise NotFoundError(
                        f"artifact {artifact_id} is not selected in profile {resolved}"
                    )
                candidate = self.approved_blueprints.candidate_for_profile_artifact(conn, pa["id"])
                if candidate:
                    raise ValidationError(
                        f"blueprint {candidate['id']} is already {candidate['workflow_status']}"
                    )
                latest = self.approved_blueprints.latest_for_profile_artifact(conn, pa["id"])
                version = int(latest["version"]) + 1 if latest else 1
                blueprint_id = new_id("ABP")
                blueprint = self.approved_blueprints.create(conn, {
                    "id": blueprint_id,
                    "profile_id": resolved,
                    "artifact_id": artifact_id,
                    "profile_artifact_id": pa["id"],
                    "version": version,
                    "parent_blueprint_id": latest["id"] if latest else None,
                    "source_blueprint_id": generated["blueprintId"],
                    "source_payload_hash": payload_hash,
                    "engine_version": generated["engineVersion"],
                    "blueprint_version": generated["blueprintVersion"],
                    "rule_set_id": generated["ruleSetId"],
                    "rule_set_version": generated["ruleSetVersion"],
                    "rule_set_hash": generated["ruleSetHash"],
                    "action_plan_type": generated["actionPlanType"],
                    "title": generated["title"],
                    "generation_confidence": generated["confidence"],
                    "generation_requires_review": int(generated["requiresHumanReview"]),
                    "workflow_status": "DRAFT",
                    "created_by": actor,
                    "change_summary": change_summary,
                    "last_actor": actor,
                    "last_actor_role": actor_role,
                })
                rule_versions: dict[str, str] = {}
                for rule in generated["appliedRules"]:
                    rule_versions[rule["ruleId"]] = rule["ruleVersion"]
                    self.approved_blueprints.add_rule(conn, {
                        "blueprint_id": blueprint_id,
                        "rule_id": rule["ruleId"],
                        "rule_version": rule["ruleVersion"],
                        "stage": rule["stage"],
                        "priority": rule["priority"],
                        "rationale": rule["rationale"],
                        "base_confidence": rule["baseConfidence"],
                    })
                for action in generated["actions"]:
                    action_id = new_id("ABA")
                    self.approved_blueprints.add_action(conn, {
                        "id": action_id,
                        "blueprint_id": blueprint_id,
                        "source_action_id": action["id"],
                        "action_code": action["actionCode"],
                        "semantic_key": action["semanticKey"],
                        "title": action["title"],
                        "description": action["description"],
                        "category": action["category"],
                        "phase": action["phase"],
                        "display_order": action["order"],
                        "rationale": action["rationale"],
                        "confidence": action["confidence"],
                        "taskable": int(action["taskable"]),
                        "requires_human_review": int(action["requiresHumanReview"]),
                        "source_artifact_id": action.get("sourceArtifactId"),
                        "source_citation": action.get("sourceCitation"),
                    })
                    for rule_id in action["sourceRuleIds"]:
                        self.approved_blueprints.add_action_rule(conn, {
                            "action_id": action_id,
                            "rule_id": rule_id,
                            "rule_version": rule_versions[rule_id],
                        })
                for output in generated["expectedOutputs"]:
                    output_id = new_id("ABO")
                    self.approved_blueprints.add_output(conn, {
                        "id": output_id,
                        "blueprint_id": blueprint_id,
                        "source_output_id": output["id"],
                        "output_code": output["outputCode"],
                        "semantic_key": output["semanticKey"],
                        "title": output["title"],
                        "description": output["description"],
                        "rationale": output["rationale"],
                    })
                    for rule_id in output["sourceRuleIds"]:
                        self.approved_blueprints.add_output_rule(conn, {
                            "output_id": output_id,
                            "rule_id": rule_id,
                            "rule_version": rule_versions[rule_id],
                        })
                for evidence in generated["evidence"]:
                    evidence_id = new_id("ABE")
                    self.approved_blueprints.add_evidence(conn, {
                        "id": evidence_id,
                        "blueprint_id": blueprint_id,
                        "source_evidence_id": evidence["id"],
                        "evidence_code": evidence["evidenceCode"],
                        "semantic_key": evidence["semanticKey"],
                        "title": evidence["title"],
                        "evidence_type": evidence["evidenceType"],
                        "description": evidence["description"],
                        "rationale": evidence["rationale"],
                        "mandatory": int(evidence["mandatory"]),
                        "confidence": evidence["confidence"],
                        "requires_human_review": int(evidence["requiresHumanReview"]),
                        "source_artifact_id": evidence.get("sourceArtifactId"),
                        "source_citation": evidence.get("sourceCitation"),
                    })
                    for rule_id in evidence["sourceRuleIds"]:
                        self.approved_blueprints.add_evidence_rule(conn, {
                            "evidence_id": evidence_id,
                            "rule_id": rule_id,
                            "rule_version": rule_versions[rule_id],
                        })
                for index, reason in enumerate(generated["reviewReasons"], 1):
                    self.approved_blueprints.add_review_finding(conn, {
                        "id": new_id("ABF"),
                        "blueprint_id": blueprint_id,
                        "finding_type": "REVIEW_REASON",
                        "finding_code": f"REVIEW-{index:03d}",
                        "detail": reason,
                    })
                for event in generated["normalizationEvents"]:
                    self.approved_blueprints.add_review_finding(conn, {
                        "id": new_id("ABF"),
                        "blueprint_id": blueprint_id,
                        "finding_type": "NORMALIZATION",
                        "finding_code": event["normalizationType"],
                        "field_name": event["field"],
                        "input_value": event.get("inputValue"),
                        "canonical_value": event.get("canonicalValue"),
                        "detail": event["reason"],
                        "quality": event.get("quality"),
                    })
                for conflict in generated["conflicts"]:
                    self.approved_blueprints.add_review_finding(conn, {
                        "id": new_id("ABF"),
                        "blueprint_id": blueprint_id,
                        "finding_type": "CONFLICT",
                        "finding_code": "SEMANTIC_EMISSION_CONFLICT",
                        "field_name": conflict.get("field"),
                        "input_value": conflict.get("semanticKey"),
                        "canonical_value": conflict.get("collection"),
                        "detail": "; ".join(
                            str(value) for value in conflict.get("values", [])
                        ) or "conflicting blueprint emissions",
                    })
                detail = self.approved_blueprints.detail(conn, resolved, blueprint_id)
        except sqlite3.Error as exc:
            raise self._translate_integrity(exc) from exc
        self.events.publish(
            "BlueprintDraftCreatedEvent",
            profile_id=resolved,
            artifact_id=artifact_id,
            blueprint_id=blueprint_id,
            version=version,
        )
        return detail

    def enrich_blueprint_from_pattern(
        self,
        blueprint_id: str,
        *,
        pattern_id: str,
        selected_by: str,
        selection_reason: str,
        copied_title_ar: str | None = None,
        copied_text_ar: str | None = None,
        safety_acknowledged: bool = False,
        actor_role: str = "AUTHOR",
        profile_id: str | None = None,
    ) -> dict[str, Any]:
        """Attach a non-authoritative operational pattern to a DRAFT blueprint.

        The enrichment is explicit, reversible, and stores a frozen copy of the
        pattern text (after the author's edits) with the library version and
        sha256, the source pattern identity, and the actor/time/reason. A pattern
        is never turned into a task; it only informs the governed draft snapshot.
        """
        actor = self._require_actor(selected_by, actor_role, {"AUTHOR"})
        if not selection_reason or not selection_reason.strip():
            raise ValidationError("selection_reason is required")
        try:
            library = self.operational_patterns or OperationalPatternLibrary()
            pattern = library.get(pattern_id)
            metadata = library.metadata
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        if not pattern:
            raise NotFoundError(f"operational pattern not found: {pattern_id}")
        safety_required = bool(pattern["safetyReviewRequired"])
        if safety_required and not safety_acknowledged:
            raise ValidationError(
                f"pattern {pattern_id} requires explicit safety acknowledgement: "
                f"{pattern.get('safetyNoteAr')}"
            )
        title = (copied_title_ar if copied_title_ar is not None else pattern["titleAr"]).strip()
        text = (copied_text_ar if copied_text_ar is not None else pattern["sourceTextAr"]).strip()
        if not title or not text:
            raise ValidationError("copied title and text cannot be empty")
        enrichment_id = new_id("BPE")
        try:
            with self.db.transaction() as conn:
                resolved = self._profile_id(conn, profile_id)
                blueprint = self.approved_blueprints.get(conn, resolved, blueprint_id)
                if not blueprint:
                    raise NotFoundError(
                        f"blueprint {blueprint_id} does not belong to profile {resolved}"
                    )
                if blueprint["workflow_status"] != "DRAFT":
                    raise ValidationError(
                        "pattern enrichment is allowed only while the blueprint is DRAFT"
                    )
                if self.approved_blueprints.enrichment_for_pattern(
                    conn, blueprint_id, pattern_id
                ):
                    raise ValidationError(
                        f"pattern {pattern_id} already enriches blueprint {blueprint_id}"
                    )
                self.approved_blueprints.add_pattern_enrichment(conn, {
                    "id": enrichment_id,
                    "blueprint_id": blueprint_id,
                    "source_pattern_id": pattern_id,
                    "pattern_source_row": pattern["sourceRow"],
                    "library_id": metadata["libraryId"],
                    "library_version": metadata["version"],
                    "library_sha256": metadata["sha256"],
                    "recommended_artifact_type": pattern["recommendedArtifactType"],
                    "primary_domain": pattern["primaryDomain"],
                    "sub_domain": pattern["subDomain"],
                    "pattern_priority": pattern["priority"],
                    "copied_title_ar": title,
                    "copied_text_ar": text,
                    "safety_review_required": int(safety_required),
                    "safety_acknowledged": int(bool(safety_acknowledged)) if safety_required else 0,
                    "safety_note_ar": pattern.get("safetyNoteAr") if safety_required else None,
                    "selected_by": actor,
                    "selection_reason": selection_reason.strip(),
                })
                self.approved_blueprints.add_pattern_enrichment_event(conn, {
                    "blueprint_id": blueprint_id,
                    "enrichment_id": enrichment_id,
                    "source_pattern_id": pattern_id,
                    "event_type": "ADDED",
                    "actor": actor,
                    "reason": selection_reason.strip(),
                })
                detail = self.approved_blueprints.detail(conn, resolved, blueprint_id)
        except sqlite3.Error as exc:
            raise self._translate_integrity(exc) from exc
        self.events.publish(
            "BlueprintEnrichedEvent",
            profile_id=resolved,
            blueprint_id=blueprint_id,
            enrichment_id=enrichment_id,
            source_pattern_id=pattern_id,
        )
        return detail

    def remove_blueprint_enrichment(
        self,
        blueprint_id: str,
        enrichment_id: str,
        *,
        removed_by: str,
        removal_reason: str | None = None,
        actor_role: str = "AUTHOR",
        profile_id: str | None = None,
    ) -> dict[str, Any]:
        """Reverse a pattern enrichment while the blueprint is still a DRAFT."""
        actor = self._require_actor(removed_by, actor_role, {"AUTHOR"})
        reason = removal_reason.strip() if removal_reason and removal_reason.strip() else None
        try:
            with self.db.transaction() as conn:
                resolved = self._profile_id(conn, profile_id)
                blueprint = self.approved_blueprints.get(conn, resolved, blueprint_id)
                if not blueprint:
                    raise NotFoundError(
                        f"blueprint {blueprint_id} does not belong to profile {resolved}"
                    )
                if blueprint["workflow_status"] != "DRAFT":
                    raise ValidationError(
                        "pattern enrichment can be removed only while the blueprint is DRAFT"
                    )
                enrichment = self.approved_blueprints.pattern_enrichment(
                    conn, blueprint_id, enrichment_id
                )
                if not enrichment:
                    raise NotFoundError(
                        f"enrichment {enrichment_id} not found on blueprint {blueprint_id}"
                    )
                self.approved_blueprints.add_pattern_enrichment_event(conn, {
                    "blueprint_id": blueprint_id,
                    "enrichment_id": enrichment_id,
                    "source_pattern_id": enrichment["source_pattern_id"],
                    "event_type": "REMOVED",
                    "actor": actor,
                    "reason": reason,
                })
                self.approved_blueprints.remove_pattern_enrichment(conn, enrichment_id)
                detail = self.approved_blueprints.detail(conn, resolved, blueprint_id)
        except sqlite3.Error as exc:
            raise self._translate_integrity(exc) from exc
        self.events.publish(
            "BlueprintEnrichmentRemovedEvent",
            profile_id=resolved,
            blueprint_id=blueprint_id,
            enrichment_id=enrichment_id,
            source_pattern_id=enrichment["source_pattern_id"],
        )
        return detail

    def list_blueprints(
        self,
        *,
        profile_id: str | None = None,
        artifact_id: str | None = None,
        workflow_status: str | None = None,
    ) -> list[dict[str, Any]]:
        if workflow_status is not None and workflow_status not in BLUEPRINT_STATUSES:
            raise ValidationError(f"invalid blueprint workflow_status: {workflow_status}")
        with self.db.read() as conn:
            resolved = self._profile_id(conn, profile_id)
            return self.approved_blueprints.list(
                conn, resolved, artifact_id=artifact_id, workflow_status=workflow_status
            )

    def blueprint_detail(
        self, blueprint_id: str, *, profile_id: str | None = None
    ) -> dict[str, Any]:
        with self.db.read() as conn:
            resolved = self._profile_id(conn, profile_id)
            result = self.approved_blueprints.detail(conn, resolved, blueprint_id)
        if not result:
            raise NotFoundError(f"blueprint {blueprint_id} does not belong to profile {resolved}")
        return result

    def _transition_blueprint(
        self,
        blueprint_id: str,
        changes: dict[str, Any],
        *,
        actor: str,
        actor_role: str,
        allowed_roles: set[str],
        profile_id: str | None,
    ) -> dict[str, Any]:
        clean_actor = self._require_actor(actor, actor_role, allowed_roles)
        changes = {**changes, "last_actor": clean_actor, "last_actor_role": actor_role}
        try:
            with self.db.transaction() as conn:
                resolved = self._profile_id(conn, profile_id)
                current = self.approved_blueprints.get(conn, resolved, blueprint_id)
                if not current:
                    raise NotFoundError(
                        f"blueprint {blueprint_id} does not belong to profile {resolved}"
                    )
                self.approved_blueprints.transition(conn, blueprint_id, changes)
                result = self.approved_blueprints.detail(conn, resolved, blueprint_id)
        except sqlite3.Error as exc:
            raise self._translate_integrity(exc) from exc
        self.events.publish(
            "BlueprintTransitionedEvent",
            profile_id=resolved,
            blueprint_id=blueprint_id,
            workflow_status=result["workflow_status"],
        )
        return result

    def submit_blueprint(
        self,
        blueprint_id: str,
        *,
        submitted_by: str,
        profile_id: str | None = None,
        actor_role: str = "AUTHOR",
    ) -> dict[str, Any]:
        actor = self._require_actor(submitted_by, actor_role, {"AUTHOR"})
        return self._transition_blueprint(
            blueprint_id,
            {
                "workflow_status": "UNDER_REVIEW",
                "submitted_by": actor,
                "submitted_at": datetime.now(timezone.utc).isoformat(),
            },
            actor=actor,
            actor_role=actor_role,
            allowed_roles={"AUTHOR"},
            profile_id=profile_id,
        )

    def return_blueprint_to_draft(
        self,
        blueprint_id: str,
        *,
        reviewed_by: str,
        review_note: str,
        profile_id: str | None = None,
        actor_role: str = "REVIEWER",
    ) -> dict[str, Any]:
        if not review_note or not review_note.strip():
            raise ValidationError("review_note is required")
        return self._transition_blueprint(
            blueprint_id,
            {"workflow_status": "DRAFT", "review_resolution_note": review_note.strip()},
            actor=reviewed_by,
            actor_role=actor_role,
            allowed_roles={"REVIEWER"},
            profile_id=profile_id,
        )

    def approve_blueprint(
        self,
        blueprint_id: str,
        *,
        approved_by: str,
        review_resolution_note: str | None = None,
        profile_id: str | None = None,
        actor_role: str = "APPROVER",
    ) -> dict[str, Any]:
        actor = self._require_actor(approved_by, actor_role, {"APPROVER"})
        now = datetime.now(timezone.utc).isoformat()
        try:
            with self.db.transaction() as conn:
                resolved = self._profile_id(conn, profile_id)
                current = self.approved_blueprints.get(conn, resolved, blueprint_id)
                if not current:
                    raise NotFoundError(
                        f"blueprint {blueprint_id} does not belong to profile {resolved}"
                    )
                if current["workflow_status"] != "UNDER_REVIEW":
                    raise ValidationError("only an UNDER_REVIEW blueprint can be approved")
                if current["generation_requires_review"] and (
                    not review_resolution_note or not review_resolution_note.strip()
                ):
                    raise ValidationError(
                        "review_resolution_note is required for generated review flags"
                    )
                previous = self.approved_blueprints.approved_for_profile_artifact(
                    conn, current["profile_artifact_id"]
                )
                if previous:
                    self.approved_blueprints.transition(conn, previous["id"], {
                        "workflow_status": "SUPERSEDED",
                        "closed_by": actor,
                        "closed_at": now,
                        "last_actor": actor,
                        "last_actor_role": actor_role,
                    })
                self.approved_blueprints.transition(conn, blueprint_id, {
                    "workflow_status": "APPROVED",
                    "approved_by": actor,
                    "approved_at": now,
                    "review_resolution_note": review_resolution_note.strip()
                    if review_resolution_note else None,
                    "last_actor": actor,
                    "last_actor_role": actor_role,
                })
                result = self.approved_blueprints.detail(conn, resolved, blueprint_id)
        except sqlite3.Error as exc:
            raise self._translate_integrity(exc) from exc
        self.events.publish(
            "BlueprintApprovedEvent",
            profile_id=resolved,
            blueprint_id=blueprint_id,
            superseded_blueprint_id=previous["id"] if previous else None,
        )
        return result

    def cancel_blueprint(
        self,
        blueprint_id: str,
        *,
        cancelled_by: str,
        cancellation_note: str,
        profile_id: str | None = None,
        actor_role: str = "AUTHOR",
    ) -> dict[str, Any]:
        if not cancellation_note or not cancellation_note.strip():
            raise ValidationError("cancellation_note is required")
        actor = self._require_actor(
            cancelled_by, actor_role, {"AUTHOR", "REVIEWER"}
        )
        with self.db.read() as conn:
            resolved = self._profile_id(conn, profile_id)
            current = self.approved_blueprints.get(conn, resolved, blueprint_id)
        if not current:
            raise NotFoundError(f"blueprint {blueprint_id} does not belong to profile {resolved}")
        required_role = "AUTHOR" if current["workflow_status"] == "DRAFT" else "REVIEWER"
        return self._transition_blueprint(
            blueprint_id,
            {
                "workflow_status": "CANCELLED",
                "closed_by": actor,
                "closed_at": datetime.now(timezone.utc).isoformat(),
                "change_summary": cancellation_note.strip(),
            },
            actor=actor,
            actor_role=actor_role,
            allowed_roles={required_role},
            profile_id=resolved,
        )

    def materialize_blueprint_tasks(
        self,
        blueprint_id: str,
        *,
        created_by: str,
        profile_id: str | None = None,
        actor_role: str = "APPROVER",
        priority: str | None = None,
        assigned_to: str | None = None,
        due_date: str | None = None,
    ) -> dict[str, Any]:
        actor = self._require_actor(created_by, actor_role, {"APPROVER"})
        if priority is not None and priority not in PRIORITIES:
            raise ValidationError(f"invalid priority: {priority}")
        try:
            with self.db.transaction() as conn:
                resolved = self._profile_id(conn, profile_id)
                blueprint = self.approved_blueprints.get(conn, resolved, blueprint_id)
                if not blueprint:
                    raise NotFoundError(
                        f"blueprint {blueprint_id} does not belong to profile {resolved}"
                    )
                if blueprint["workflow_status"] != "APPROVED":
                    raise ValidationError("tasks can be created only from an APPROVED blueprint")
                created, existing, task_ids = self.approved_blueprints.materialize_tasks(
                    conn,
                    blueprint=blueprint,
                    created_by=actor,
                    priority=priority,
                    assigned_to=assigned_to,
                    due_date=due_date,
                    id_factory=new_id,
                )
                self.approved_blueprints.add_event(conn, {
                    "blueprint_id": blueprint_id,
                    "event_type": "TASKS_MATERIALIZED",
                    "status_from": "APPROVED",
                    "status_to": "APPROVED",
                    "actor": actor,
                    "actor_role": actor_role,
                    "note": f"created={created}; existing={existing}",
                })
        except sqlite3.Error as exc:
            raise self._translate_integrity(exc) from exc
        self.events.publish(
            "BlueprintTasksMaterializedEvent",
            profile_id=resolved,
            blueprint_id=blueprint_id,
            created=created,
            existing=existing,
        )
        return {
            "profile_id": resolved,
            "blueprint_id": blueprint_id,
            "created": created,
            "existing": existing,
            "task_ids": task_ids,
        }

    def list_tasks(
        self, *, profile_id: str | None = None, status: str | None = None
    ) -> list[dict[str, Any]]:
        if status is not None and status not in TASK_STATUSES:
            raise ValidationError(f"invalid task status: {status}")
        with self.db.read() as conn:
            resolved = self._profile_id(conn, profile_id)
            return self.approved_blueprints.tasks(conn, resolved, status)

    def update_task(
        self,
        task_id: str,
        *,
        changed_by: str,
        profile_id: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        assigned_to: str | None = None,
        due_date: str | None = None,
        note: str | None = None,
    ) -> dict[str, Any]:
        if not changed_by or not changed_by.strip():
            raise ValidationError("changed_by is required")
        if status is not None and status not in TASK_STATUSES:
            raise ValidationError(f"invalid task status: {status}")
        if priority is not None and priority not in PRIORITIES:
            raise ValidationError(f"invalid priority: {priority}")
        changes = {
            key: value for key, value in {
                "status": status,
                "priority": priority,
                "assigned_to": assigned_to,
                "due_date": due_date,
                "last_change_note": note,
            }.items() if value is not None
        }
        changes["last_changed_by"] = changed_by.strip()
        if status in {"DONE", "CANCELLED"}:
            changes["closed_by"] = changed_by.strip()
            changes["completed_at"] = datetime.now(timezone.utc).isoformat()
        try:
            with self.db.transaction() as conn:
                resolved = self._profile_id(conn, profile_id)
                current = self.approved_blueprints.task(conn, resolved, task_id)
                if not current:
                    raise NotFoundError(f"task {task_id} does not belong to profile {resolved}")
                self.approved_blueprints.update_task(conn, task_id, changes)
                result = self.approved_blueprints.task(conn, resolved, task_id)
        except sqlite3.Error as exc:
            raise self._translate_integrity(exc) from exc
        self.events.publish(
            "ProfileTaskUpdatedEvent",
            profile_id=resolved,
            task_id=task_id,
            status=result["status"],
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
            approved_blueprints = self.approved_blueprints.list(
                conn, resolved, workflow_status="APPROVED"
            )
            tasks = self.approved_blueprints.tasks(conn, resolved)
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
                "approved_blueprint_count": len(approved_blueprints),
                "task_count": len(tasks),
                "open_task_count": sum(
                    task["status"] not in {"DONE", "CANCELLED"} for task in tasks
                ),
            },
            "items": items,
            "approved_blueprints": approved_blueprints,
            "tasks": tasks,
        }
