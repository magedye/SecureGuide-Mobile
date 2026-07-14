"""Typed, non-authoritative blueprint DTOs used by the MVP engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _without_none(values: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None}


@dataclass(frozen=True)
class ClassificationContext:
    artifact_id: str
    artifact_type: str
    primary_domain: str
    obligation_level: str
    control_nature: str | None = None
    control_function: str | None = None
    sub_domain: str | None = None
    classification_confidence: float | None = None
    ai_review_status: str | None = None
    source_artifact_id: str | None = None
    source_citation: str | None = None

    def to_rule_values(self) -> dict[str, str | None]:
        return {
            "artifactTypes": self.artifact_type,
            "controlNatures": self.control_nature,
            "controlFunctions": self.control_function,
            "primaryDomains": self.primary_domain,
            "obligationLevels": self.obligation_level,
        }


@dataclass
class AppliedRule:
    rule_id: str
    rule_version: str
    stage: str
    priority: int
    rationale: str
    base_confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "ruleId": self.rule_id,
            "ruleVersion": self.rule_version,
            "stage": self.stage,
            "priority": self.priority,
            "rationale": self.rationale,
            "baseConfidence": self.base_confidence,
        }


@dataclass
class BlueprintAction:
    id: str
    action_code: str
    semantic_key: str
    title: str
    description: str
    category: str
    phase: str
    order: int
    source_rule_ids: list[str]
    source_rule_versions: list[str]
    rationale: str
    source_artifact_id: str | None = None
    source_citation: str | None = None
    confidence: float = 1.0
    taskable: bool = True
    requires_human_review: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _without_none(
            {
                "id": self.id,
                "actionCode": self.action_code,
                "semanticKey": self.semantic_key,
                "title": self.title,
                "description": self.description,
                "category": self.category,
                "phase": self.phase,
                "order": self.order,
                "sourceRuleIds": self.source_rule_ids,
                "sourceRuleVersions": self.source_rule_versions,
                "sourceArtifactId": self.source_artifact_id,
                "sourceCitation": self.source_citation,
                "rationale": self.rationale,
                "confidence": round(self.confidence, 4),
                "taskable": self.taskable,
                "requiresHumanReview": self.requires_human_review,
            }
        )


@dataclass
class ExpectedOutput:
    id: str
    output_code: str
    semantic_key: str
    title: str
    description: str
    source_rule_ids: list[str]
    source_rule_versions: list[str]
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "outputCode": self.output_code,
            "semanticKey": self.semantic_key,
            "title": self.title,
            "description": self.description,
            "sourceRuleIds": self.source_rule_ids,
            "sourceRuleVersions": self.source_rule_versions,
            "rationale": self.rationale,
        }


@dataclass
class BlueprintEvidence:
    id: str
    evidence_code: str
    semantic_key: str
    title: str
    evidence_type: str
    description: str
    source_rule_ids: list[str]
    source_rule_versions: list[str]
    rationale: str
    mandatory: bool
    source_artifact_id: str | None = None
    source_citation: str | None = None
    confidence: float = 1.0
    requires_human_review: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _without_none(
            {
                "id": self.id,
                "evidenceCode": self.evidence_code,
                "semanticKey": self.semantic_key,
                "title": self.title,
                "evidenceType": self.evidence_type,
                "description": self.description,
                "sourceRuleIds": self.source_rule_ids,
                "sourceRuleVersions": self.source_rule_versions,
                "sourceArtifactId": self.source_artifact_id,
                "sourceCitation": self.source_citation,
                "rationale": self.rationale,
                "mandatory": self.mandatory,
                "confidence": round(self.confidence, 4),
                "requiresHumanReview": self.requires_human_review,
            }
        )


@dataclass
class EffortProfile:
    semantic_key: str
    effort_types: list[str]
    effort_level: str
    skill_requirements: list[str]
    estimated_complexity: str
    implementation_mode: str
    source_rule_ids: list[str]
    source_rule_versions: list[str]
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "semanticKey": self.semantic_key,
            "effortTypes": self.effort_types,
            "effortLevel": self.effort_level,
            "skillRequirements": self.skill_requirements,
            "estimatedComplexity": self.estimated_complexity,
            "implementationMode": self.implementation_mode,
            "sourceRuleIds": self.source_rule_ids,
            "sourceRuleVersions": self.source_rule_versions,
            "rationale": self.rationale,
        }


@dataclass
class SupportingAsset:
    id: str
    semantic_key: str
    asset_type: str
    title: str
    usage: str
    availability: str
    source_rule_ids: list[str]
    source_rule_versions: list[str]
    rationale: str
    template_ref: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return _without_none(
            {
                "id": self.id,
                "semanticKey": self.semantic_key,
                "assetType": self.asset_type,
                "title": self.title,
                "usage": self.usage,
                "availability": self.availability,
                "templateRef": self.template_ref,
                "sourceRuleIds": self.source_rule_ids,
                "sourceRuleVersions": self.source_rule_versions,
                "rationale": self.rationale,
            }
        )


@dataclass
class SuggestedSolution:
    id: str
    semantic_key: str
    solution_type: str
    title: str
    description: str
    recommendation_level: str
    vendor_neutral: bool
    requires_human_validation: bool
    prerequisites: list[str]
    risks: list[str]
    source_rule_ids: list[str]
    source_rule_versions: list[str]
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "semanticKey": self.semantic_key,
            "solutionType": self.solution_type,
            "title": self.title,
            "description": self.description,
            "recommendationLevel": self.recommendation_level,
            "vendorNeutral": self.vendor_neutral,
            "requiresHumanValidation": self.requires_human_validation,
            "prerequisites": self.prerequisites,
            "risks": self.risks,
            "sourceRuleIds": self.source_rule_ids,
            "sourceRuleVersions": self.source_rule_versions,
            "rationale": self.rationale,
        }


@dataclass
class GeneratedBlueprint:
    blueprint_id: str
    artifact_id: str
    artifact_type: str
    action_plan_type: str
    title: str
    actions: list[BlueprintAction]
    expected_outputs: list[ExpectedOutput]
    evidence: list[BlueprintEvidence]
    applied_rules: list[AppliedRule]
    effort_profiles: list[EffortProfile]
    supporting_assets: list[SupportingAsset]
    suggested_solutions: list[SuggestedSolution]
    confidence: float
    confidence_factors: dict[str, float]
    requires_human_review: bool
    review_reasons: list[str]
    normalization_events: list[dict[str, Any]]
    conflicts: list[dict[str, Any]]
    engine_version: str
    rule_set_id: str
    rule_set_version: str
    rule_set_hash: str
    blueprint_version: str = "1.0.0"
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    approval_status: str = "GENERATED"
    is_generated: bool = True
    authoritative: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "blueprintId": self.blueprint_id,
            "artifactId": self.artifact_id,
            "artifactType": self.artifact_type,
            "actionPlanType": self.action_plan_type,
            "title": self.title,
            "actions": [item.to_dict() for item in self.actions],
            "expectedOutputs": [item.to_dict() for item in self.expected_outputs],
            "evidence": [item.to_dict() for item in self.evidence],
            "appliedRules": [item.to_dict() for item in self.applied_rules],
            "effortProfiles": [item.to_dict() for item in self.effort_profiles],
            "supportingAssets": [item.to_dict() for item in self.supporting_assets],
            "suggestedSolutions": [item.to_dict() for item in self.suggested_solutions],
            "confidence": round(self.confidence, 4),
            "confidenceFactors": {
                key: round(value, 4) for key, value in self.confidence_factors.items()
            },
            "requiresHumanReview": self.requires_human_review,
            "reviewReasons": self.review_reasons,
            "normalizationEvents": self.normalization_events,
            "conflicts": self.conflicts,
            "engineVersion": self.engine_version,
            "ruleSetId": self.rule_set_id,
            "ruleSetVersion": self.rule_set_version,
            "ruleSetHash": self.rule_set_hash,
            "blueprintVersion": self.blueprint_version,
            "generatedAt": self.generated_at,
            "approvalStatus": self.approval_status,
            "isGenerated": self.is_generated,
            "authoritative": self.authoritative,
            "displayLabel": "اقتراحات معيارية بناءً على التصنيف",
        }
