"""Fail-closed tests for the governed mobile release catalog builder."""

from __future__ import annotations

import json
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.build_release_db import BuildError, _release_gates, build


ROOT = Path(__file__).resolve().parent.parent


class GovernedReleaseBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp = tempfile.TemporaryDirectory()
        cls.output = Path(cls.temp.name) / "secureguide-release.db"
        cls.manifest = build(cls.output, mode="release")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp.cleanup()

    def _working_copy(self, name: str) -> Path:
        target = Path(self.temp.name) / name
        shutil.copy2(self.output, target)
        return target

    def test_release_preserves_approved_lineage_and_installs_template(self) -> None:
        expected_schema_version = max(
            int(path.name[:3])
            for path in (ROOT / "migrations").glob("[0-9][0-9][0-9]_*.sql")
        )
        self.assertEqual(self.manifest["mode"], "release")
        self.assertEqual(
            self.manifest["schemaVersion"], f"{expected_schema_version:03d}"
        )
        self.assertEqual(self.manifest["publicationStatus"], {"APPROVED": 4})
        self.assertEqual(self.manifest["releaseCounts"]["artifacts"], 4)
        self.assertGreater(self.manifest["releaseCounts"]["rawArtifacts"], 0)
        self.assertEqual(self.manifest["releaseCounts"]["templates"], 1)
        self.assertEqual(self.manifest["releaseCounts"]["templateItems"], 4)
        self.assertIn("raw_source_lineage", self.manifest["gatesPassed"])

        manifest_path = self.output.with_suffix(".db.manifest.json")
        persisted = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(persisted["sha256"], self.manifest["sha256"])

        conn = sqlite3.connect(self.output)
        try:
            self.assertEqual(
                conn.execute("PRAGMA user_version").fetchone()[0],
                expected_schema_version,
            )
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM enterprise_profiles").fetchone()[0],
                0,
            )
        finally:
            conn.close()

    def test_release_gate_rejects_missing_templates(self) -> None:
        path = self._working_copy("missing-template.db")
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            conn.execute("DELETE FROM templates")
            conn.commit()
            with self.assertRaisesRegex(BuildError, "no usable template"):
                _release_gates(conn)
        finally:
            conn.close()

    def test_release_gate_rejects_demo_markers(self) -> None:
        path = self._working_copy("demo-marker.db")
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute(
                "UPDATE security_artifacts SET title_en='Test fixture' "
                "WHERE id=(SELECT MIN(id) FROM security_artifacts)"
            )
            conn.commit()
            with self.assertRaisesRegex(BuildError, "demo/test fixture"):
                _release_gates(conn)
        finally:
            conn.close()

    def test_release_source_checksum_is_pinned(self) -> None:
        source = Path(self.temp.name) / "catalog.db"
        shutil.copy2(ROOT / "catalog.db", source)
        with source.open("ab") as handle:
            handle.write(b"stale")
        with self.assertRaisesRegex(BuildError, "checksum"):
            build(
                Path(self.temp.name) / "rejected.db",
                mode="release",
                release_source=source,
            )

    def test_release_database_is_bit_reproducible(self) -> None:
        second_output = Path(self.temp.name) / "secureguide-release-second.db"
        second_manifest = build(second_output, mode="release")

        self.assertEqual(second_manifest["sha256"], self.manifest["sha256"])
        self.assertEqual(second_output.read_bytes(), self.output.read_bytes())
        self.assertEqual(
            second_manifest["reproducibleBuildTimestampUtc"],
            "2026-07-01T00:00:00Z",
        )


if __name__ == "__main__":
    unittest.main()
