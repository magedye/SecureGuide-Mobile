"""Schema contract tests for catalog closure, provenance, and source rights."""

from __future__ import annotations

import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from secureguide.database import apply_migrations


ROOT = Path(__file__).resolve().parent.parent


class CatalogClosureSchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "closure.db"
        apply_migrations(self.path)
        self.conn = sqlite3.connect(self.path)
        self.conn.execute("PRAGMA foreign_keys=ON")

    def tearDown(self) -> None:
        self.conn.close()
        self.temp.cleanup()

    def test_closure_tables_and_raw_manifest_link_exist(self) -> None:
        tables = {
            row[0]
            for row in self.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        self.assertTrue(
            {
                "source_import_manifests",
                "source_rights_versions",
                "raw_artifact_dispositions",
                "artifact_source_lineage",
                "raw_artifact_reconciliation_links",
                "raw_artifact_deferred_reasons",
            }.issubset(tables)
        )
        columns = {
            row[1] for row in self.conn.execute("PRAGMA table_info(raw_artifacts)")
        }
        self.assertIn("source_manifest_id", columns)

    def _seed_reference_rows(self) -> None:
        self.conn.execute(
            "INSERT INTO source_catalogs(id,name,source_type,version) VALUES(?,?,?,?)",
            ("SRC-1", "Source one", "STANDARD", "1"),
        )
        self.conn.execute(
            """INSERT INTO source_import_manifests(
                   id,source_catalog_id,source_version,source_file,source_sha256,
                   manifest_sha256,importer_name,importer_version,raw_record_count
               ) VALUES(?,?,?,?,?,?,?,?,?)""",
            ("MAN-1", "SRC-1", "1", "source.json", "a" * 64, "b" * 64, "test", "1", 1),
        )
        self.conn.execute(
            """INSERT INTO raw_artifacts(
                   id,source_catalog_id,source_document,source_version,raw_json,
                   source_file,content_hash,source_manifest_id
               ) VALUES(?,?,?,?,?,?,?,?)""",
            ("RAW-1", "SRC-1", "Source one", "1", "{}", "source.json", "c" * 64, "MAN-1"),
        )
        self.conn.execute(
            """INSERT INTO security_artifacts(
                   id,type,title_en,definition_short_en,primary_domain,sub_domain,
                   abstraction_level,source,source_type,obligation_level,requirement_type,
                   granularity_level,classification_confidence,
                   classification_rationale,publication_status,source_document
               ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                "SG-REQ-1", "ART-REQ", "Requirement", "Maintain one inventory.",
                "SD-02", "SD-02.01", "ABS-CTR", "SRC-STD", "STANDARD",
                "OBL-MND", "RQT-STD", "GRN-MEDIUM", 0.8, "It states a required outcome.",
                "APPROVED", "Source one",
            ),
        )

    def test_rights_are_fail_closed_and_disposition_is_exactly_one(self) -> None:
        self._seed_reference_rows()
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                """INSERT INTO source_rights_versions(
                       id,source_catalog_id,source_version,rights_version,
                       redistribution_status,ship_raw_text,decision_reason,decided_by
                   ) VALUES(?,?,?,?,?,?,?,?)""",
                ("RIGHT-1", "SRC-1", "1", "1", "UNKNOWN", 1, "No evidence", "test"),
            )
        self.conn.execute(
            """INSERT INTO raw_artifact_dispositions(
                   raw_artifact_id,disposition,rationale,decision_method,
                   requires_human_review,decided_by
               ) VALUES(?,?,?,?,?,?)""",
            ("RAW-1", "SUPPORTS_CANONICAL", "Primary source", "TEST", 0, "test"),
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                """INSERT INTO raw_artifact_dispositions(
                       raw_artifact_id,disposition,rationale,decision_method,
                       requires_human_review,decided_by
                   ) VALUES(?,?,?,?,?,?)""",
                ("RAW-1", "DEFERRED", "Duplicate decision", "TEST", 1, "test"),
            )

    def test_lineage_supports_many_to_many_and_delete_guards(self) -> None:
        self._seed_reference_rows()
        self.conn.execute(
            """INSERT INTO artifact_source_lineage(
                   artifact_id,raw_artifact_id,lineage_role,mapping_strength,is_primary
               ) VALUES(?,?,?,?,?)""",
            ("SG-REQ-1", "RAW-1", "SUPPORTS_CANONICAL", "DIRECT", 1),
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("DELETE FROM raw_artifacts WHERE id='RAW-1'")
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "DELETE FROM artifact_source_lineage WHERE artifact_id='SG-REQ-1'"
            )

    def test_reconciliation_links_and_deferred_reasons_are_normalized(self) -> None:
        self._seed_reference_rows()
        self.conn.execute(
            """INSERT INTO raw_artifact_dispositions(
                   raw_artifact_id,disposition,rationale,decision_method,
                   requires_human_review,decided_by
               ) VALUES(?,?,?,?,?,?)""",
            ("RAW-1", "DEFERRED", "Source statement has an unresolved atomicity conflict.",
             "SEMANTIC_RECONCILIATION_V1", 1, "test"),
        )
        self.conn.execute(
            """INSERT INTO raw_artifact_deferred_reasons(
                   raw_artifact_id,reason_code
               ) VALUES(?,?)""",
            ("RAW-1", "ATOMICITY_AMBIGUITY"),
        )
        self.conn.execute(
            """INSERT INTO raw_artifact_reconciliation_links(
                   raw_artifact_id,link_index,disposition,target_artifact_id,
                   target_raw_artifact_id,mapping_strength,rationale,evidence_method
               ) VALUES(?,?,?,?,?,?,?,?)""",
            ("RAW-1", 0, "RELATION_ONLY", "SG-REQ-1", None, "INFORMATIVE",
             "The source provides context but is not equivalent.", "TEST"),
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                """INSERT INTO raw_artifact_reconciliation_links(
                       raw_artifact_id,link_index,disposition,target_artifact_id,
                       target_raw_artifact_id,mapping_strength,rationale,evidence_method
                   ) VALUES(?,?,?,?,?,?,?,?)""",
                ("RAW-1", 1, "RELATION_ONLY", "SG-REQ-1", "RAW-1", "DIRECT",
                 "Both target kinds are invalid.", "TEST"),
            )
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO raw_artifact_deferred_reasons(raw_artifact_id,reason_code) VALUES(?,?)",
                ("RAW-1", "GENERIC_NO_CLASSIFIER_EVIDENCE"),
            )

    def test_migration_preserves_existing_profile_rows(self) -> None:
        legacy = Path(self.temp.name) / "legacy.db"
        shutil.copy2(ROOT / "mobile" / "assets" / "catalog.db", legacy)
        conn = sqlite3.connect(legacy)
        conn.execute("PRAGMA foreign_keys=ON")
        artifact_id = conn.execute("SELECT MIN(id) FROM security_artifacts").fetchone()[0]
        conn.execute(
            "INSERT INTO enterprise_profiles(id,name,profile_kind) VALUES('P1','Profile','SYSTEM')"
        )
        conn.execute(
            """INSERT INTO profile_artifacts(id,profile_id,artifact_id)
               VALUES('PA1','P1',?)""",
            (artifact_id,),
        )
        conn.commit()
        before = conn.execute(
            "SELECT id,profile_id,artifact_id FROM profile_artifacts"
        ).fetchall()
        conn.close()
        apply_migrations(legacy)
        conn = sqlite3.connect(legacy)
        try:
            self.assertEqual(
                before,
                conn.execute(
                    "SELECT id,profile_id,artifact_id FROM profile_artifacts"
                ).fetchall(),
            )
            self.assertEqual(conn.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(conn.execute("PRAGMA foreign_key_check").fetchall(), [])
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
