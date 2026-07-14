"""Tests for reversible, provenance-preserving pattern enrichment of draft blueprints."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from secureguide import Database, SecureGuideService, apply_migrations
from secureguide.blueprints import OperationalPatternLibrary
from secureguide.database import connect
from secureguide.errors import NotFoundError, ValidationError
from tests.test_profile_workflow import seed_catalog


ROOT = Path(__file__).resolve().parent.parent


class BlueprintPatternEnrichmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "enrichment.db"
        applied = apply_migrations(self.path, ROOT / "migrations")
        self.assertIn("024", applied)
        seed_catalog(self.path)
        self.service = SecureGuideService(Database(self.path))
        self.service.create_profile(name="Profile One", profile_id="P1", activate=True)
        self.service.create_profile(name="Profile Two", profile_id="P2")
        for profile_id in ("P1", "P2"):
            self.service.select_artifacts(
                ["A-IDENTITY"], profile_id=profile_id, selected_by="selector"
            )
        library = OperationalPatternLibrary()
        self.library_meta = library.metadata
        self.safe_pattern = library.search(safety_review_required=False, limit=1)[0]
        self.risky_pattern = library.search(safety_review_required=True, limit=1)[0]

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _draft(self, profile_id: str = "P1") -> dict:
        return self.service.create_blueprint_draft(
            "A-IDENTITY", profile_id=profile_id, created_by="author"
        )

    def test_enrichment_stores_full_provenance_and_frozen_copy(self) -> None:
        draft = self._draft()
        pattern_id = self.safe_pattern["patternId"]
        detail = self.service.enrich_blueprint_from_pattern(
            draft["id"],
            profile_id="P1",
            pattern_id=pattern_id,
            selected_by="author",
            selection_reason="Reuse a proven identity rollout example",
            copied_text_ar="نص معدّل من المؤلف يخص هذا الملف",
        )
        self.assertEqual(len(detail["pattern_enrichments"]), 1)
        enrichment = detail["pattern_enrichments"][0]
        self.assertEqual(enrichment["source_pattern_id"], pattern_id)
        self.assertEqual(enrichment["library_version"], self.library_meta["version"])
        self.assertEqual(enrichment["library_sha256"], self.library_meta["sha256"])
        self.assertEqual(len(enrichment["library_sha256"]), 64)
        self.assertEqual(enrichment["selected_by"], "author")
        self.assertEqual(
            enrichment["selection_reason"], "Reuse a proven identity rollout example"
        )
        # Frozen copy after the author's edit, not a live reference to the library.
        self.assertEqual(enrichment["copied_text_ar"], "نص معدّل من المؤلف يخص هذا الملف")
        self.assertNotEqual(enrichment["copied_text_ar"], self.safe_pattern["sourceTextAr"])
        self.assertEqual(enrichment["copied_title_ar"], self.safe_pattern["titleAr"])
        events = [e for e in detail["pattern_enrichment_events"] if e["event_type"] == "ADDED"]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["actor"], "author")

    def test_duplicate_pattern_enrichment_is_rejected(self) -> None:
        draft = self._draft()
        pattern_id = self.safe_pattern["patternId"]
        self.service.enrich_blueprint_from_pattern(
            draft["id"], profile_id="P1", pattern_id=pattern_id,
            selected_by="author", selection_reason="first",
        )
        with self.assertRaises(ValidationError):
            self.service.enrich_blueprint_from_pattern(
                draft["id"], profile_id="P1", pattern_id=pattern_id,
                selected_by="author", selection_reason="second",
            )

    def test_safety_pattern_requires_explicit_acknowledgement(self) -> None:
        draft = self._draft()
        pattern_id = self.risky_pattern["patternId"]
        with self.assertRaises(ValidationError):
            self.service.enrich_blueprint_from_pattern(
                draft["id"], profile_id="P1", pattern_id=pattern_id,
                selected_by="author", selection_reason="needs change control",
            )
        detail = self.service.enrich_blueprint_from_pattern(
            draft["id"], profile_id="P1", pattern_id=pattern_id,
            selected_by="author", selection_reason="needs change control",
            safety_acknowledged=True,
        )
        enrichment = detail["pattern_enrichments"][0]
        self.assertEqual(enrichment["safety_review_required"], 1)
        self.assertEqual(enrichment["safety_acknowledged"], 1)
        self.assertEqual(enrichment["safety_note_ar"], self.risky_pattern["safetyNoteAr"])

    def test_missing_reason_and_unknown_pattern(self) -> None:
        draft = self._draft()
        with self.assertRaises(ValidationError):
            self.service.enrich_blueprint_from_pattern(
                draft["id"], profile_id="P1",
                pattern_id=self.safe_pattern["patternId"],
                selected_by="author", selection_reason="   ",
            )
        with self.assertRaises(NotFoundError):
            self.service.enrich_blueprint_from_pattern(
                draft["id"], profile_id="P1", pattern_id="OPP-999",
                selected_by="author", selection_reason="unknown pattern",
            )

    def test_reversal_keeps_append_only_audit_trail(self) -> None:
        draft = self._draft()
        detail = self.service.enrich_blueprint_from_pattern(
            draft["id"], profile_id="P1",
            pattern_id=self.safe_pattern["patternId"],
            selected_by="author", selection_reason="try it",
        )
        enrichment_id = detail["pattern_enrichments"][0]["id"]
        after = self.service.remove_blueprint_enrichment(
            draft["id"], enrichment_id, profile_id="P1",
            removed_by="author", removal_reason="not a fit after all",
        )
        self.assertEqual(after["pattern_enrichments"], [])
        types = [e["event_type"] for e in after["pattern_enrichment_events"]]
        self.assertEqual(types, ["ADDED", "REMOVED"])
        self.assertEqual(after["pattern_enrichment_events"][-1]["reason"], "not a fit after all")

    def test_enrichment_frozen_and_travels_into_approved_snapshot(self) -> None:
        draft = self._draft()
        detail = self.service.enrich_blueprint_from_pattern(
            draft["id"], profile_id="P1",
            pattern_id=self.safe_pattern["patternId"],
            selected_by="author", selection_reason="carry into approval",
        )
        enrichment_id = detail["pattern_enrichments"][0]["id"]
        self.service.submit_blueprint(draft["id"], profile_id="P1", submitted_by="author")

        # Service refuses enrichment mutation once the blueprint leaves DRAFT.
        with self.assertRaises(ValidationError):
            self.service.enrich_blueprint_from_pattern(
                draft["id"], profile_id="P1",
                pattern_id=self.risky_pattern["patternId"],
                selected_by="author", selection_reason="too late",
                safety_acknowledged=True,
            )
        with self.assertRaises(ValidationError):
            self.service.remove_blueprint_enrichment(
                draft["id"], enrichment_id, profile_id="P1", removed_by="author"
            )
        # The storage layer enforces the same lock directly.
        conn = connect(self.path)
        try:
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute(
                    "DELETE FROM approved_blueprint_pattern_enrichments WHERE id=?",
                    (enrichment_id,),
                )
        finally:
            conn.close()

        approved = self.service.approve_blueprint(
            draft["id"], profile_id="P1", approved_by="approver"
        )
        self.assertEqual(approved["workflow_status"], "APPROVED")
        self.assertEqual(len(approved["pattern_enrichments"]), 1)
        self.assertEqual(approved["pattern_enrichments"][0]["id"], enrichment_id)

    def test_profile_isolation(self) -> None:
        draft = self._draft(profile_id="P1")
        with self.assertRaises(NotFoundError):
            self.service.enrich_blueprint_from_pattern(
                draft["id"], profile_id="P2",
                pattern_id=self.safe_pattern["patternId"],
                selected_by="author", selection_reason="wrong profile",
            )

    def test_governance_view_is_clean(self) -> None:
        draft = self._draft()
        self.service.enrich_blueprint_from_pattern(
            draft["id"], profile_id="P1",
            pattern_id=self.safe_pattern["patternId"],
            selected_by="author", selection_reason="clean",
        )
        self.service.enrich_blueprint_from_pattern(
            draft["id"], profile_id="P1",
            pattern_id=self.risky_pattern["patternId"],
            selected_by="author", selection_reason="clean risky",
            safety_acknowledged=True,
        )
        conn = connect(self.path)
        try:
            issues = conn.execute(
                "SELECT COUNT(*) FROM v_blueprint_enrichment_governance_issues"
            ).fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(issues, 0)


if __name__ == "__main__":
    unittest.main()
