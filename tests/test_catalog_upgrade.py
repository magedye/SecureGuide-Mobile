"""Populated-install catalog upgrade and rollback qualification tests."""

from __future__ import annotations

import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from secureguide import Database, SecureGuideService, apply_migrations
from secureguide.catalog_upgrade import (
    CatalogUpgradeError,
    operational_snapshot,
    upgrade_catalog,
)
from secureguide.database import connect
from scripts.build_release_db import build


ROOT = Path(__file__).resolve().parent.parent


class CatalogUpgradeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.class_temp = tempfile.TemporaryDirectory()
        cls.candidate = Path(cls.class_temp.name) / "candidate.db"
        build(cls.candidate, mode="curated")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.class_temp.cleanup()

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.installed = Path(self.temp.name) / "installed.db"
        # The tracked root catalog is the explicit four-artifact predecessor
        # fixture. The mobile asset is the current release candidate and must
        # not be used as both sides of an upgrade qualification.
        shutil.copy2(ROOT / "catalog.db", self.installed)
        apply_migrations(self.installed)
        self.service = SecureGuideService(Database(self.installed))
        self._seed_profiles()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _seed_profiles(self) -> None:
        self.service.create_profile(
            profile_id="P1", name="Head Office", profile_kind="organization", activate=True
        )
        self.service.create_profile(
            profile_id="P2", name="Cloud Audit", profile_kind="audit"
        )
        self.service.select_artifacts(
            ["SG-CTR-AI-02", "SG-CTR-AI-05"], selected_by="tester"
        )
        assessment = self.service.assess_artifact(
            "SG-CTR-AI-02", assessor_name="auditor",
            implementation_status="STS-FULL", verification_status="VER-PASS",
            effectiveness="EFF-HIGH", score=100, comments="Verified",
        )
        self.service.add_evidence(
            "SG-CTR-AI-02", evidence_type="REPORT", assessment_id=assessment["id"],
            description="Quarterly verification", collected_by="auditor",
            content_hash="A" * 64,
        )
        exception = self.service.create_exception(
            "SG-CTR-AI-05", exception_status="EXC-DEFERRED",
            justification="Scheduled remediation window.",
        )
        self.service.submit_exception(exception["id"])
        self.service.approve_exception(
            exception["id"], approved_by="CISO",
            approval_date="2026-08-13", expiry_date="2027-02-13",
        )
        self.service.activate_profile("P2")
        self.service.select_artifacts(["SG-REQ-AI-06"], selected_by="tester")

    def _snapshot(self) -> str:
        conn = connect(self.installed)
        try:
            return operational_snapshot(conn)["sha256"]
        finally:
            conn.close()

    def test_upgrade_preserves_profiles_assessments_evidence_and_exceptions(self) -> None:
        before = self._snapshot()
        result = upgrade_catalog(self.installed, self.candidate, actor="qualification")
        after = self._snapshot()
        self.assertEqual(before, after)
        self.assertEqual(result["operationalSnapshotBefore"], before)
        self.assertEqual(result["operationalSnapshotAfter"], after)
        self.assertEqual(result["oldArtifactCount"], 4)
        self.assertEqual(result["newArtifactCount"], 1227)
        conn = sqlite3.connect(self.installed)
        try:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM enterprise_profiles").fetchone()[0], 2)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM profile_artifacts").fetchone()[0], 3)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM profile_assessments").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM profile_evidence").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM profile_exceptions").fetchone()[0], 1)
            self.assertEqual(
                conn.execute(
                    "SELECT active_profile_id FROM application_state WHERE singleton_id=1"
                ).fetchone()[0],
                "P2",
            )
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM raw_artifacts").fetchone()[0], 4265)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM staging_artifacts").fetchone()[0], 0)
            self.assertEqual(conn.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(conn.execute("PRAGMA foreign_key_check").fetchall(), [])
        finally:
            conn.close()

    def test_stable_id_failure_rolls_back_catalog_and_preserves_operational_snapshot(self) -> None:
        invalid = Path(self.temp.name) / "invalid-candidate.db"
        shutil.copy2(self.candidate, invalid)
        conn = sqlite3.connect(invalid)
        conn.execute(
            "UPDATE security_artifacts SET type='ART-STD' WHERE id='SG-CTR-AI-02'"
        )
        conn.commit()
        conn.close()
        before = self._snapshot()
        conn = sqlite3.connect(self.installed)
        artifact_count = conn.execute("SELECT COUNT(*) FROM security_artifacts").fetchone()[0]
        conn.close()
        with self.assertRaisesRegex(CatalogUpgradeError, "stable-ID"):
            upgrade_catalog(self.installed, invalid)
        self.assertEqual(before, self._snapshot())
        conn = sqlite3.connect(self.installed)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM security_artifacts").fetchone()[0], artifact_count)
        conn.close()

    def test_reapplying_same_candidate_is_idempotent_for_catalog_counts(self) -> None:
        first = upgrade_catalog(self.installed, self.candidate)
        second = upgrade_catalog(self.installed, self.candidate)
        self.assertEqual(first["newArtifactCount"], second["newArtifactCount"])
        conn = sqlite3.connect(self.installed)
        candidate = sqlite3.connect(self.candidate)
        self.assertEqual(
            conn.execute("SELECT COUNT(*) FROM framework_mappings").fetchone()[0],
            candidate.execute("SELECT COUNT(*) FROM framework_mappings").fetchone()[0],
        )
        candidate.close()
        conn.close()


if __name__ == "__main__":
    unittest.main()
