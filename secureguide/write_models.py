"""Write-side facade over :class:`SecureGuideService`.

Symmetric with :class:`~secureguide.read_models.ReadModel`: a pure translation
layer that maps ``camelCase`` write requests onto the service's governed write
operations and returns the affected resource as a ``read-model-v1`` DTO, so a
client can update its state from the response. Every business rule (validation,
controlled values, state machines, isolation) stays in the service — this layer
only renames keys and re-wraps the result.
"""

from __future__ import annotations

from typing import Any

from .errors import ValidationError
from .read_models import (
    CONTRACT_VERSION,
    AssessmentRecord,
    OperationalItem,
    ProfileSummary,
)
from .services import SecureGuideService

__all__ = ["WriteModel"]


def _envelope(**body: Any) -> dict[str, Any]:
    return {"contractVersion": CONTRACT_VERSION, **body}


class WriteModel:
    """UI-facing write facade. Returns the same versioned wire shapes as reads."""

    def __init__(self, service: SecureGuideService):
        self._service = service

    def create_profile(self, payload: dict[str, Any]) -> dict[str, Any]:
        activate = bool(payload.get("activate", False))
        profile = self._service.create_profile(
            name=payload.get("name"),
            profile_id=payload.get("profileId"),
            description=payload.get("description"),
            profile_kind=payload.get("profileKind"),
            organization_size=payload.get("organizationSize"),
            industry=payload.get("industry"),
            country=payload.get("country"),
            target_maturity_level=payload.get("targetMaturityLevel"),
            activate=activate,
        )
        return _envelope(
            profile=ProfileSummary.from_row(profile, is_active=activate).to_wire()
        )

    def activate_profile(self, payload: dict[str, Any]) -> dict[str, Any]:
        profile_id = payload.get("profileId")
        if not profile_id or not str(profile_id).strip():
            raise ValidationError("profileId is required")
        profile = self._service.activate_profile(str(profile_id))
        return _envelope(
            profile=ProfileSummary.from_row(profile, is_active=True).to_wire()
        )

    def select_artifacts(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = self._service.select_artifacts(
            payload.get("artifactIds") or [],
            profile_id=payload.get("profileId"),
            selected_by=payload.get("selectedBy"),
            inclusion_status=payload.get("inclusionStatus"),
            selection_reason=payload.get("selectionReason"),
        )
        return _envelope(
            selection={
                "profileId": result["profile_id"],
                "requested": result["requested"],
                "created": result["created"],
                "existing": result["existing"],
                "originsAdded": result["origins_added"],
                "profileArtifactIds": result["profile_artifact_ids"],
            }
        )

    def assess_artifact(self, payload: dict[str, Any]) -> dict[str, Any]:
        artifact_id = payload.get("artifactId")
        if not artifact_id or not str(artifact_id).strip():
            raise ValidationError("artifactId is required")
        assessment = self._service.assess_artifact(
            str(artifact_id),
            profile_id=payload.get("profileId"),
            assessor_name=payload.get("assessorName"),
            implementation_status=payload.get("implementationStatus"),
            verification_status=payload.get("verificationStatus"),
            effectiveness=payload.get("effectiveness"),
            current_maturity_level=payload.get("currentMaturityLevel"),
            assigned_owner=payload.get("assignedOwner"),
            clear_assigned_owner=bool(payload.get("clearAssignedOwner", False)),
            due_date=payload.get("dueDate"),
            clear_due_date=bool(payload.get("clearDueDate", False)),
            notes=payload.get("notes"),
            clear_notes=bool(payload.get("clearNotes", False)),
            priority_override=payload.get("priorityOverride"),
            review_frequency_override=payload.get("reviewFrequencyOverride"),
            clear_priority_override=bool(payload.get("clearPriorityOverride", False)),
            clear_review_frequency_override=bool(
                payload.get("clearReviewFrequencyOverride", False)
            ),
            score=payload.get("score"),
            comments=payload.get("comments"),
        )
        detail = self._service.profile_artifact_detail(
            str(artifact_id), profile_id=payload.get("profileId")
        )
        return _envelope(
            assessment=AssessmentRecord.from_row(assessment).to_wire(),
            artifact=OperationalItem.from_row(detail["artifact"]).to_wire(),
        )

    def apply_template(self, payload: dict[str, Any]) -> dict[str, Any]:
        template_id = payload.get("templateId")
        if not template_id or not str(template_id).strip():
            raise ValidationError("templateId is required")
        template_version = payload.get("templateVersion")
        if not template_version or not str(template_version).strip():
            raise ValidationError("templateVersion is required")
        applied_by = payload.get("appliedBy")
        if not applied_by or not str(applied_by).strip():
            raise ValidationError("appliedBy is required")
        result = self._service.apply_template(
            str(template_id),
            str(template_version),
            str(applied_by),
            profile_id=payload.get("profileId"),
            note=payload.get("note"),
        )
        return _envelope(
            application={
                "profileId": result["profile_id"],
                "templateId": result["template_id"],
                "templateVersion": result["template_version"],
                "appliedItems": result["applied_items"],
            }
        )

    def add_evidence(self, payload: dict[str, Any]) -> dict[str, Any]:
        artifact_id = payload.get("artifactId")
        if not artifact_id or not str(artifact_id).strip():
            raise ValidationError("artifactId is required")
        evidence_type = payload.get("evidenceType")
        if not evidence_type or not str(evidence_type).strip():
            raise ValidationError("evidenceType is required")
        result = self._service.add_evidence(
            str(artifact_id),
            evidence_type=str(evidence_type),
            profile_id=payload.get("profileId"),
            assessment_id=payload.get("assessmentId"),
            evidence_url=payload.get("evidenceUrl"),
            description=payload.get("description"),
            title=payload.get("title"),
            collected_by=payload.get("collectedBy"),
            content_hash=payload.get("contentHash"),
            mime_type=payload.get("mimeType"),
        )
        return _envelope(
            evidence={
                "id": result["id"],
                "profileArtifactId": result["profile_artifact_id"],
                "evidenceType": result["evidence_type"],
                "evidenceUrl": result["evidence_url"],
                "title": result["title"],
                "description": result["description"],
                "collectedBy": result["collected_by"],
            }
        )

    def create_exception(self, payload: dict[str, Any]) -> dict[str, Any]:
        artifact_id = payload.get("artifactId")
        if not artifact_id or not str(artifact_id).strip():
            raise ValidationError("artifactId is required")
        exception_status = payload.get("exceptionStatus")
        if not exception_status or not str(exception_status).strip():
            raise ValidationError("exceptionStatus is required")
        justification = payload.get("justification")
        if not justification or not str(justification).strip():
            raise ValidationError("justification is required")
        result = self._service.create_exception(
            str(artifact_id),
            exception_status=str(exception_status),
            justification=str(justification),
            profile_id=payload.get("profileId"),
            exception_source=payload.get("exceptionSource", "USER"),
        )
        return _envelope(
            exception={
                "id": result["id"],
                "profileArtifactId": result["profile_artifact_id"],
                "exceptionStatus": result["exception_status"],
                "justification": result["justification"],
                "workflowStatus": result["workflow_status"],
            }
        )
