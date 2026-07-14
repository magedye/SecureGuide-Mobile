"""End-to-end tests for blueprint approval, versioning, and task materialization."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from secureguide import Database, SecureGuideService, apply_migrations
from secureguide.blueprints import BlueprintEngine
from secureguide.database import connect
from secureguide.errors import NotFoundError, ValidationError
from tests.test_profile_workflow import seed_catalog


ROOT = Path(__file__).resolve().parent.parent


class InvalidEvidenceEngine:
    """Valid generation except for one DB-rejected snapshot value."""

    def __init__(self) -> None:
        self.real = BlueprintEngine()

    def generate(self, context):
        blueprint = self.real.generate(context)
        blueprint.evidence[0].evidence_type = "INVALID"
        return blueprint


class BlueprintApprovalWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "blueprint.db"
        applied = apply_migrations(self.path, ROOT / "migrations")
        self.assertIn("023", applied)
        seed_catalog(self.path)
        self.service = SecureGuideService(Database(self.path))
        self.p1 = self.service.create_profile(name="Profile One", profile_id="P1", activate=True)
        self.p2 = self.service.create_profile(name="Profile Two", profile_id="P2")
        for profile_id in ("P1", "P2"):
            self.service.select_artifacts(
                ["A-IDENTITY"], profile_id=profile_id, selected_by="selector"
            )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _approve_identity(self) -> dict:
        draft = self.service.create_blueprint_draft(
            "A-IDENTITY", profile_id="P1", created_by="author"
        )
        submitted = self.service.submit_blueprint(
            draft["id"], profile_id="P1", submitted_by="author"
        )
        self.assertEqual(submitted["workflow_status"], "UNDER_REVIEW")
        return self.service.approve_blueprint(
            draft["id"], profile_id="P1", approved_by="approver"
        )

    def test_complete_workflow_permissions_immutability_and_tasks(self) -> None:
        draft = self.service.create_blueprint_draft(
            "A-IDENTITY",
            profile_id="P1",
            created_by="author",
            change_summary="Initial implementation plan",
        )
        self.assertEqual(draft["workflow_status"], "DRAFT")
        self.assertEqual(draft["version"], 1)
        self.assertTrue(draft["actions"])
        self.assertTrue(draft["evidence"])
        self.assertTrue(all(item["source_rules"] for item in draft["actions"]))
        self.assertTrue(all(item["source_rules"] for item in draft["evidence"]))
        self.assertEqual(len(draft["source_payload_hash"]), 64)

        with self.assertRaises(ValidationError):
            self.service.materialize_blueprint_tasks(
                draft["id"], profile_id="P1", created_by="approver"
            )
        with self.assertRaises(ValidationError):
            self.service.submit_blueprint(
                draft["id"], profile_id="P1", submitted_by="reviewer",
                actor_role="REVIEWER",
            )

        submitted = self.service.submit_blueprint(
            draft["id"], profile_id="P1", submitted_by="author"
        )
        self.assertEqual(submitted["workflow_status"], "UNDER_REVIEW")
        conn = connect(self.path)
        try:
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute(
                    "UPDATE approved_blueprint_actions SET title='tampered' WHERE id=?",
                    (submitted["actions"][0]["id"],),
                )
        finally:
            conn.close()

        returned = self.service.return_blueprint_to_draft(
            draft["id"], profile_id="P1", reviewed_by="reviewer",
            review_note="Clarify operational ownership",
        )
        self.assertEqual(returned["workflow_status"], "DRAFT")
        self.service.submit_blueprint(
            draft["id"], profile_id="P1", submitted_by="author"
        )
        approved = self.service.approve_blueprint(
            draft["id"], profile_id="P1", approved_by="approver"
        )
        self.assertEqual(approved["workflow_status"], "APPROVED")

        first = self.service.materialize_blueprint_tasks(
            draft["id"], profile_id="P1", created_by="approver",
            priority="PRI-HIGH", assigned_to="security-team",
        )
        second = self.service.materialize_blueprint_tasks(
            draft["id"], profile_id="P1", created_by="approver"
        )
        taskable = sum(item["taskable"] for item in approved["actions"])
        self.assertEqual(first["created"], taskable)
        self.assertEqual(first["existing"], 0)
        self.assertEqual(second["created"], 0)
        self.assertEqual(second["existing"], taskable)
        self.assertEqual(set(first["task_ids"]), set(second["task_ids"]))

        task_id = first["task_ids"][0]
        started = self.service.update_task(
            task_id, profile_id="P1", changed_by="operator", status="IN_PROGRESS"
        )
        self.assertEqual(started["status"], "IN_PROGRESS")
        done = self.service.update_task(
            task_id, profile_id="P1", changed_by="operator", status="DONE",
            note="Implementation verified",
        )
        self.assertEqual(done["status"], "DONE")
        with self.assertRaises(ValidationError):
            self.service.update_task(
                task_id, profile_id="P1", changed_by="operator", status="IN_PROGRESS"
            )

        report = self.service.report(profile_id="P1")
        self.assertEqual(report["summary"]["approved_blueprint_count"], 1)
        self.assertEqual(report["summary"]["task_count"], taskable)
        self.assertEqual(report["approved_blueprints"][0]["id"], draft["id"])

    def test_profile_isolation_and_version_supersession(self) -> None:
        approved_v1 = self._approve_identity()
        self.service.materialize_blueprint_tasks(
            approved_v1["id"], profile_id="P1", created_by="approver"
        )
        with self.assertRaises(NotFoundError):
            self.service.blueprint_detail(approved_v1["id"], profile_id="P2")
        with self.assertRaises(NotFoundError):
            self.service.materialize_blueprint_tasks(
                approved_v1["id"], profile_id="P2", created_by="approver"
            )
        self.assertEqual(self.service.list_tasks(profile_id="P2"), [])

        draft_v2 = self.service.create_blueprint_draft(
            "A-IDENTITY", profile_id="P1", created_by="author",
            change_summary="Second governed version",
        )
        self.assertEqual(draft_v2["version"], 2)
        self.assertEqual(draft_v2["parent_blueprint_id"], approved_v1["id"])
        self.service.submit_blueprint(
            draft_v2["id"], profile_id="P1", submitted_by="author"
        )
        approved_v2 = self.service.approve_blueprint(
            draft_v2["id"], profile_id="P1", approved_by="approver"
        )
        self.assertEqual(approved_v2["workflow_status"], "APPROVED")
        old = self.service.blueprint_detail(approved_v1["id"], profile_id="P1")
        self.assertEqual(old["workflow_status"], "SUPERSEDED")
        statuses = [item["workflow_status"] for item in self.service.list_blueprints(profile_id="P1")]
        self.assertEqual(statuses.count("APPROVED"), 1)
        self.assertEqual(statuses.count("SUPERSEDED"), 1)

    def test_transaction_rollback_and_review_resolution_gate(self) -> None:
        self.service.select_artifacts(
            ["A-LOGGING"], profile_id="P1", selected_by="selector"
        )
        broken = SecureGuideService(
            Database(self.path), blueprint_engine=InvalidEvidenceEngine()
        )
        with self.assertRaises(ValidationError):
            broken.create_blueprint_draft(
                "A-LOGGING", profile_id="P1", created_by="author"
            )
        conn = connect(self.path)
        try:
            count = conn.execute(
                "SELECT COUNT(*) FROM approved_blueprints WHERE artifact_id='A-LOGGING'"
            ).fetchone()[0]
            self.assertEqual(count, 0)
            conn.execute(
                """UPDATE security_artifacts
                      SET classification_confidence=.65,
                          classification_rationale='Ambiguous classification',
                          ai_review_status='AIR-HUMAN-REVIEW',requires_human_review=1
                    WHERE id='A-LOGGING'"""
            )
        finally:
            conn.close()

        draft = self.service.create_blueprint_draft(
            "A-LOGGING", profile_id="P1", created_by="author"
        )
        self.assertEqual(draft["generation_requires_review"], 1)
        self.assertTrue(draft["review_findings"])
        self.assertIn(
            "classification confidence",
            " ".join(item["detail"] for item in draft["review_findings"]),
        )
        self.service.submit_blueprint(
            draft["id"], profile_id="P1", submitted_by="author"
        )
        with self.assertRaises(ValidationError):
            self.service.approve_blueprint(
                draft["id"], profile_id="P1", approved_by="approver"
            )
        approved = self.service.approve_blueprint(
            draft["id"], profile_id="P1", approved_by="approver",
            review_resolution_note="Classification and generated actions reviewed and accepted.",
        )
        self.assertEqual(approved["workflow_status"], "APPROVED")


if __name__ == "__main__":
    unittest.main()
