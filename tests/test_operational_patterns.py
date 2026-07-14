"""Tests for governed, read-only operational implementation patterns."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from secureguide import SecureGuideService
from secureguide.blueprints import OperationalPatternError, OperationalPatternLibrary
from secureguide.errors import ValidationError


ROOT = Path(__file__).resolve().parent.parent
LIBRARY_PATH = ROOT / "reference" / "operational_patterns_v1.json"


class OperationalPatternLibraryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.library = OperationalPatternLibrary(LIBRARY_PATH)

    def test_library_is_traceable_non_authoritative_and_under_review(self) -> None:
        self.assertEqual(self.library.metadata["patternCount"], 59)
        self.assertFalse(self.library.metadata["authoritative"])
        self.assertFalse(self.library.metadata["source"]["isOriginalRequirementSource"])
        self.assertRegex(self.library.metadata["sha256"], r"^[0-9a-f]{64}$")
        self.assertTrue(all(
            item["requiresHumanReview"] and item["aiReviewStatus"] == "AIR-HUMAN-REVIEW"
            for item in self.library.search(limit=200)
        ))

    def test_search_supports_text_and_governed_filters(self) -> None:
        pam_ids = {item["patternId"] for item in self.library.search(query="PAM")}
        self.assertTrue({"OPP-012", "OPP-019", "OPP-028", "OPP-031"}.issubset(pam_ids))
        iptables = self.library.search(query="iptables")
        self.assertEqual([item["patternId"] for item in iptables], ["OPP-053"])
        self.assertTrue(iptables[0]["safetyReviewRequired"])
        hardening = self.library.search(sub_domain="SD-04.03", limit=200)
        self.assertTrue(hardening)
        self.assertTrue(all(item["subDomain"] == "SD-04.03" for item in hardening))
        self.assertEqual(len(self.library.search(safety_review_required=True, limit=200)), 14)

    def test_compound_patterns_remain_flagged_for_split(self) -> None:
        patterns = self.library.search(limit=200)
        self.assertEqual(sum(item["requiresSplit"] for item in patterns), 12)
        compound = self.library.get("OPP-051")
        self.assertIsNotNone(compound)
        self.assertTrue(compound["requiresSplit"])
        self.assertLessEqual(compound["classificationConfidence"], 0.70)

    def test_type_conditional_fields_follow_usacm(self) -> None:
        patterns = self.library.search(limit=200)
        for item in patterns:
            if item["recommendedArtifactType"] in {"ART-CTR", "ART-CTE"}:
                self.assertIsNotNone(item["controlNature"])
                self.assertIsNotNone(item["controlFunction"])
                self.assertIsNotNone(item["testability"])
            else:
                self.assertIsNone(item["controlNature"])
                self.assertIsNone(item["controlFunction"])
                self.assertIsNone(item["testability"])
            if item["recommendedArtifactType"] == "ART-REQ":
                self.assertIsNotNone(item["requirementType"])
            else:
                self.assertIsNone(item["requirementType"])

    def test_invalid_filters_and_duplicate_json_keys_are_rejected(self) -> None:
        with self.assertRaisesRegex(OperationalPatternError, "invalid artifact_type"):
            self.library.search(artifact_type="CONTROL")
        with self.assertRaisesRegex(OperationalPatternError, "does not belong"):
            self.library.search(primary_domain="SD-03", sub_domain="SD-04.01")
        with self.assertRaisesRegex(OperationalPatternError, "limit"):
            self.library.search(limit=0)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "duplicate.json"
            path.write_text('{"libraryId":"x","libraryId":"y"}', encoding="utf-8")
            with self.assertRaisesRegex(OperationalPatternError, "duplicate JSON key"):
                OperationalPatternLibrary(path)

    def test_service_search_is_read_only_and_does_not_create_database(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            database_path = Path(temp) / "must-not-be-created.db"
            service = SecureGuideService(database_path, operational_patterns=self.library)
            result = service.search_operational_patterns(query="Zero Trust")
            self.assertEqual([item["patternId"] for item in result["results"]], ["OPP-051"])
            self.assertFalse(database_path.exists())
            with self.assertRaises(ValidationError):
                service.search_operational_patterns(artifact_type="ART-CONTROL")


if __name__ == "__main__":
    unittest.main()
