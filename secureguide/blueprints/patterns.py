"""Read-only access to non-authoritative operational implementation patterns."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .aliases import (
    ARTIFACT_TYPES,
    CONTROL_FUNCTIONS,
    CONTROL_NATURES,
PRIMARY_DOMAINS,
)

SUB_DOMAINS = {f"SD-{domain:02d}.{subdomain:02d}" for domain in range(1, 9) for subdomain in range(1, 6)}
PRIORITIES = {"PRI-CRITICAL", "PRI-HIGH", "PRI-MEDIUM"}
AI_REVIEW_STATUSES = {"AIR-HUMAN-REVIEW"}
TESTABILITY_VALUES = {"TST-AUTO", "TST-MAN", "TST-DOC", "TST-INT", "TST-NA"}
REQUIREMENT_TYPES = {"RQT-GOV", "RQT-REG", "RQT-LEG", "RQT-CON", "RQT-STD", "RQT-INT", "RQT-RSK"}
REVIEW_FREQUENCIES = {"DAILY", "WEEKLY", "MONTHLY", "QUARTERLY", "SEMI-ANNUAL", "ANNUAL", "CONTINUOUS"}
DELIVERY_ARCHETYPES = {"URGENT_RESPONSE", "MANAGED_SERVICE", "PROGRAM", "INITIATIVE", "CONTINUOUS_OPERATION", "PROJECT", "CONTROLLED_CHANGE", "OPERATIONAL_ACTIVITY"}
EFFORT_SIZES = {"SMALL", "SMALL_MEDIUM", "MEDIUM", "MEDIUM_LARGE", "LARGE", "VERY_LARGE"}
COMPLEXITIES = {"MEDIUM", "HIGH"}
REQUIRED_PATTERN_FIELDS = {
    "patternId", "sourceRow", "sectionAr", "sourceTextAr", "titleAr",
    "originalClassificationAr", "originalDeliveryModelAr", "recommendedArtifactType",
    "primaryDomain", "subDomain", "controlNature", "controlFunction", "testability",
    "requirementType", "deliveryArchetype", "effortSize", "complexity", "priority",
    "ownerRoles", "implementationActions", "evidenceExamples", "acceptanceCriteriaAr",
    "reviewFrequencies", "requiresSplit", "safetyReviewRequired", "safetyNoteAr",
    "classificationConfidence", "classificationRationaleAr", "requiresHumanReview",
    "aiReviewStatus", "sourcePatternId",
}
REQUIRED_LIBRARY_FIELDS = {"libraryId", "version", "authoritative", "usageLabelAr", "source", "patterns"}
REQUIRED_SOURCE_FIELDS = {"sourceType", "sourceBatchId", "sourceSha256", "isOriginalRequirementSource", "usageConstraint"}


class OperationalPatternError(ValueError):
    pass


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise OperationalPatternError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


class OperationalPatternLibrary:
    """Versioned reference suggestions; never an original-requirement source."""

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else (
            Path(__file__).resolve().parents[2] / "reference" / "operational_patterns_v1.json"
        )
        try:
            raw = self.path.read_text(encoding="utf-8")
            payload = json.loads(raw, object_pairs_hook=_no_duplicates)
        except OperationalPatternError:
            raise
        except (OSError, json.JSONDecodeError) as exc:
            raise OperationalPatternError(f"cannot load pattern library: {exc}") from exc
        self._validate(payload)
        self.payload = payload
        self.sha256 = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        self._by_id = {item["patternId"]: item for item in payload["patterns"]}

    @staticmethod
    def _validate(payload: dict[str, Any]) -> None:
        if not isinstance(payload, dict):
            raise OperationalPatternError("pattern library root must be an object")
        if set(payload) != REQUIRED_LIBRARY_FIELDS:
            raise OperationalPatternError("invalid pattern library fields")
        if payload.get("authoritative") is not False:
            raise OperationalPatternError("operational patterns must be non-authoritative")
        if payload.get("usageLabelAr") != "اقتراحات معيارية بناءً على التصنيف":
            raise OperationalPatternError("invalid operational pattern usage label")
        source = payload.get("source")
        if not isinstance(source, dict) or source.get("isOriginalRequirementSource") is not False:
            raise OperationalPatternError("pattern source cannot be presented as original requirements")
        if set(source) != REQUIRED_SOURCE_FIELDS:
            raise OperationalPatternError("invalid pattern source fields")
        if source.get("sourceType") != "USER_SUPPLIED_OPERATIONAL_GUIDANCE":
            raise OperationalPatternError("invalid operational pattern source type")
        if not isinstance(source.get("sourceBatchId"), str) or not source["sourceBatchId"].strip():
            raise OperationalPatternError("invalid source batch id")
        if not isinstance(source.get("sourceSha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", source["sourceSha256"]):
            raise OperationalPatternError("invalid source hash")
        patterns = payload.get("patterns")
        if not isinstance(patterns, list) or not patterns:
            raise OperationalPatternError("patterns must be a non-empty array")
        ids: set[str] = set()
        rows: list[int] = []
        for item in patterns:
            if not isinstance(item, dict):
                raise OperationalPatternError("every pattern must be an object")
            missing = REQUIRED_PATTERN_FIELDS - item.keys()
            if missing:
                raise OperationalPatternError(f"pattern missing fields: {sorted(missing)}")
            unexpected = item.keys() - REQUIRED_PATTERN_FIELDS
            if unexpected:
                raise OperationalPatternError(f"pattern has unexpected fields: {sorted(unexpected)}")
            pattern_id = item.get("patternId")
            if (not isinstance(pattern_id, str) or not re.fullmatch(r"OPP-[0-9]{3}", pattern_id)
                    or pattern_id in ids):
                raise OperationalPatternError(f"invalid or duplicate patternId: {pattern_id}")
            ids.add(pattern_id)
            source_row = item.get("sourceRow")
            if isinstance(source_row, bool) or not isinstance(source_row, int):
                raise OperationalPatternError(f"invalid sourceRow in {pattern_id}")
            rows.append(source_row)
            artifact_type = item.get("recommendedArtifactType")
            domain = item.get("primaryDomain")
            subdomain = item.get("subDomain")
            if artifact_type not in ARTIFACT_TYPES:
                raise OperationalPatternError(f"invalid artifact type in {pattern_id}")
            if domain not in PRIMARY_DOMAINS or not isinstance(subdomain, str):
                raise OperationalPatternError(f"invalid domain in {pattern_id}")
            if subdomain not in SUB_DOMAINS or subdomain[:5] != domain:
                raise OperationalPatternError(f"invalid subdomain in {pattern_id}")
            nature = item.get("controlNature")
            function = item.get("controlFunction")
            testability = item.get("testability")
            requirement_type = item.get("requirementType")
            if artifact_type in {"ART-CTR", "ART-CTE"}:
                if (nature not in CONTROL_NATURES or function not in CONTROL_FUNCTIONS
                        or testability not in TESTABILITY_VALUES):
                    raise OperationalPatternError(f"control classification missing in {pattern_id}")
            elif nature is not None or function is not None or testability is not None:
                raise OperationalPatternError(f"non-control has control fields in {pattern_id}")
            if artifact_type == "ART-REQ":
                if requirement_type not in REQUIREMENT_TYPES:
                    raise OperationalPatternError(f"requirement type missing in {pattern_id}")
            elif requirement_type is not None:
                raise OperationalPatternError(f"non-requirement has requirementType in {pattern_id}")
            for field in ("ownerRoles", "implementationActions", "evidenceExamples"):
                if not isinstance(item.get(field), list) or not item[field]:
                    raise OperationalPatternError(f"{field} is empty in {pattern_id}")
                if len(item[field]) != len(set(item[field])):
                    raise OperationalPatternError(f"{field} contains duplicates in {pattern_id}")
                if any(not isinstance(value, str) or not value.strip() for value in item[field]):
                    raise OperationalPatternError(f"{field} contains invalid text in {pattern_id}")
            for field in ("sectionAr", "sourceTextAr", "titleAr", "originalClassificationAr",
                          "originalDeliveryModelAr", "acceptanceCriteriaAr", "classificationRationaleAr"):
                if not isinstance(item.get(field), str) or not item[field].strip():
                    raise OperationalPatternError(f"{field} is empty in {pattern_id}")
            if not item.get("acceptanceCriteriaAr"):
                raise OperationalPatternError(f"acceptance criteria missing in {pattern_id}")
            frequencies = item.get("reviewFrequencies")
            if (not isinstance(frequencies, list) or len(frequencies) != len(set(frequencies))
                    or any(value not in REVIEW_FREQUENCIES for value in frequencies)):
                raise OperationalPatternError(f"invalid review frequencies in {pattern_id}")
            if item.get("deliveryArchetype") not in DELIVERY_ARCHETYPES:
                raise OperationalPatternError(f"invalid delivery archetype in {pattern_id}")
            if item.get("effortSize") not in EFFORT_SIZES or item.get("complexity") not in COMPLEXITIES:
                raise OperationalPatternError(f"invalid effort classification in {pattern_id}")
            if not isinstance(item.get("requiresSplit"), bool) or not isinstance(item.get("safetyReviewRequired"), bool):
                raise OperationalPatternError(f"invalid governance flags in {pattern_id}")
            if item.get("safetyReviewRequired") and not item.get("safetyNoteAr"):
                raise OperationalPatternError(f"safety note missing in {pattern_id}")
            if not item.get("safetyReviewRequired") and item.get("safetyNoteAr") is not None:
                raise OperationalPatternError(f"unexpected safety note in {pattern_id}")
            confidence = item.get("classificationConfidence")
            if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= confidence <= 1:
                raise OperationalPatternError(f"invalid classification confidence in {pattern_id}")
            if item.get("requiresHumanReview") is not True:
                raise OperationalPatternError(f"pattern must remain under human review: {pattern_id}")
            if item.get("aiReviewStatus") not in AI_REVIEW_STATUSES:
                raise OperationalPatternError(f"invalid review status in {pattern_id}")
            if not item.get("classificationRationaleAr"):
                raise OperationalPatternError(f"classification rationale missing in {pattern_id}")
            if item.get("priority") not in PRIORITIES:
                raise OperationalPatternError(f"invalid priority in {pattern_id}")
            if item.get("sourcePatternId") != pattern_id:
                raise OperationalPatternError(f"sourcePatternId mismatch in {pattern_id}")
        if rows != list(range(1, len(patterns) + 1)):
            raise OperationalPatternError("source rows must be contiguous and ordered")

    @property
    def metadata(self) -> dict[str, Any]:
        return {
            "libraryId": self.payload["libraryId"],
            "version": self.payload["version"],
            "sha256": self.sha256,
            "authoritative": False,
            "usageLabelAr": self.payload["usageLabelAr"],
            "source": copy.deepcopy(self.payload["source"]),
            "patternCount": len(self.payload["patterns"]),
        }

    def get(self, pattern_id: str) -> dict[str, Any] | None:
        item = self._by_id.get(pattern_id)
        return copy.deepcopy(item) if item else None

    def search(
        self,
        *,
        query: str | None = None,
        artifact_type: str | None = None,
        primary_domain: str | None = None,
        sub_domain: str | None = None,
        safety_review_required: bool | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        if artifact_type is not None and artifact_type not in ARTIFACT_TYPES:
            raise OperationalPatternError(f"invalid artifact_type: {artifact_type}")
        if primary_domain is not None and primary_domain not in PRIMARY_DOMAINS:
            raise OperationalPatternError(f"invalid primary_domain: {primary_domain}")
        if sub_domain is not None and sub_domain not in SUB_DOMAINS:
            raise OperationalPatternError(f"invalid sub_domain: {sub_domain}")
        if sub_domain is not None and primary_domain is not None and sub_domain[:5] != primary_domain:
            raise OperationalPatternError("sub_domain does not belong to primary_domain")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 200:
            raise OperationalPatternError("limit must be between 1 and 200")
        tokens = [token.casefold() for token in re.findall(r"\S+", query or "")]
        results: list[tuple[int, int, dict[str, Any]]] = []
        for item in self.payload["patterns"]:
            if artifact_type and item["recommendedArtifactType"] != artifact_type:
                continue
            if primary_domain and item["primaryDomain"] != primary_domain:
                continue
            if sub_domain and item["subDomain"] != sub_domain:
                continue
            if safety_review_required is not None and item["safetyReviewRequired"] != safety_review_required:
                continue
            haystack = " ".join(
                [
                    item["titleAr"], item["sourceTextAr"], item["originalClassificationAr"],
                    item["originalDeliveryModelAr"], item["acceptanceCriteriaAr"],
                    *item["ownerRoles"], *item["implementationActions"], *item["evidenceExamples"],
                ]
            ).casefold()
            if tokens and not all(token in haystack for token in tokens):
                continue
            score = sum(haystack.count(token) for token in tokens)
            result = copy.deepcopy(item)
            result["matchScore"] = score
            results.append((-score, item["sourceRow"], result))
        results.sort(key=lambda row: (row[0], row[1]))
        return [row[2] for row in results[:limit]]
