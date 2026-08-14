"""Catalog provenance backfill and complete-corpus curation tests."""

from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

import yaml

from secureguide.catalog_curation import (
    CurationInputError,
    backfill_source_provenance,
    build_projection,
    curate_complete_catalog,
    load_curation_candidates,
    load_semantic_reconciliation_ledger,
    prepare_curation_database,
    validate_semantic_reconciliation_ledger,
)
from secureguide.catalog_validation import (
    canonical_hash,
    portable_text_bytes,
    portable_text_hash,
    validate_catalog,
)
from secureguide.database import apply_migrations


ROOT = Path(__file__).resolve().parent.parent


class ProvenanceBackfillTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db = self.root / "catalog.db"
        apply_migrations(self.db)
        self.conn = sqlite3.connect(self.db, isolation_level=None)
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.source = self.root / "source.json"
        self.source.write_text('{"artifacts":[{}]}\n', encoding="utf-8")
        self.conn.execute(
            "INSERT INTO source_catalogs(id,name,source_type,version) "
            "VALUES('SRC','Source','STANDARD','Unknown')"
        )
        self.conn.execute(
            """INSERT INTO raw_artifacts(
                   id,source_catalog_id,source_document,source_version,raw_json,
                   source_file,content_hash
               ) VALUES('RAW','SRC','Source','Unknown','{}','source.json',?)""",
            ("c" * 64,),
        )
        source_hash = portable_text_hash(self.source)
        manifest = {
            "schema_version": 1,
            "manifest_id": "test",
            "created_at": "2026-01-01T00:00:00Z",
            "corpus_root": ".",
            "hash_algorithm": "SHA-256",
            "manifest_sha256": None,
            "manifest_hash_scope": "test",
            "source_count": 1,
            "raw_record_count": 1,
            "total_bytes": len(portable_text_bytes(self.source)),
            "importer": {"name": "test", "version": "1"},
            "sources": [{
                "id": "MAN", "source_catalog_id": "SRC",
                "source_document": "Source", "source_version": "UNKNOWN",
                "version_unknown_reason": "No immutable upstream version evidence.",
                "source_file": "source.json", "source_sha256": source_hash,
                "source_bytes": len(portable_text_bytes(self.source)),
                "retrieval_uri": None, "retrieved_at": None,
                "raw_record_count": 1,
            }],
        }
        manifest["manifest_sha256"] = canonical_hash(manifest)
        self.manifest_path = self.root / "manifest.json"
        self.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        rights = {
            "schema_version": 1,
            "rights": [{
                "id": "RIGHT", "source_catalog_id": "SRC",
                "source_version": "UNKNOWN", "rights_version": "1",
                "redistribution_status": "UNKNOWN", "ship_raw_text": False,
                "license_identifier": None, "terms_url": None,
                "evidence_sha256": None, "evidence_retrieved_at": None,
                "attribution_text": None, "decision_reason": "No evidence.",
                "decided_by": "test", "decided_at": "2026-01-01T00:00:00Z",
                "supersedes_id": None, "is_current": True,
            }],
        }
        self.rights_path = self.root / "rights.yaml"
        self.rights_path.write_text(yaml.safe_dump(rights), encoding="utf-8")

    def tearDown(self) -> None:
        self.conn.close()
        self.temp.cleanup()

    def test_backfill_normalizes_unknown_and_is_idempotent(self) -> None:
        first = backfill_source_provenance(
            self.conn, self.manifest_path, self.rights_path, root=self.root
        )
        second = backfill_source_provenance(
            self.conn, self.manifest_path, self.rights_path, root=self.root
        )
        row = self.conn.execute(
            "SELECT source_version,source_manifest_id FROM raw_artifacts WHERE id='RAW'"
        ).fetchone()
        right = self.conn.execute(
            "SELECT redistribution_status,ship_raw_text FROM source_rights_versions"
        ).fetchone()
        self.assertEqual(tuple(row), ("UNKNOWN", "MAN"))
        self.assertEqual(tuple(right), ("UNKNOWN", 0))
        self.assertEqual(first["missingManifestRows"], 0)
        self.assertEqual(second["missingRightsRows"], 0)
        self.assertEqual(self.conn.execute(
            "SELECT COUNT(*) FROM source_import_manifests"
        ).fetchone()[0], 1)

    def test_stale_source_hash_is_rejected_before_mutation(self) -> None:
        self.source.write_text("changed", encoding="utf-8")
        with self.assertRaises(CurationInputError):
            backfill_source_provenance(
                self.conn, self.manifest_path, self.rights_path, root=self.root
            )
        self.assertIsNone(self.conn.execute(
            "SELECT source_manifest_id FROM raw_artifacts WHERE id='RAW'"
        ).fetchone()[0])

    def test_unknown_rights_cannot_ship_raw_text(self) -> None:
        rights = yaml.safe_load(self.rights_path.read_text(encoding="utf-8"))
        rights["rights"][0]["ship_raw_text"] = True
        self.rights_path.write_text(yaml.safe_dump(rights), encoding="utf-8")
        with self.assertRaises(CurationInputError):
            backfill_source_provenance(
                self.conn, self.manifest_path, self.rights_path, root=self.root
            )


