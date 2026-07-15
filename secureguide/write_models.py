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
from .read_models import CONTRACT_VERSION, ProfileSummary
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
