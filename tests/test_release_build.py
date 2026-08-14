"""Fail-closed tests for the governed mobile release catalog builder."""

from __future__ import annotations

import json
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.build_release_db import (
    BuildError,
    _canonical_manifest_hash,
    _publish_pair,
    _release_gates,
    build,
)


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


class CuratedReleaseBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp = tempfile.TemporaryDirectory()
        cls.first = Path(cls.temp.name) / "curated-a.db"
        cls.second = Path(cls.temp.name) / "curated-b.db"
        cls.first_manifest = build(cls.first, mode="curated")
        cls.second_manifest = build(cls.second, mode="curated")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp.cleanup()

    def test_curated_database_and_manifest_are_reproducible(self) -> None:
        self.assertEqual(self.first.read_bytes(), self.second.read_bytes())
        self.assertEqual(self.first_manifest, self.second_manifest)
        self.assertEqual(
            self.first.with_suffix(".db.manifest.json").read_bytes(),
            self.second.with_suffix(".db.manifest.json").read_bytes(),
        )
        self.assertEqual(
            self.first_manifest["manifestSha256"],
            _canonical_manifest_hash(self.first_manifest),
        )

    def test_legacy_curated_candidates_are_rejected_until_semantic_closure_exists(self) -> None:
        from scripts.validate_catalog_release import validate_release

        report = validate_release(
            self.first,
            comparison_database=self.second,
        )
        self.assertFalse(report["valid"], report)
        self.assertFalse(report["V1"]["valid"], report)
        self.assertEqual(report["V1"]["closure"]["genericDeferredRationales"], 2792)
        self.assertEqual(report["V1"]["closure"]["deferredWithoutReasonCode"], 2792)
        self.assertTrue(all(report[level]["valid"] for level in ("V2", "V3", "V4")))
        self.assertEqual(report["V4"]["bindingErrors"], {})

    def test_curated_release_has_closed_minimum_catalog_and_no_unlicensed_payload(self) -> None:
        manifest = self.first_manifest
        self.assertEqual(manifest["releaseCounts"]["artifacts"], 1218)
        self.assertEqual(manifest["releaseCounts"]["rawArtifacts"], 4265)
        self.assertEqual(manifest["releaseCounts"]["quality"]["minimumValid"], 1218)
        self.assertEqual(manifest["releaseCounts"]["closure"]["rawDisposed"], 4265)
        self.assertEqual(manifest["rights"]["rawPayloadsIncluded"], 0)
        self.assertEqual(manifest["rights"]["rawPayloadsExcluded"], 4265)
        conn = sqlite3.connect(self.first)
        try:
            self.assertEqual(conn.execute(
                """SELECT COUNT(*) FROM raw_artifacts
                     WHERE raw_text_en IS NOT NULL OR raw_text_ar IS NOT NULL
                        OR raw_json<>'{}' OR title_draft IS NOT NULL
                        OR description_draft IS NOT NULL"""
            ).fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM staging_artifacts").fetchone()[0], 0)
            self.assertEqual(conn.execute(
                """SELECT COUNT(*) FROM security_artifacts
                     WHERE trim(title_en) GLOB '[0-9.]*'
                       AND trim(title_en) NOT GLOB '*[A-Za-z]*'"""
            ).fetchone()[0], 0)
            self.assertEqual(conn.execute(
                """SELECT COUNT(*) FROM security_artifacts
                     WHERE definition_short_en LIKE '%](http%'
                        OR definition_short_en LIKE '%<code>%'
                        OR definition_short_en LIKE '%(Citation:%'
                        OR definition_full_en LIKE '%](http%'
                        OR definition_full_en LIKE '%<code>%'
                        OR definition_full_en LIKE '%(Citation:%'"""
            ).fetchone()[0], 0)
            self.assertEqual(conn.execute(
                """SELECT COUNT(*) FROM security_artifacts
                     WHERE title_en GLOB 'T[0-9][0-9][0-9][0-9]*'
                       AND type<>'ART-THR'"""
            ).fetchone()[0], 0)
            self.assertEqual(conn.execute(
                """SELECT COUNT(*) FROM (
                       SELECT lower(trim(title_en)) FROM security_artifacts
                       GROUP BY lower(trim(title_en)) HAVING COUNT(*)>1)"""
            ).fetchone()[0], 0)
            self.assertGreater(conn.execute(
                "SELECT COUNT(*) FROM external_references"
            ).fetchone()[0], 0)
            self.assertEqual(conn.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(conn.execute("PRAGMA foreign_key_check").fetchall(), [])
        finally:
            conn.close()

    def test_pair_promotion_rolls_back_both_files_on_second_replace_failure(self) -> None:
        root = Path(self.temp.name)
        output = root / "pair.db"
        manifest = root / "pair.db.manifest.json"
        db_temp = root / ".pair.db.building"
        manifest_temp = root / ".pair.db.manifest.json.building"
        output.write_bytes(b"old-db")
        manifest.write_bytes(b"old-manifest")
        db_temp.write_bytes(b"new-db")
        manifest_temp.write_bytes(b"new-manifest")
        real_replace = __import__("os").replace
        failed = False

        def replace_once(source, target):
            nonlocal failed
            if Path(source) == manifest_temp and not failed:
                failed = True
                raise OSError("simulated manifest publish failure")
            return real_replace(source, target)

        with patch("scripts.build_release_db.os.replace", side_effect=replace_once):
            with self.assertRaisesRegex(OSError, "simulated"):
                _publish_pair(db_temp, manifest_temp, output, manifest)
        self.assertEqual(output.read_bytes(), b"old-db")
        self.assertEqual(manifest.read_bytes(), b"old-manifest")


if __name__ == "__main__":
    unittest.main()
