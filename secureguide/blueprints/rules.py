"""Versioned rule-pack loading and strict validation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .aliases import (
    ARTIFACT_TYPES,
    CONTROL_FUNCTIONS,
    CONTROL_NATURES,
    OBLIGATION_LEVELS,
    PRIMARY_DOMAINS,
)


STAGES = (
    "ARTIFACT_TYPE",
    "CONTROL_NATURE",
    "CONTROL_FUNCTION",
    "SECURITY_DOMAIN",
    "OBLIGATION_LEVEL",
)
MATCH_FIELDS = {
    "artifactTypes": ARTIFACT_TYPES,
    "controlNatures": CONTROL_NATURES,
    "controlFunctions": CONTROL_FUNCTIONS,
    "primaryDomains": PRIMARY_DOMAINS,
    "obligationLevels": OBLIGATION_LEVELS,
}
EMISSION_COLLECTIONS = (
    "actions",
    "expectedOutputs",
    "evidence",
    "effortProfiles",
    "supportingAssets",
    "suggestedSolutions",
)
EMISSION_REQUIRED = {
    "actions": {"actionCode", "semanticKey", "title", "description", "category", "phase", "taskable"},
    "expectedOutputs": {"outputCode", "semanticKey", "title", "description"},
    "evidence": {"evidenceCode", "semanticKey", "title", "evidenceType", "description", "mandatory"},
    "effortProfiles": {"semanticKey", "effortTypes", "effortLevel", "skillRequirements", "estimatedComplexity", "implementationMode"},
    "supportingAssets": {"semanticKey", "assetType", "title", "usage", "availability"},
    "suggestedSolutions": {"semanticKey", "solutionType", "title", "description", "recommendationLevel", "vendorNeutral", "requiresHumanValidation", "prerequisites", "risks"},
}
EVIDENCE_TYPES = {"DOCUMENT", "SCREENSHOT", "LOG", "REPORT", "CONFIG", "ATTESTATION", "LINK", "OTHER"}


class RulePackError(ValueError):
    """Raised when a rule pack is ambiguous, malformed, or non-canonical."""


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise RulePackError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _canonical_hash(value: dict[str, Any]) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class RulePack:
    rule_set_id: str
    rule_set_version: str
    engine_compatibility: str
    rules: tuple[dict[str, Any], ...]
    sha256: str
    path: Path


def _require(value: dict[str, Any], key: str, expected: type) -> Any:
    item = value.get(key)
    if not isinstance(item, expected) or (expected is str and not item.strip()):
        raise RulePackError(f"{key} must be a non-empty {expected.__name__}")
    return item


def _validate_rule(rule: dict[str, Any], seen: set[str]) -> None:
    rule_id = _require(rule, "ruleId", str)
    if rule_id in seen:
        raise RulePackError(f"duplicate ruleId: {rule_id}")
    seen.add(rule_id)
    _require(rule, "ruleVersion", str)
    stage = _require(rule, "stage", str)
    if stage not in STAGES:
        raise RulePackError(f"invalid stage in {rule_id}: {stage}")
    if not isinstance(rule.get("priority"), int):
        raise RulePackError(f"priority must be integer in {rule_id}")
    confidence = rule.get("baseConfidence")
    if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        raise RulePackError(f"baseConfidence must be 0..1 in {rule_id}")
    _require(rule, "rationale", str)

    when = _require(rule, "when", dict)
    unknown = set(when) - set(MATCH_FIELDS)
    if unknown:
        raise RulePackError(f"unknown match fields in {rule_id}: {sorted(unknown)}")
    for key, values in when.items():
        if not isinstance(values, list) or not values:
            raise RulePackError(f"{key} must be a non-empty array in {rule_id}")
        invalid = set(values) - MATCH_FIELDS[key]
        if invalid:
            raise RulePackError(f"non-canonical {key} in {rule_id}: {sorted(invalid)}")

    then = _require(rule, "then", dict)
    unknown_then = set(then) - (set(EMISSION_COLLECTIONS) | {"actionPlanType", "titleTemplate"})
    if unknown_then:
        raise RulePackError(f"unknown then fields in {rule_id}: {sorted(unknown_then)}")
    if "actionPlanType" in then and stage != "ARTIFACT_TYPE":
        raise RulePackError(f"only ARTIFACT_TYPE may set actionPlanType: {rule_id}")
    if stage == "ARTIFACT_TYPE" and not then.get("actionPlanType"):
        raise RulePackError(f"base rule must set actionPlanType: {rule_id}")
    for collection in EMISSION_COLLECTIONS:
        values = then.get(collection, [])
        if not isinstance(values, list):
            raise RulePackError(f"{collection} must be an array in {rule_id}")
        semantic_keys: set[str] = set()
        for item in values:
            if not isinstance(item, dict):
                raise RulePackError(f"{collection} items must be objects in {rule_id}")
            missing = EMISSION_REQUIRED[collection] - set(item)
            if missing:
                raise RulePackError(
                    f"missing fields in {rule_id}.{collection}: {sorted(missing)}"
                )
            semantic = _require(item, "semanticKey", str)
            if semantic in semantic_keys:
                raise RulePackError(
                    f"duplicate semanticKey {semantic} in {rule_id}.{collection}"
                )
            semantic_keys.add(semantic)
            if collection == "evidence" and item["evidenceType"] not in EVIDENCE_TYPES:
                raise RulePackError(f"invalid evidenceType in {rule_id}: {item['evidenceType']}")
            if collection == "suggestedSolutions" and not item.get("vendorNeutral", False):
                raise RulePackError(f"MVP solutions must be vendor-neutral in {rule_id}")


def load_rule_pack(path: str | Path | None = None) -> RulePack:
    """Load JSON while rejecting duplicate keys before structural validation."""
    target = Path(path) if path else (
        Path(__file__).resolve().parents[2] / "reference" / "blueprint_rules_mvp_v1.json"
    )
    try:
        raw = target.read_text(encoding="utf-8")
        value = json.loads(raw, object_pairs_hook=_no_duplicate_keys)
    except RulePackError:
        raise
    except (OSError, json.JSONDecodeError) as exc:
        raise RulePackError(f"cannot load rule pack {target}: {exc}") from exc
    if not isinstance(value, dict):
        raise RulePackError("rule pack root must be an object")
    rule_set_id = _require(value, "ruleSetId", str)
    rule_set_version = _require(value, "ruleSetVersion", str)
    compatibility = _require(value, "engineCompatibility", str)
    if value.get("status") != "ACTIVE":
        raise RulePackError("rule pack status must be ACTIVE")
    rules = _require(value, "rules", list)
    if not rules:
        raise RulePackError("rule pack must contain rules")
    seen: set[str] = set()
    for rule in rules:
        if not isinstance(rule, dict):
            raise RulePackError("each rule must be an object")
        _validate_rule(rule, seen)
    order = {stage: index for index, stage in enumerate(STAGES)}
    sorted_rules = tuple(
        sorted(rules, key=lambda r: (order[r["stage"]], r["priority"], r["ruleId"]))
    )
    return RulePack(
        rule_set_id=rule_set_id,
        rule_set_version=rule_set_version,
        engine_compatibility=compatibility,
        rules=sorted_rules,
        sha256=_canonical_hash(value),
        path=target,
    )
