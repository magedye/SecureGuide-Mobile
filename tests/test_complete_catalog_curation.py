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
)
from secureguide.catalog_validation import canonical_hash
from secureguide.database import apply_migrations


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
        source_hash = __import__("hashlib").sha256(self.source.read_bytes()).hexdigest()
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
            "total_bytes": self.source.stat().st_size,
            "importer": {"name": "test", "version": "1"},
            "sources": [{
                "id": "MAN", "source_catalog_id": "SRC",
                "source_document": "Source", "source_version": "UNKNOWN",
                "version_unknown_reason": "No immutable upstream version evidence.",
                "source_file": "source.json", "source_sha256": source_hash,
                "source_bytes": self.source.stat().st_size,
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


if __name__ == "__main__":
    unittest.main()
