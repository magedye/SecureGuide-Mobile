"""Tests for the pure HTML report renderer and its service/CLI wiring."""

from __future__ import annotations

import argparse
import tempfile
import unittest
from pathlib import Path

from secureguide import Database, SecureGuideService, apply_migrations
from secureguide.cli import run
from secureguide.errors import ValidationError
from secureguide.reporting import render_report_html
from tests.test_profile_workflow import seed_catalog


ROOT = Path(__file__).resolve().parent.parent


class ReportRendererUnitTests(unittest.TestCase):
    """The renderer is a pure function over the report dict — no DB required."""

    def test_escapes_untrusted_text_and_renders_structure(self) -> None:
        report = {
            "formula_version": "profile-score-v1",
            "generated_at": "2026-07-15T00:00:00+00:00",
            "profile": {"id": "P1", "name": "<script>alert(1)</script>"},
            "summary": {
                "counts": {"implemented_full": 3},
                "score": {"overall": 72.5, "band": "متقدم"},
                "gap_count": 2,
                "approved_blueprint_count": 1,
                "open_task_count": 4,
                "review_queue_count": 1,
            },
            "gaps": [],
            "approved_blueprints": [],
            "approved_blueprint_enrichments": [],
            "tasks": [],
            "templates": [],
        }
        document = render_report_html(report)
        self.assertTrue(document.lstrip().startswith("<!doctype html>"))
        self.assertIn('dir="rtl"', document)
        self.assertIn("72.5%", document)
        self.assertIn("متقدم", document)
        # The malicious profile name must be escaped, not emitted as a live tag.
        self.assertNotIn("<script>alert(1)</script>", document)
        self.assertIn("&lt;script&gt;", document)
        self.assertIn("لا توجد خطط معتمدة بعد.", document)

    def test_renders_enrichment_lineage_under_approved_blueprint(self) -> None:
        report = {
            "formula_version": "profile-score-v1",
            "generated_at": "2026-07-15T00:00:00+00:00",
            "profile": {"id": "P1", "name": "المقر"},
            "summary": {"counts": {}, "score": {}},
            "gaps": [],
            "approved_blueprints": [
                {"id": "ABP-1", "artifact_title_ar": "إدارة الهوية", "version": 1,
                 "action_count": 2, "evidence_count": 1, "task_count": 2,
                 "approved_by": "approver", "approved_at": "2026-07-15"},
            ],
            "approved_blueprint_enrichments": [
                {"blueprint_id": "ABP-1", "source_pattern_id": "OPP-007",
                 "safety_review_required": 1, "selection_reason": "ضبط التغيير"},
            ],
            "tasks": [],
            "templates": [],
        }
        document = render_report_html(report)
        self.assertIn("OPP-007", document)
        self.assertIn("اقتراحات معيارية بناءً على التصنيف", document)
        self.assertIn("ضبط التغيير", document)
        self.assertIn("⚠", document)


class ReportHtmlIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "report.db"
        apply_migrations(self.path, ROOT / "migrations")
        seed_catalog(self.path)
        self.service = SecureGuideService(Database(self.path))
        self.service.create_profile(name="المقر الرئيسي", profile_id="P1", activate=True)
        self.service.select_artifacts(["A-IDENTITY"], profile_id="P1", selected_by="selector")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _approve_enriched_blueprint(self) -> dict:
        draft = self.service.create_blueprint_draft(
            "A-IDENTITY", profile_id="P1", created_by="author"
        )
        library_first = self.service.search_operational_patterns(limit=1)["results"][0]
        self.service.enrich_blueprint_from_pattern(
            draft["id"], profile_id="P1", pattern_id=library_first["patternId"],
            selected_by="author", selection_reason="نمط مرجعي للهوية",
        )
        self.service.submit_blueprint(draft["id"], profile_id="P1", submitted_by="author")
        return self.service.approve_blueprint(
            draft["id"], profile_id="P1", approved_by="approver"
        )

    def test_service_report_html_shows_only_approved_with_lineage(self) -> None:
        approved = self._approve_enriched_blueprint()
        # A second draft that never gets approved must not surface in the report.
        self.service.select_artifacts(["A-LOGGING"], profile_id="P1", selected_by="selector")
        self.service.create_blueprint_draft("A-LOGGING", profile_id="P1", created_by="author")

        report = self.service.report(profile_id="P1")
        self.assertEqual(report["summary"]["approved_blueprint_count"], 1)
        self.assertEqual(len(report["approved_blueprint_enrichments"]), 1)

        document = self.service.report_html(profile_id="P1")
        self.assertIn("<!doctype html>", document)
        self.assertIn("المقر الرئيسي", document)
        self.assertIn(approved["pattern_enrichments"][0]["source_pattern_id"], document)
        self.assertIn("الخطط المعتمدة", document)
        self.assertIn("التقرير الرسمي", document)

    def test_cli_html_export_writes_file_and_requires_output(self) -> None:
        self._approve_enriched_blueprint()
        out = Path(self.temp.name) / "report.html"
        result = run(argparse.Namespace(
            db=str(self.path), command="report", profile="P1",
            output=str(out), format="html",
        ))
        self.assertEqual(result["format"], "html")
        self.assertTrue(out.exists())
        document = out.read_text(encoding="utf-8")
        self.assertIn("<!doctype html>", document)
        self.assertIn("تقرير الامتثال", document)

        with self.assertRaises(ValidationError):
            run(argparse.Namespace(
                db=str(self.path), command="report", profile="P1",
                output=None, format="html",
            ))


if __name__ == "__main__":
    unittest.main()
