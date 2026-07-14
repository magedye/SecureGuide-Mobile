"""Contract tests for the adopted artifact-type policy."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.validate_artifact_type_guidance import validate


ROOT = Path(__file__).resolve().parent.parent


class ArtifactTypeGuidanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.guidance = json.loads(
            (ROOT / "reference" / "artifact_type_guidance_v1.json").read_text(
                encoding="utf-8"
            )
        )

    def test_guidance_matches_normative_references(self) -> None:
        self.assertEqual(validate(), [])

    def test_ambiguous_operational_terms_are_not_new_enum_values(self) -> None:
        by_id = {item["termId"]: item for item in self.guidance["practicalTerms"]}
        for term_id in (
            "GOVERNANCE", "WORK_INSTRUCTION", "MONITORING", "REVIEW",
            "ASSESSMENT", "TESTING", "RISK_MANAGEMENT", "AWARENESS_TRAINING",
            "CORRECTIVE_ACTION",
        ):
            self.assertNotEqual(by_id[term_id]["mappingKind"], "DIRECT")
        self.assertNotIn("ART-REVIEW", {item["code"] for item in self.guidance["artifactTypes"]})
        self.assertNotIn("ART-TEST", {item["code"] for item in self.guidance["artifactTypes"]})

    def test_direct_terms_have_one_canonical_type(self) -> None:
        direct = {
            item["termId"]: item["candidateTypes"]
            for item in self.guidance["practicalTerms"]
            if item["mappingKind"] == "DIRECT"
        }
        self.assertEqual(direct["POLICY"], ["ART-POL"])
        self.assertEqual(direct["STANDARD"], ["ART-STD"])
        self.assertEqual(direct["PROCESS"], ["ART-PRO"])
        self.assertEqual(direct["PROCEDURE"], ["ART-PRC"])
        self.assertEqual(direct["EVIDENCE"], ["ART-EVD"])
        self.assertEqual(direct["METRIC"], ["ART-MET"])


if __name__ == "__main__":
    unittest.main()