class CompleteProjectionTests(unittest.TestCase):
    def test_semantic_ledger_is_hash_bound_and_requires_exact_raw_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            database = Path(folder) / "ledger.db"
            apply_migrations(database)
            conn = sqlite3.connect(database)
            try:
                conn.execute(
                    "INSERT INTO source_catalogs(id,name,source_type,version) VALUES('SRC','Source','STANDARD','1')"
                )
                conn.execute(
                    """INSERT INTO raw_artifacts(
                           id,source_catalog_id,source_document,source_version,raw_json,
                           source_file,content_hash
                       ) VALUES('RAW','SRC','Source','1','{}','source.json',?)""",
                    ("a" * 64,),
                )
                entry = {
                    "raw_id": "RAW", "source_content_sha256": "a" * 64,
                    "disposition": "DEFERRED", "decision_method": "TEST_V1",
                    "rationale": "The source lacks authoritative scope required to select a canonical.",
                    "deferred_reason_code": "MISSING_SOURCE_METADATA",
                }
                document = {"schema_version": 1, "ledger_sha256": None, "decisions": [entry]}
                document["ledger_sha256"] = canonical_hash(document)
                path = Path(folder) / "ledger.json"
                path.write_text(json.dumps(document), encoding="utf-8")
                ledger = load_semantic_reconciliation_ledger(path)
                self.assertTrue(validate_semantic_reconciliation_ledger(conn, ledger)["valid"])
                conn.execute("UPDATE raw_artifacts SET content_hash=? WHERE id='RAW'", ("b" * 64,))
                self.assertEqual(
                    validate_semantic_reconciliation_ledger(conn, ledger)["staleRawIds"], ["RAW"]
                )
            finally:
                conn.close()

    def test_projection_is_deterministic_and_globally_accounts_for_candidates(self) -> None:
        candidates = load_curation_candidates()
        first = build_projection(candidates)
        second = build_projection(candidates)
        self.assertEqual(len(candidates), 1467)
        self.assertEqual(len(first["groups"]), 215)
        self.assertEqual(len(first["selected"]), 1214)
        self.assertEqual(len(first["rawToCandidate"]), 1467)
        self.assertEqual(canonical_hash(first), canonical_hash(second))
        self.assertEqual(first["selectionOverrides"][0]["selectedCanonical"], "STG-CURATED-0641")

    def test_legacy_projection_is_rejected_until_full_corpus_reconciliation_exists(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            database = Path(folder) / "curated.db"
            prepare_curation_database(ROOT / "catalog.db", database)
            conn = sqlite3.connect(database, isolation_level=None)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            try:
                provenance = backfill_source_provenance(conn)
                result = curate_complete_catalog(conn)
            finally:
                conn.close()
            validation = validate_catalog(database)
            self.assertEqual(provenance["missingManifestRows"], 0)
            self.assertEqual(result["rawTotal"], 4265)
            self.assertEqual(sum(result["dispositions"].values()), 4265)
            self.assertEqual(set(result["domains"]), {f"SD-{number:02d}" for number in range(1, 9)})
            self.assertEqual(validation["summary"]["minimumValid"], result["canonicalTotal"])
            self.assertFalse(validation["closure"]["valid"])
            self.assertEqual(validation["closure"]["genericDeferredRationales"], 2792)
            self.assertEqual(validation["closure"]["deferredWithoutReasonCode"], 2792)
            self.assertTrue(validation["integrity"]["valid"])
            self.assertEqual(result["normalized"]["artifactIdAliases"], 959)
            verified = sqlite3.connect(database)
            try:
                alias_target = verified.execute(
                    """SELECT artifact_id FROM catalog_artifact_id_aliases
                        WHERE old_artifact_id='SG-CTR-CURATED-0138'"""
                ).fetchone()[0]
            finally:
                verified.close()
            self.assertEqual(alias_target, "SG-CFG-CAT-0203")
            self.assertGreaterEqual(validation["summary"]["canonicalTotal"], 1000)


if __name__ == "__main__":
    unittest.main()
