"""End-to-end integration tests for the enterprise-profile operational slice."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from secureguide import Database, SecureGuideService, apply_migrations
from secureguide.database import connect
from secureguide.errors import ActiveProfileRequiredError, ValidationError


ROOT = Path(__file__).resolve().parent.parent


def seed_catalog(path: Path) -> None:
    conn = connect(path)
    try:
        artifacts = [
            ("A-IDENTITY", "Identity governance", "SD-03", "SD-03.03", "PRI-CRITICAL", 10),
            ("A-LOGGING", "Security logging", "SD-06", "SD-06.01", "PRI-HIGH", 7),
            ("A-BACKUP", "Backup restoration", "SD-07", "SD-07.03", "PRI-MEDIUM", 4),
            ("A-POLICY", "Security policy", "SD-01", "SD-01.02", "PRI-LOW", 1),
        ]
        for artifact_id, title, domain, sub_domain, priority, weight in artifacts:
            conn.execute(
                """INSERT INTO security_artifacts(
                       id,type,title_en,definition_short_en,primary_domain,sub_domain,
                       abstraction_level,source,source_type,obligation_level,
                       granularity_level,control_nature,control_function,testability,
                       priority,priority_weight,publication_status,source_document,
                       ai_review_status,requires_human_review)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    artifact_id,
                    "ART-CTR",
                    title,
                    f"Implement {title.lower()} controls.",
                    domain,
                    sub_domain,
                    "ABS-CTR",
                    "SRC-STD",
                    "STANDARD",
                    "OBL-MND",
                    "GRN-DETAILED",
                    "NAT-TEC",
                    "FUN-PRE",
                    "TST-MAN",
                    priority,
                    weight,
                    "APPROVED",
                    "integration-test",
                    "AIR-HUMAN-APPROVED",
                    0,
                ),
            )
        conn.execute(
            "INSERT INTO artifact_tags(artifact_id,tag_type,tag_value) VALUES ('A-IDENTITY','Technology','Active Directory')"
        )
        conn.execute(
            """INSERT INTO artifact_applicability_scope(artifact_id,scope_type,scope_value)
               VALUES ('A-IDENTITY','ENTITY_TYPE','Windows-managed environment')"""
        )
        conn.execute(
            """INSERT INTO templates(id,name,version,scope_note)
               VALUES ('TPL-BASE','Baseline','2.0','General enterprise baseline')"""
        )
        conn.execute(
            """INSERT INTO template_items(
                   id,template_id,artifact_id,inclusion_status,inclusion_reason,
                   priority_override,review_frequency_override)
               VALUES ('TI-LOG','TPL-BASE','A-LOGGING','MANDATORY','Detection baseline',
                       'PRI-HIGH','MONTHLY')"""
        )
        conn.execute(
            """INSERT INTO template_items(
                   id,template_id,artifact_id,inclusion_status,inclusion_reason,
                   priority_override,review_frequency_override)
               VALUES ('TI-BACKUP','TPL-BASE','A-BACKUP','OPTIONAL','Recovery enhancement',
                       'PRI-MEDIUM','QUARTERLY')"""
        )
    finally:
        conn.close()


class ProfileWorkflowIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / "workflow.db"
        applied = apply_migrations(self.db_path, ROOT / "migrations")
        self.assertIn("021", applied)
        seed_catalog(self.db_path)
        self.service = SecureGuideService(Database(self.db_path))

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_complete_profile_workflow_and_profile_isolation(self) -> None:
        p1 = self.service.create_profile(
            profile_id="P1", name="Head Office", profile_kind="organization", activate=True
        )
        p2 = self.service.create_profile(
            profile_id="P2", name="Cloud Audit", profile_kind="audit"
        )
        self.assertEqual("P1", self.service.active_profile()["id"])

        manual = self.service.select_artifacts(
            ["A-IDENTITY"], selected_by="analyst", selection_reason="Critical identity scope"
        )
        self.assertEqual(1, manual["created"])
        template = self.service.apply_template("TPL-BASE", applied_by="analyst")
        self.assertEqual(1, template["eligible_items"])
        self.assertEqual(1, template["created"])
        self.assertTrue(template["application_recorded"])
        repeated = self.service.apply_template("TPL-BASE", applied_by="analyst")
        self.assertEqual(0, repeated["created"])
        self.assertEqual(0, repeated["origins_added"])

        self.service.select_artifacts(["A-BACKUP"], selected_by="analyst")
        assessment = self.service.assess_artifact(
            "A-IDENTITY",
            assessor_name="auditor",
            implementation_status="STS-FULL",
            verification_status="VER-PASS",
            effectiveness="EFF-HIGH",
            assigned_owner="IAM Team",
            score=100,
            comments="Verified configuration and review records.",
        )
        evidence = self.service.add_evidence(
            "A-IDENTITY",
            evidence_type="REPORT",
            assessment_id=assessment["id"],
            evidence_url="evidence://iam-review.pdf",
            description="Quarterly access review report",
            title="IAM access review",
            collected_by="auditor",
            content_hash="A" * 64,
            mime_type="application/pdf",
        )
        self.assertEqual(assessment["id"], evidence["assessment_id"])

        deferred = self.service.create_exception(
            "A-LOGGING",
            exception_status="EXC-DEFERRED",
            justification="SIEM procurement completes next quarter.",
        )
        self.service.submit_exception(deferred["id"])
        self.service.approve_exception(
            deferred["id"],
            approved_by="CISO",
            approval_date="2026-07-14",
            expiry_date="2026-12-31",
        )
        not_applicable = self.service.create_exception(
            "A-BACKUP",
            exception_status="EXC-NOT-APPLICABLE",
            justification="No data is stored in the assessment-only scope.",
        )
        self.service.submit_exception(not_applicable["id"])
        self.service.approve_exception(
            not_applicable["id"],
            approved_by="Audit Owner",
            approval_date="2026-07-14",
            expiry_date="2027-07-14",
        )

        dashboard = self.service.dashboard()
        self.assertEqual("P1", dashboard["profile"]["id"])
        self.assertEqual(3, dashboard["counts"]["total_items"])
        self.assertEqual(2, dashboard["counts"]["applicable_items"])
        self.assertEqual(1, dashboard["counts"]["open_gaps"])
        self.assertEqual("profile-score-v1", dashboard["score"]["formula_version"])
        self.assertEqual(["A-LOGGING"], [gap["artifact_id"] for gap in dashboard["gaps"]])

        p1_full = self.service.search_catalog(
            filters={"implementation_status": "STS-FULL"}, selected_only=True
        )
        self.assertEqual(["A-IDENTITY"], [row["id"] for row in p1_full])
        tagged = self.service.search_catalog(
            query="identity", filters={"tag_type": "Technology", "tag_value": "Active Directory"}
        )
        self.assertEqual(["A-IDENTITY"], [row["id"] for row in tagged])

        self.service.activate_profile(p2["id"])
        self.service.select_artifacts(["A-IDENTITY"], selected_by="cloud-auditor")
        p2_full = self.service.search_catalog(
            filters={"implementation_status": "STS-FULL"}, selected_only=True
        )
        self.assertEqual([], p2_full)
        p2_dashboard = self.service.dashboard()
        self.assertEqual(1, p2_dashboard["counts"]["total_items"])
        self.assertEqual(0, p2_dashboard["counts"]["implemented_full"])

        with self.assertRaises(ValidationError):
            self.service.add_evidence(
                "A-IDENTITY",
                evidence_type="REPORT",
                assessment_id=assessment["id"],
                description="must not cross profile-artifact boundary",
                collected_by="cloud-auditor",
            )

        p1_report = self.service.report(profile_id=p1["id"])
        self.assertEqual(3, len(p1_report["items"]))
        self.assertEqual(1, len(p1_report["templates"]))
        self.assertEqual("profile-score-v1", p1_report["formula_version"])

        conn = connect(self.db_path)
        try:
            reference_state = conn.execute(
                """SELECT implementation_status,verification_status,effectiveness,exception_status
                     FROM security_artifacts WHERE id='A-IDENTITY'"""
            ).fetchone()
            self.assertEqual(
                ("STS-NOT-APPLIED", "VER-NOT-VERIFIED", "EFF-UNKNOWN", "EXC-NONE"),
                tuple(reference_state),
            )
            origins = conn.execute(
                """SELECT origin_type,COUNT(*) FROM profile_artifact_origins o
                     JOIN profile_artifacts pa ON pa.id=o.profile_artifact_id
                    WHERE pa.profile_id='P1' GROUP BY origin_type ORDER BY origin_type"""
            ).fetchall()
            self.assertEqual([("MANUAL", 2), ("TEMPLATE", 1)], [tuple(row) for row in origins])
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute(
                    "UPDATE profile_assessments SET comments='rewritten' WHERE id=?",
                    (assessment["id"],),
                )
            self.assertEqual(0, conn.execute("SELECT COUNT(*) FROM v_profile_evidence_integrity_issues").fetchone()[0])
            self.assertEqual("ok", conn.execute("PRAGMA integrity_check").fetchone()[0])
            self.assertEqual([], conn.execute("PRAGMA foreign_key_check").fetchall())
        finally:
            conn.close()

    def test_active_profile_required_for_operational_writes(self) -> None:
        self.service.create_profile(profile_id="P1", name="Unselected")
        with self.assertRaises(ActiveProfileRequiredError):
            self.service.select_artifacts(["A-POLICY"], selected_by="analyst")

    def test_user_priority_override_survives_template_reapplication(self) -> None:
        self.service.create_profile(profile_id="P1", name="Profile", activate=True)
        self.service.apply_template("TPL-BASE", applied_by="analyst")
        self.service.assess_artifact(
            "A-LOGGING", assessor_name="owner", priority_override="PRI-LOW"
        )
        self.service.apply_template("TPL-BASE", applied_by="analyst")
        row = self.service.search_catalog(
            query="logging", selected_only=True
        )[0]
        self.assertEqual("PRI-LOW", row["effective_priority"])
        conn = connect(self.db_path)
        try:
            conn.execute("UPDATE templates SET version='2.1' WHERE id='TPL-BASE'")
        finally:
            conn.close()
        versioned = self.service.apply_template("TPL-BASE", applied_by="analyst")
        self.assertTrue(versioned["application_recorded"])
        self.assertEqual(1, versioned["origins_added"])
        conn = connect(self.db_path)
        try:
            self.assertEqual(
                2,
                conn.execute(
                    "SELECT COUNT(*) FROM profile_templates WHERE profile_id='P1'"
                ).fetchone()[0],
            )
            self.assertEqual(
                2,
                conn.execute(
                    """SELECT COUNT(*) FROM profile_artifact_origins o
                         JOIN profile_artifacts pa ON pa.id=o.profile_artifact_id
                        WHERE pa.profile_id='P1' AND pa.artifact_id='A-LOGGING'
                          AND o.origin_type='TEMPLATE'"""
                ).fetchone()[0],
            )
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
