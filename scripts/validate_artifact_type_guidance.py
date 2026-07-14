"""Validate artifact-type guidance against the USACM controlled list."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate() -> list[str]:
    errors: list[str] = []
    controlled = load(ROOT / "reference" / "usacm_controlled_lists.json")
    guidance = load(ROOT / "reference" / "artifact_type_guidance_v1.json")
    canonical = [item["code"] for item in controlled["ARTIFACT_TYPE"]["values"]]
    documented = [item["code"] for item in guidance["artifactTypes"]]
    if documented != canonical:
        errors.append("artifactTypes must match USACM order and values exactly")
    if len(set(documented)) != len(documented):
        errors.append("artifactTypes contains duplicate codes")

    term_ids: set[str] = set()
    allowed_kinds = {"DIRECT", "CONTEXTUAL", "SPLIT_REQUIRED"}
    for term in guidance.get("practicalTerms", []):
        term_id = term.get("termId")
        if term_id in term_ids:
            errors.append(f"duplicate practical term: {term_id}")
        term_ids.add(term_id)
        if term.get("mappingKind") not in allowed_kinds:
            errors.append(f"invalid mappingKind for {term_id}")
        candidates = term.get("candidateTypes", [])
        if not candidates or any(code not in canonical for code in candidates):
            errors.append(f"invalid candidateTypes for {term_id}")
        if term.get("mappingKind") == "DIRECT" and len(candidates) != 1:
            errors.append(f"DIRECT mapping must have one candidate: {term_id}")

    required_terms = {
        "GOVERNANCE", "POLICY", "STANDARD", "CONTROL", "PROCESS", "PROCEDURE",
        "WORK_INSTRUCTION", "MONITORING", "REVIEW", "ASSESSMENT", "TESTING",
        "RISK_MANAGEMENT", "EXTERNAL_COMPLIANCE", "AWARENESS_TRAINING",
        "EXCEPTION", "EVIDENCE", "METRIC", "CORRECTIVE_ACTION",
    }
    if term_ids != required_terms:
        errors.append(f"practical term coverage mismatch: {sorted(term_ids ^ required_terms)}")

    authoring = (ROOT / "docs" / "AUTHORING_POLICY.md").read_text(encoding="utf-8")
    policy = (ROOT / "docs" / "ARTIFACT_TYPE_POLICY.md").read_text(encoding="utf-8")
    for code in canonical:
        if code not in authoring:
            errors.append(f"AUTHORING_POLICY missing {code}")
        if code not in policy:
            errors.append(f"ARTIFACT_TYPE_POLICY missing {code}")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"FAIL - {error}")
        return 1
    print("PASS - artifact-type guidance matches all 22 USACM types")
    print("PASS - 18 practical terms map only to canonical ART-* values")
    print("PASS - authoring and selection policies document every type")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
