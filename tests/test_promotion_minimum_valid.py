"""Promotion regression tests for minimum-valid versus review status."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts import _promote_common as promotion
from secureguide.database import apply_migrations


class PromotionMinimumTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "promotion.db"
        apply_migrations(self.db)
        self.conn = sqlite3.connect(self.db)
        self.conn.row_factory = sqlite3.Row
        self.valid = promotion.load_valid(self.conn)

    def tearDown(self) -> None:
        self.conn.close()
        self.temp.cleanup()

    def row(self, **overrides: object) -> sqlite3.Row:
        values = {
            "id": "STG-1", "title_en": "Protect accounts",
            "definition_short_en": "Require multi-factor authentication.",
            "proposed_type": "ART-CTR", "proposed_abstraction_level": "ABS-CTR",
            "proposed_primary_domain": "SD-03", "proposed_sub_domain": "SD-03.02",
            "proposed_obligation_level": "OBL-MND", "proposed_control_nature": "NAT-TEC",
            "proposed_control_function": "FUN-PRE", "proposed_testability": "TST-MAN",
            "proposed_mappings_json": '[{"raw_id":"RAW","source_document":"Source","mapping_strength":"DIRECT"}]',
            "classification_confidence": 0.65,
            "classification_rationale": "A technical safeguard.",
            "requires_human_review": 1, "curation_status": "NEEDS_REVIEW",
            "ready_for_promotion": 1, "final_review_status": None,
            "approved_by": None, "approved_at": None, "promotion_blockers": None,
            "proposed_priority": "PRI-MEDIUM",
        }
        values.update(overrides)
        columns = list(values)
        query = "SELECT " + ",".join(f"? AS {column}" for column in columns)
        return self.conn.execute(query, tuple(values[column] for column in columns)).fetchone()

    def test_not_reviewed_low_confidence_can_be_minimum_valid(self) -> None:
        assessment = promotion.promotion_assessment(self.row(), self.valid)
        self.assertTrue(assessment["MINIMUM_CATALOG_VALIDATION"]["valid"])
        self.assertFalse(assessment["STRICT_USACM_CONFORMANCE"]["valid"])

    def test_type_specific_fields_still_block_minimum_entry(self) -> None:
        blockers = promotion.minimum_promotion_blockers(
            self.row(proposed_control_nature=None), self.valid
        )
        self.assertTrue(any("proposed_control_nature" in item for item in blockers))

    def test_human_review_is_claimed_only_with_auditable_evidence(self) -> None:
        incomplete = promotion.strict_review_blockers(
            self.row(final_review_status="APPROVED")
        )
        complete = promotion.strict_review_blockers(self.row(
            final_review_status="APPROVED", approved_by="reviewer",
            approved_at="2026-08-13T00:00:00Z", requires_human_review=0,
            classification_confidence=0.90,
        ))
        self.assertIn("human approval lacks approved_by/approved_at evidence", incomplete)
        self.assertEqual(complete, [])


if __name__ == "__main__":
    unittest.main()
