"""Deterministic, explainable Dynamic Action & Evidence Blueprint engine."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from typing import Any, Callable

from .aliases import normalize_context
from .models import (
    AppliedRule,
    BlueprintAction,
    BlueprintEvidence,
    ClassificationContext,
    EffortProfile,
    ExpectedOutput,
    GeneratedBlueprint,
    SuggestedSolution,
    SupportingAsset,
)
from .rules import RulePack, load_rule_pack


ENGINE_VERSION = "1.0.0"
SUPPORTED_ARTIFACT_TYPES = {
    "ART-POL", "ART-STD", "ART-PRC", "ART-CTR",
    "ART-REQ", "ART-EVD", "ART-MET", "ART-RSK",
}
STAGE_ORDER = {
    "ARTIFACT_TYPE": 0,
    "CONTROL_NATURE": 1,
    "CONTROL_FUNCTION": 2,
    "SECURITY_DOMAIN": 3,
    "OBLIGATION_LEVEL": 4,
}


class BlueprintGenerationError(ValueError):
    pass


def _stable_id(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16].upper()
    return f"{prefix}-{digest}"


def _matches(rule: dict[str, Any], context: ClassificationContext) -> bool:
    values = context.to_rule_values()
    return all(values.get(field) in accepted for field, accepted in rule["when"].items())


def _merge_emissions(
    matches: list[dict[str, Any]], collection: str, conflicts: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    code_fields = {
        "actions": "actionCode",
        "expectedOutputs": "outputCode",
        "evidence": "evidenceCode",
        "supportingAssets": "assetType",
        "suggestedSolutions": "solutionType",
    }
    for rule in matches:
        for item in rule["then"].get(collection, []):
            key = item["semanticKey"]
            candidate = dict(item)
            candidate["sourceRuleIds"] = [rule["ruleId"]]
            candidate["sourceRuleVersions"] = [rule["ruleVersion"]]
            candidate["rationales"] = [rule["rationale"]]
            candidate["confidence"] = float(rule["baseConfidence"])
            if key not in merged:
                merged[key] = candidate
                continue
            current = merged[key]
            code_field = code_fields.get(collection)
            if code_field and current.get(code_field) != candidate.get(code_field):
                conflicts.append({
                    "collection": collection,
                    "semanticKey": key,
                    "field": code_field,
                    "values": [current.get(code_field), candidate.get(code_field)],
                    "sourceRuleIds": current["sourceRuleIds"] + candidate["sourceRuleIds"],
                })
            for source_key in ("sourceRuleIds", "sourceRuleVersions", "rationales"):
                current[source_key] = list(dict.fromkeys(current[source_key] + candidate[source_key]))
            current["confidence"] = min(current["confidence"], candidate["confidence"])
            if collection == "evidence":
                current["mandatory"] = bool(current.get("mandatory") or candidate.get("mandatory"))
    return list(merged.values())


def _rationale(item: dict[str, Any]) -> str:
    return " | ".join(item.pop("rationales"))


class BlueprintEngine:
    """Generate transient suggestions; this class performs no persistence."""

    def __init__(self, rule_pack: RulePack | None = None):
        self.rule_pack = rule_pack or load_rule_pack()
        if self.rule_pack.engine_compatibility.split(".")[0] != ENGINE_VERSION.split(".")[0]:
            raise BlueprintGenerationError("rule pack is not compatible with this engine")

    def generate(self, context: ClassificationContext) -> GeneratedBlueprint:
        normalized, normalization, review_reasons, normalization_quality = normalize_context(context)
        if normalized.artifact_type not in SUPPORTED_ARTIFACT_TYPES:
            raise BlueprintGenerationError(
                f"artifact type is outside the MVP rule pack: {normalized.artifact_type}"
            )
        matches = [rule for rule in self.rule_pack.rules if _matches(rule, normalized)]
        matches.sort(key=lambda r: (STAGE_ORDER[r["stage"]], r["priority"], r["ruleId"]))
        base = [rule for rule in matches if rule["stage"] == "ARTIFACT_TYPE"]
        if len(base) != 1:
            raise BlueprintGenerationError(
                f"expected exactly one artifact-type rule, found {len(base)}"
            )

        conflicts: list[dict[str, Any]] = []
        emissions = {
            name: _merge_emissions(matches, name, conflicts)
            for name in (
                "actions", "expectedOutputs", "evidence", "effortProfiles",
                "supportingAssets", "suggestedSolutions",
            )
        }
        if conflicts:
            review_reasons.append("semantic emission conflicts require human review")

        source_artifact_id = normalized.source_artifact_id or normalized.artifact_id
        actions: list[BlueprintAction] = []
        for order, item in enumerate(emissions["actions"], 1):
            actions.append(BlueprintAction(
                id=_stable_id("BPA", item["semanticKey"]),
                action_code=item["actionCode"], semantic_key=item["semanticKey"],
                title=item["title"], description=item["description"],
                category=item.get("category", "IMPLEMENTATION"),
                phase=item.get("phase", "IMPLEMENT"), order=order,
                source_rule_ids=item["sourceRuleIds"],
                source_rule_versions=item["sourceRuleVersions"],
                source_artifact_id=source_artifact_id,
                source_citation=normalized.source_citation if item.get("inheritSourceCitation") else None,
                rationale=_rationale(item), confidence=item["confidence"],
                taskable=bool(item.get("taskable", True)),
                requires_human_review=bool(conflicts),
            ))

        expected_outputs: list[ExpectedOutput] = []
        for item in emissions["expectedOutputs"]:
            expected_outputs.append(ExpectedOutput(
                id=_stable_id("BPO", item["semanticKey"]),
                output_code=item["outputCode"], semantic_key=item["semanticKey"],
                title=item["title"], description=item["description"],
                source_rule_ids=item["sourceRuleIds"],
                source_rule_versions=item["sourceRuleVersions"],
                rationale=_rationale(item),
            ))

        evidence_items: list[BlueprintEvidence] = []
        for item in emissions["evidence"]:
            evidence_items.append(BlueprintEvidence(
                id=_stable_id("BPE", item["semanticKey"]),
                evidence_code=item["evidenceCode"], semantic_key=item["semanticKey"],
                title=item["title"], evidence_type=item["evidenceType"],
                description=item["description"], source_rule_ids=item["sourceRuleIds"],
                source_rule_versions=item["sourceRuleVersions"],
                source_artifact_id=source_artifact_id,
                source_citation=normalized.source_citation if item.get("inheritSourceCitation") else None,
                rationale=_rationale(item), mandatory=bool(item.get("mandatory", False)),
                confidence=item["confidence"], requires_human_review=bool(conflicts),
            ))

        effort_profiles: list[EffortProfile] = []
        for item in emissions["effortProfiles"]:
            effort_profiles.append(EffortProfile(
                semantic_key=item["semanticKey"], effort_types=item["effortTypes"],
                effort_level=item["effortLevel"], skill_requirements=item["skillRequirements"],
                estimated_complexity=item["estimatedComplexity"],
                implementation_mode=item["implementationMode"],
                source_rule_ids=item["sourceRuleIds"],
                source_rule_versions=item["sourceRuleVersions"], rationale=_rationale(item),
            ))

        supporting_assets: list[SupportingAsset] = []
        for item in emissions["supportingAssets"]:
            supporting_assets.append(SupportingAsset(
                id=_stable_id("BPS", item["semanticKey"]), semantic_key=item["semanticKey"],
                asset_type=item["assetType"], title=item["title"], usage=item["usage"],
                availability=item["availability"], template_ref=item.get("templateRef"),
                source_rule_ids=item["sourceRuleIds"], source_rule_versions=item["sourceRuleVersions"],
                rationale=_rationale(item),
            ))

        solutions: list[SuggestedSolution] = []
        for item in emissions["suggestedSolutions"]:
            solutions.append(SuggestedSolution(
                id=_stable_id("BPL", item["semanticKey"]), semantic_key=item["semanticKey"],
                solution_type=item["solutionType"], title=item["title"],
                description=item["description"], recommendation_level=item["recommendationLevel"],
                vendor_neutral=bool(item["vendorNeutral"]),
                requires_human_validation=bool(item.get("requiresHumanValidation", True)),
                prerequisites=item.get("prerequisites", []), risks=item.get("risks", []),
                source_rule_ids=item["sourceRuleIds"], source_rule_versions=item["sourceRuleVersions"],
                rationale=_rationale(item),
            ))

        confidence, factors = self._confidence(normalized, matches, normalization_quality, conflicts)
        if normalized.classification_confidence is not None and normalized.classification_confidence <= .70:
            review_reasons.append("classification confidence is at or below 0.70")
        if normalized.ai_review_status in {"AIR-HUMAN-REVIEW", "AIR-HUMAN-REJECTED"}:
            review_reasons.append(f"classification review status is {normalized.ai_review_status}")
        review_reasons = list(dict.fromkeys(review_reasons))

        fingerprint = json.dumps(
            {"context": asdict(normalized), "ruleSetHash": self.rule_pack.sha256},
            ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        )
        return GeneratedBlueprint(
            blueprint_id=_stable_id("GBP", fingerprint), artifact_id=normalized.artifact_id,
            artifact_type=normalized.artifact_type, action_plan_type=base[0]["then"]["actionPlanType"],
            title=base[0]["then"].get("titleTemplate", "خطة تنفيذ معيارية"),
            actions=actions, expected_outputs=expected_outputs, evidence=evidence_items,
            applied_rules=[AppliedRule(
                rule_id=r["ruleId"], rule_version=r["ruleVersion"], stage=r["stage"],
                priority=r["priority"], rationale=r["rationale"], base_confidence=r["baseConfidence"]
            ) for r in matches],
            effort_profiles=effort_profiles, supporting_assets=supporting_assets,
            suggested_solutions=solutions, confidence=confidence, confidence_factors=factors,
            requires_human_review=bool(review_reasons), review_reasons=review_reasons,
            normalization_events=normalization, conflicts=conflicts, engine_version=ENGINE_VERSION,
            rule_set_id=self.rule_pack.rule_set_id, rule_set_version=self.rule_pack.rule_set_version,
            rule_set_hash=self.rule_pack.sha256,
        )

    @staticmethod
    def _confidence(
        context: ClassificationContext,
        matches: list[dict[str, Any]],
        normalization_quality: float,
        conflicts: list[dict[str, Any]],
    ) -> tuple[float, dict[str, float]]:
        required = [context.artifact_type, context.primary_domain, context.obligation_level]
        if context.artifact_type == "ART-CTR":
            required += [context.control_nature, context.control_function]
        completeness = sum(value is not None for value in required) / len(required)
        optional = [context.control_nature, context.control_function, context.sub_domain]
        specificity = .7 + .1 * sum(value is not None for value in optional)
        if context.ai_review_status == "AIR-HUMAN-APPROVED":
            classification = 1.0
        elif context.classification_confidence is None:
            classification = .75
        else:
            classification = context.classification_confidence
        maturity = sum(float(rule["baseConfidence"]) for rule in matches) / len(matches)
        factors = {
            "completeness": completeness,
            "specificity": min(1.0, specificity),
            "classificationQuality": classification,
            "conflictFree": 0.0 if conflicts else 1.0,
            "ruleMaturity": maturity,
            "normalizationQuality": normalization_quality,
        }
        weights = {
            "completeness": .22, "specificity": .20, "classificationQuality": .20,
            "conflictFree": .15, "ruleMaturity": .13, "normalizationQuality": .10,
        }
        return sum(factors[key] * weights[key] for key in weights), factors
