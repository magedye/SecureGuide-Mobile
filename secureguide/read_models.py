"""Stable read-model / DTO contract over :class:`SecureGuideService`.

This module is a *pure* presentation-facing layer: it contains no SQL, no
business rules, and recomputes nothing. It maps the service's internal dict
shapes — persisted rows are ``snake_case`` (``workflow_status``, ``artifact_id``)
while the blueprint engine emits ``camelCase`` (``blueprintId``, ``ruleSetHash``)
— into ONE stable, versioned, ``camelCase`` wire contract that a Flutter /
local-API client mirrors as Dart data classes.

Design guarantees (mirroring :mod:`secureguide.reporting`):

* **Explicit field selection.** Each DTO reads a named subset via ``dict.get``,
  so adding a database column never leaks to the UI and never raises.
* **Representation normalization only.** The layer coerces SQLite integer flags
  to real booleans and renames keys to ``camelCase``; it never reclassifies,
  rescores, or re-evaluates exception/approval logic.
* **Versioned envelope.** Every top-level payload carries ``contractVersion``
  so the client can detect a contract change without diffing field-by-field.

The internal snake_case service output stays the source of truth; this contract
is the *only* shape screens are allowed to bind to.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Optional

from .services import SecureGuideService

__all__ = [
    "CONTRACT_VERSION",
    "ReadModel",
    "ProfileSummary",
    "ScoreView",
    "DashboardCounts",
    "GapItem",
    "RecommendationItem",
    "OperationalItem",
    "CatalogItem",
    "BlueprintSummary",
    "BlueprintDetail",
    "TaskItem",
]

CONTRACT_VERSION = "read-model-v1"


# --------------------------------------------------------------------------- #
# helpers                                                                      #
# --------------------------------------------------------------------------- #
def _flag(value: Any) -> Optional[bool]:
    """Normalize a SQLite integer flag (0/1/None) to a real boolean or None."""
    if value is None:
        return None
    return bool(value)


def _source_rules(rows: Iterable[dict[str, Any]] | None) -> list[dict[str, Any]]:
    return [
        {"ruleId": row.get("rule_id"), "ruleVersion": row.get("rule_version")}
        for row in (rows or [])
    ]


def _envelope(**body: Any) -> dict[str, Any]:
    """Wrap a wire body with the versioned contract envelope."""
    return {"contractVersion": CONTRACT_VERSION, **body}


# --------------------------------------------------------------------------- #
# leaf / entity DTOs                                                           #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ProfileSummary:
    """Enterprise profile as shown in the selector and dashboard header."""

    id: Optional[str]
    name: Optional[str]
    description: Optional[str]
    profile_kind: Optional[str]
    organization_size: Optional[str]
    industry: Optional[str]
    country: Optional[str]
    target_maturity_level: Optional[str]
    is_active: Optional[bool]

    @classmethod
    def from_row(cls, row: dict[str, Any], *, is_active: Optional[bool] = None) -> "ProfileSummary":
        resolved = is_active if is_active is not None else _flag(row.get("is_active"))
        return cls(
            id=row.get("id"),
            name=row.get("name"),
            description=row.get("description"),
            profile_kind=row.get("profile_kind"),
            organization_size=row.get("organization_size"),
            industry=row.get("industry"),
            country=row.get("country"),
            target_maturity_level=row.get("target_maturity_level"),
            is_active=resolved,
        )

    def to_wire(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "profileKind": self.profile_kind,
            "organizationSize": self.organization_size,
            "industry": self.industry,
            "country": self.country,
            "targetMaturityLevel": self.target_maturity_level,
            "isActive": self.is_active,
        }


@dataclass(frozen=True)
class ScoreView:
    """The auditable ``profile-score-v1`` result, passed through unchanged."""

    raw: dict[str, Any]

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "ScoreView":
        return cls(raw=row or {})

    def to_wire(self) -> dict[str, Any]:
        s = self.raw
        return {
            "overall": s.get("overall"),
            "band": s.get("band"),
            "capped": _flag(s.get("capped")),
            "formulaVersion": s.get("formula_version"),
            "assessmentCoverage": s.get("assessment_coverage"),
            "riskReductionPct": s.get("risk_reduction_pct"),
            "implementationScoreRaw": s.get("implementation_score_raw"),
            "verificationCoverage": s.get("verification_coverage"),
            "verificationAssessmentCoverage": s.get("verification_assessment_coverage"),
            "effectivenessKnown": s.get("effectiveness_known"),
            "assessedControls": s.get("assessed_controls"),
            "totalControls": s.get("total_controls"),
            "remainingCriticalRisk": s.get("remaining_critical_risk"),
            "criticalTotal": s.get("critical_total"),
            "criticalCompliant": s.get("critical_compliant"),
            "criticalAccepted": s.get("critical_accepted"),
            "verifiedPass": s.get("verified_pass"),
            "verifiedFail": s.get("verified_fail"),
            "effectivenessKnownCount": s.get("effectiveness_known_count"),
            "domainScores": s.get("domain_scores") or {},
        }


@dataclass(frozen=True)
class DashboardCounts:
    """Rollup counts from ``v_profile_dashboard``."""

    raw: dict[str, Any]

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "DashboardCounts":
        return cls(raw=row or {})

    def to_wire(self) -> dict[str, Any]:
        c = self.raw
        return {
            "totalItems": c.get("total_items"),
            "applicableItems": c.get("applicable_items"),
            "implementedFull": c.get("implemented_full"),
            "implementedPartial": c.get("implemented_partial"),
            "notApplied": c.get("not_applied"),
            "verifiedPass": c.get("verified_pass"),
            "verifiedFail": c.get("verified_fail"),
            "withException": c.get("with_exception"),
            "openGaps": c.get("open_gaps"),
            "overdueItems": c.get("overdue_items"),
        }


@dataclass(frozen=True)
class GapItem:
    """One open gap from ``v_gap_analysis``."""

    raw: dict[str, Any]

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "GapItem":
        return cls(raw=row or {})

    def to_wire(self) -> dict[str, Any]:
        g = self.raw
        return {
            "artifactId": g.get("artifact_id"),
            "titleEn": g.get("title_en"),
            "primaryDomain": g.get("primary_domain"),
            "subDomain": g.get("sub_domain"),
            "priority": g.get("priority"),
            "implementationStatus": g.get("implementation_status"),
            "verificationStatus": g.get("verification_status"),
            "effectiveness": g.get("effectiveness"),
            "exceptionStatus": g.get("exception_status"),
            "assignedOwner": g.get("assigned_owner"),
            "dueDate": g.get("due_date"),
        }


@dataclass(frozen=True)
class RecommendationItem:
    """One deterministic recommendation from the scoring engine."""

    raw: dict[str, Any]

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "RecommendationItem":
        return cls(raw=row or {})

    def to_wire(self) -> dict[str, Any]:
        r = self.raw
        return {
            "artifactId": r.get("id"),
            "priority": r.get("priority"),
            "dependencyReady": _flag(r.get("dependency_ready")),
            "reasonCodes": list(r.get("reason_codes") or []),
        }


@dataclass(frozen=True)
class OperationalItem:
    """A selected artifact projected with its single-profile operational state.

    Sourced from ``v_profile_operational_items``; also used for the dashboard
    review queue, which the service pre-filters (no recomputation here).
    """

    raw: dict[str, Any]

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "OperationalItem":
        return cls(raw=row or {})

    def to_wire(self) -> dict[str, Any]:
        i = self.raw
        return {
            "profileArtifactId": i.get("profile_artifact_id"),
            "artifactId": i.get("artifact_id"),
            "type": i.get("type"),
            "titleEn": i.get("title_en"),
            "titleAr": i.get("title_ar"),
            "primaryDomain": i.get("primary_domain"),
            "subDomain": i.get("sub_domain"),
            "obligationLevel": i.get("obligation_level"),
            "inclusionStatus": i.get("inclusion_status"),
            "effectivePriority": i.get("effective_priority"),
            "effectiveReviewFrequency": i.get("effective_review_frequency"),
            "implementationStatus": i.get("implementation_status"),
            "verificationStatus": i.get("verification_status"),
            "effectiveness": i.get("effectiveness"),
            "exceptionStatus": i.get("exception_status"),
            "currentMaturityLevel": i.get("current_maturity_level"),
            "assignedOwner": i.get("assigned_owner"),
            "dueDate": i.get("due_date"),
            "evidenceCount": i.get("evidence_count"),
            "originCount": i.get("origin_count"),
            "lastAssessmentAt": i.get("last_assessment_at"),
        }


@dataclass(frozen=True)
class CatalogItem:
    """A Master-Catalog artifact with optional active-profile state overlay."""

    raw: dict[str, Any]

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "CatalogItem":
        return cls(raw=row or {})

    def to_wire(self) -> dict[str, Any]:
        a = self.raw
        return {
            "id": a.get("id"),
            "type": a.get("type"),
            "title": a.get("title"),
            "definitionShort": a.get("definition_short"),
            "primaryDomain": a.get("primary_domain"),
            "subDomain": a.get("sub_domain"),
            "source": a.get("source"),
            "sourceDocument": a.get("source_document"),
            "obligationLevel": a.get("obligation_level"),
            "testability": a.get("testability"),
            "aiReviewStatus": a.get("ai_review_status"),
            "publicationStatus": a.get("publication_status"),
            "effectivePriority": a.get("effective_priority"),
            # Trivial presentation flag: the service already resolved the join.
            "isSelected": a.get("profile_artifact_id") is not None,
            "profileArtifactId": a.get("profile_artifact_id"),
            "inclusionStatus": a.get("inclusion_status"),
            "implementationStatus": a.get("implementation_status"),
            "verificationStatus": a.get("verification_status"),
            "effectiveness": a.get("effectiveness"),
            "exceptionStatus": a.get("exception_status"),
            "assignedOwner": a.get("assigned_owner"),
            "dueDate": a.get("due_date"),
            "evidenceCount": a.get("evidence_count"),
        }


@dataclass(frozen=True)
class BlueprintSummary:
    """A governed blueprint row from ``v_profile_blueprints`` for list views."""

    raw: dict[str, Any]

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "BlueprintSummary":
        return cls(raw=row or {})

    def to_wire(self) -> dict[str, Any]:
        b = self.raw
        return {
            "id": b.get("id"),
            "artifactId": b.get("artifact_id"),
            "artifactTitleEn": b.get("artifact_title_en"),
            "artifactTitleAr": b.get("artifact_title_ar"),
            "title": b.get("title"),
            "version": b.get("version"),
            "workflowStatus": b.get("workflow_status"),
            "actionPlanType": b.get("action_plan_type"),
            "generationConfidence": b.get("generation_confidence"),
            "generationRequiresReview": _flag(b.get("generation_requires_review")),
            "actionCount": b.get("action_count"),
            "evidenceCount": b.get("evidence_count"),
            "taskCount": b.get("task_count"),
            "createdBy": b.get("created_by"),
            "approvedBy": b.get("approved_by"),
            "approvedAt": b.get("approved_at"),
            "updatedAt": b.get("updated_at"),
        }


def _map_applied_rule(r: dict[str, Any]) -> dict[str, Any]:
    return {
        "ruleId": r.get("rule_id"),
        "ruleVersion": r.get("rule_version"),
        "stage": r.get("stage"),
        "priority": r.get("priority"),
        "rationale": r.get("rationale"),
        "baseConfidence": r.get("base_confidence"),
    }


def _map_action(a: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": a.get("id"),
        "actionCode": a.get("action_code"),
        "semanticKey": a.get("semantic_key"),
        "title": a.get("title"),
        "description": a.get("description"),
        "category": a.get("category"),
        "phase": a.get("phase"),
        "displayOrder": a.get("display_order"),
        "rationale": a.get("rationale"),
        "confidence": a.get("confidence"),
        "taskable": _flag(a.get("taskable")),
        "requiresHumanReview": _flag(a.get("requires_human_review")),
        "sourceCitation": a.get("source_citation"),
        "sourceRules": _source_rules(a.get("source_rules")),
    }


def _map_output(o: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": o.get("id"),
        "outputCode": o.get("output_code"),
        "semanticKey": o.get("semantic_key"),
        "title": o.get("title"),
        "description": o.get("description"),
        "rationale": o.get("rationale"),
        "sourceRules": _source_rules(o.get("source_rules")),
    }


def _map_evidence(e: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": e.get("id"),
        "evidenceCode": e.get("evidence_code"),
        "semanticKey": e.get("semantic_key"),
        "title": e.get("title"),
        "evidenceType": e.get("evidence_type"),
        "description": e.get("description"),
        "rationale": e.get("rationale"),
        "mandatory": _flag(e.get("mandatory")),
        "confidence": e.get("confidence"),
        "requiresHumanReview": _flag(e.get("requires_human_review")),
        "sourceCitation": e.get("source_citation"),
        "sourceRules": _source_rules(e.get("source_rules")),
    }


def _map_enrichment(e: dict[str, Any]) -> dict[str, Any]:
    """A non-authoritative operational-pattern enrichment frozen onto a draft."""
    return {
        "id": e.get("id"),
        "sourcePatternId": e.get("source_pattern_id"),
        "recommendedArtifactType": e.get("recommended_artifact_type"),
        "primaryDomain": e.get("primary_domain"),
        "subDomain": e.get("sub_domain"),
        "patternPriority": e.get("pattern_priority"),
        "copiedTitleAr": e.get("copied_title_ar"),
        "copiedTextAr": e.get("copied_text_ar"),
        "safetyReviewRequired": _flag(e.get("safety_review_required")),
        "safetyAcknowledged": _flag(e.get("safety_acknowledged")),
        "safetyNoteAr": e.get("safety_note_ar"),
        "libraryVersion": e.get("library_version"),
        "selectedBy": e.get("selected_by"),
        "selectionReason": e.get("selection_reason"),
        "selectedAt": e.get("selected_at"),
    }


def _map_review_finding(f: dict[str, Any]) -> dict[str, Any]:
    return {
        "findingType": f.get("finding_type"),
        "findingCode": f.get("finding_code"),
        "fieldName": f.get("field_name"),
        "inputValue": f.get("input_value"),
        "canonicalValue": f.get("canonical_value"),
        "detail": f.get("detail"),
        "quality": f.get("quality"),
    }


@dataclass(frozen=True)
class BlueprintDetail:
    """Full governed-blueprint snapshot with its nested collections."""

    raw: dict[str, Any]

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "BlueprintDetail":
        return cls(raw=row or {})

    def to_wire(self) -> dict[str, Any]:
        # Built from the raw ``approved_blueprints`` row plus its nested
        # collections. The list-only rollups (artifact titles, action/evidence/
        # task counts) live on the ``blueprints`` surface, not here — detail
        # carries the full snapshot, and counts are the nested array lengths.
        b = self.raw
        return {
            "id": b.get("id"),
            "artifactId": b.get("artifact_id"),
            "title": b.get("title"),
            "version": b.get("version"),
            "workflowStatus": b.get("workflow_status"),
            "actionPlanType": b.get("action_plan_type"),
            "generationConfidence": b.get("generation_confidence"),
            "generationRequiresReview": _flag(b.get("generation_requires_review")),
            "profileId": b.get("profile_id"),
            "profileArtifactId": b.get("profile_artifact_id"),
            "parentBlueprintId": b.get("parent_blueprint_id"),
            "ruleSetId": b.get("rule_set_id"),
            "ruleSetVersion": b.get("rule_set_version"),
            "ruleSetHash": b.get("rule_set_hash"),
            "engineVersion": b.get("engine_version"),
            "changeSummary": b.get("change_summary"),
            "reviewResolutionNote": b.get("review_resolution_note"),
            "createdBy": b.get("created_by"),
            "submittedBy": b.get("submitted_by"),
            "submittedAt": b.get("submitted_at"),
            "approvedBy": b.get("approved_by"),
            "approvedAt": b.get("approved_at"),
            "updatedAt": b.get("updated_at"),
            "appliedRules": [_map_applied_rule(r) for r in b.get("applied_rules") or []],
            "actions": [_map_action(a) for a in b.get("actions") or []],
            "expectedOutputs": [_map_output(o) for o in b.get("expected_outputs") or []],
            "evidence": [_map_evidence(e) for e in b.get("evidence") or []],
            "patternEnrichments": [
                _map_enrichment(e) for e in b.get("pattern_enrichments") or []
            ],
            "reviewFindings": [
                _map_review_finding(f) for f in b.get("review_findings") or []
            ],
        }


@dataclass(frozen=True)
class TaskItem:
    """An operational task from ``v_profile_task_queue``."""

    raw: dict[str, Any]

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "TaskItem":
        return cls(raw=row or {})

    def to_wire(self) -> dict[str, Any]:
        t = self.raw
        return {
            "id": t.get("id"),
            "title": t.get("title"),
            "description": t.get("description"),
            "status": t.get("status"),
            "priority": t.get("priority"),
            "assignedTo": t.get("assigned_to"),
            "dueDate": t.get("due_date"),
            "artifactId": t.get("artifact_id"),
            "artifactTitleEn": t.get("artifact_title_en"),
            "primaryDomain": t.get("primary_domain"),
            "subDomain": t.get("sub_domain"),
            "blueprintId": t.get("blueprint_id"),
            "blueprintVersion": t.get("blueprint_version_number"),
            "actionPlanType": t.get("action_plan_type"),
            "sourceSemanticKey": t.get("source_semantic_key"),
            "lastChangedBy": t.get("last_changed_by"),
            "lastChangeNote": t.get("last_change_note"),
            "completedAt": t.get("completed_at"),
            "updatedAt": t.get("updated_at"),
        }


# --------------------------------------------------------------------------- #
# facade                                                                       #
# --------------------------------------------------------------------------- #
class ReadModel:
    """UI-facing read facade: calls :class:`SecureGuideService` and returns the
    versioned ``camelCase`` wire contract. Screens depend on this shape only.

    Every method returns a plain JSON-serializable ``dict`` (or list) so the
    same output can be handed to a Flutter client, a local API, or a golden
    fixture without adaptation.
    """

    def __init__(self, service: SecureGuideService):
        self._service = service

    # -- profile selector -------------------------------------------------- #
    def profiles(self) -> dict[str, Any]:
        rows = self._service.list_profiles()
        return _envelope(
            profiles=[ProfileSummary.from_row(row).to_wire() for row in rows]
        )

    def active_profile(self) -> dict[str, Any]:
        row = self._service.active_profile()
        profile = ProfileSummary.from_row(row, is_active=True).to_wire() if row else None
        return _envelope(profile=profile)

    # -- home dashboard ---------------------------------------------------- #
    def dashboard(self, *, profile_id: Optional[str] = None, gap_limit: int = 20) -> dict[str, Any]:
        data = self._service.dashboard(profile_id=profile_id, gap_limit=gap_limit)
        return _envelope(
            profile=ProfileSummary.from_row(data.get("profile") or {}).to_wire(),
            counts=DashboardCounts.from_row(data.get("counts") or {}).to_wire(),
            score=ScoreView.from_row(data.get("score") or {}).to_wire(),
            gaps=[GapItem.from_row(g).to_wire() for g in data.get("gaps") or []],
            recommendations=[
                RecommendationItem.from_row(r).to_wire()
                for r in data.get("recommendations") or []
            ],
            reviewQueue=[
                OperationalItem.from_row(i).to_wire() for i in data.get("review_queue") or []
            ],
        )

    # -- master catalog viewer -------------------------------------------- #
    def catalog(
        self,
        *,
        profile_id: Optional[str] = None,
        locale: str = "en",
        query: Optional[str] = None,
        filters: Optional[dict[str, Any]] = None,
        selected_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        rows = self._service.search_catalog(
            profile_id=profile_id,
            locale=locale,
            query=query,
            filters=filters,
            selected_only=selected_only,
            limit=limit,
            offset=offset,
        )
        items = [CatalogItem.from_row(row).to_wire() for row in rows]
        return _envelope(
            locale=locale,
            query=query,
            limit=limit,
            offset=offset,
            count=len(items),
            items=items,
        )

    # -- blueprints -------------------------------------------------------- #
    def blueprints(
        self,
        *,
        profile_id: Optional[str] = None,
        artifact_id: Optional[str] = None,
        workflow_status: Optional[str] = None,
    ) -> dict[str, Any]:
        rows = self._service.list_blueprints(
            profile_id=profile_id,
            artifact_id=artifact_id,
            workflow_status=workflow_status,
        )
        return _envelope(
            blueprints=[BlueprintSummary.from_row(row).to_wire() for row in rows]
        )

    def blueprint(self, blueprint_id: str, *, profile_id: Optional[str] = None) -> dict[str, Any]:
        detail = self._service.blueprint_detail(blueprint_id, profile_id=profile_id)
        return _envelope(blueprint=BlueprintDetail.from_row(detail).to_wire())

    # -- tasks ------------------------------------------------------------- #
    def tasks(
        self, *, profile_id: Optional[str] = None, status: Optional[str] = None
    ) -> dict[str, Any]:
        rows = self._service.list_tasks(profile_id=profile_id, status=status)
        return _envelope(tasks=[TaskItem.from_row(row).to_wire() for row in rows])

    # -- official report (approved-only) ----------------------------------- #
    def report(self, *, profile_id: Optional[str] = None) -> dict[str, Any]:
        data = self._service.report(profile_id=profile_id)
        summary = data.get("summary") or {}
        return _envelope(
            reportType=data.get("report_type"),
            generatedAt=data.get("generated_at"),
            formulaVersion=data.get("formula_version"),
            profile=ProfileSummary.from_row(data.get("profile") or {}).to_wire(),
            summary={
                "counts": DashboardCounts.from_row(summary.get("counts") or {}).to_wire(),
                "score": ScoreView.from_row(summary.get("score") or {}).to_wire(),
                "gapCount": summary.get("gap_count"),
                "reviewQueueCount": summary.get("review_queue_count"),
                "approvedBlueprintCount": summary.get("approved_blueprint_count"),
                "taskCount": summary.get("task_count"),
                "openTaskCount": summary.get("open_task_count"),
            },
            items=[OperationalItem.from_row(i).to_wire() for i in data.get("items") or []],
            gaps=[GapItem.from_row(g).to_wire() for g in data.get("gaps") or []],
            reviewQueue=[
                OperationalItem.from_row(i).to_wire() for i in data.get("review_queue") or []
            ],
            approvedBlueprints=[
                BlueprintSummary.from_row(b).to_wire()
                for b in data.get("approved_blueprints") or []
            ],
            tasks=[TaskItem.from_row(t).to_wire() for t in data.get("tasks") or []],
        )
