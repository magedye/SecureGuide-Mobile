"""Governance and schema gate for the non-authoritative pattern library."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from secureguide.blueprints import OperationalPatternLibrary  # noqa: E402


LIBRARY_PATH = ROOT / "reference" / "operational_patterns_v1.json"
SCHEMA_PATH = ROOT / "reference" / "operational_pattern_schema_v1.json"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def controlled_values(payload: dict[str, Any], key: str) -> set[str]:
    return {item["code"] for item in payload[key]["values"]}


def validate() -> list[str]:
    errors: list[str] = []
    schema = load(SCHEMA_PATH)
    payload = load(LIBRARY_PATH)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    for error in sorted(validator.iter_errors(payload), key=lambda item: list(item.path)):
        location = ".".join(str(part) for part in error.path) or "$"
        errors.append(f"schema {location}: {error.message}")

    # The runtime loader adds duplicate-key checks and semantic USACM/SDT checks.
    try:
        library = OperationalPatternLibrary(LIBRARY_PATH)
    except ValueError as exc:
        errors.append(f"runtime loader: {exc}")
        return errors

    controlled = load(ROOT / "reference" / "usacm_controlled_lists.json")
    artifact_types = controlled_values(controlled, "ARTIFACT_TYPE")
    natures = controlled_values(controlled, "CONTROL_NATURE")
    functions = controlled_values(controlled, "CONTROL_FUNCTION")
    testability_values = controlled_values(controlled, "TESTABILITY")
    requirement_types = controlled_values(controlled, "REQUIREMENT_TYPE")
    priorities = controlled_values(controlled, "PRIORITY")
    review_statuses = controlled_values(controlled, "AI_REVIEW_STATUS")
    frequencies = controlled_values(controlled, "REVIEW_FREQUENCY")
    taxonomy = load(ROOT / "reference" / "sdt_taxonomy.json")
    subdomain_parent = {
        subdomain["code"]: domain["code"]
        for domain in taxonomy
        for subdomain in domain["sub_domains"]
    }

    patterns = payload.get("patterns", [])
    if len(patterns) != 59 or [item.get("sourceRow") for item in patterns] != list(range(1, 60)):
        errors.append("library must preserve source rows 1..59 exactly")
    if library.metadata["patternCount"] != 59:
        errors.append("runtime metadata pattern count must be 59")
    if payload.get("authoritative") is not False:
        errors.append("library must remain non-authoritative")
    if payload.get("source", {}).get("isOriginalRequirementSource") is not False:
        errors.append("source must not be marked as an original requirement source")

    for item in patterns:
        pattern_id = item.get("patternId", "<unknown>")
        artifact_type = item.get("recommendedArtifactType")
        nature = item.get("controlNature")
        function = item.get("controlFunction")
        testability = item.get("testability")
        requirement_type = item.get("requirementType")
        if artifact_type not in artifact_types:
            errors.append(f"{pattern_id}: non-canonical artifact type")
        if item.get("subDomain") not in subdomain_parent:
            errors.append(f"{pattern_id}: unknown SDT subdomain")
        elif subdomain_parent[item["subDomain"]] != item.get("primaryDomain"):
            errors.append(f"{pattern_id}: SDT parent mismatch")
        if artifact_type in {"ART-CTR", "ART-CTE"}:
            if (nature not in natures or function not in functions
                    or testability not in testability_values):
                errors.append(f"{pattern_id}: control requires nature, function, and testability")
        elif nature is not None or function is not None or testability is not None:
            errors.append(f"{pattern_id}: non-control must not carry control-only fields")
        if artifact_type == "ART-REQ":
            if requirement_type not in requirement_types:
                errors.append(f"{pattern_id}: requirement requires canonical requirementType")
        elif requirement_type is not None:
            errors.append(f"{pattern_id}: non-requirement must not carry requirementType")
        if item.get("priority") not in priorities:
            errors.append(f"{pattern_id}: non-canonical priority")
        if item.get("aiReviewStatus") not in review_statuses:
            errors.append(f"{pattern_id}: non-canonical review status")
        if item.get("requiresHumanReview") is not True:
            errors.append(f"{pattern_id}: pattern must remain under human review")
        confidence = item.get("classificationConfidence")
        if isinstance(confidence, (int, float)) and confidence <= 0.70:
            if item.get("aiReviewStatus") != "AIR-HUMAN-REVIEW":
                errors.append(f"{pattern_id}: low confidence must route to human review")
        if any(value not in frequencies for value in item.get("reviewFrequencies", [])):
            errors.append(f"{pattern_id}: non-canonical review frequency")

    if sum(bool(item.get("requiresSplit")) for item in patterns) != 12:
        errors.append("expected exactly 12 compound patterns requiring split")
    if sum(bool(item.get("safetyReviewRequired")) for item in patterns) != 14:
        errors.append("expected exactly 14 safety-sensitive patterns")
    if any(not next(item for item in patterns if item["sourceRow"] == row)["safetyReviewRequired"]
           for row in (53, 54, 55, 56, 57, 58, 59)):
        errors.append("incident-cleanup and host-firewall rows 53..59 must require safety review")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"FAIL - {error}")
        return 1
    print("PASS - JSON Schema and runtime semantic validation")
    print("PASS - 59 traceable non-authoritative operational patterns")
    print("PASS - 12 split-required and 14 safety-review patterns")
    print("PASS - USACM controlled values and all 40 SDT subdomains enforced")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
