from __future__ import annotations

import unittest
import tempfile
from pathlib import Path

from scripts.validate_catalog_identity import audit_database, scan


class CatalogIdentityTests(unittest.TestCase):
    def test_retired_identity_is_confined_to_compatibility_evidence(self) -> None:
        self.assertEqual(scan(), [])

    def test_database_audit_distinguishes_active_history_and_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            database = Path(folder) / "identity.db"
            import sqlite3

            conn = sqlite3.connect(database)
            token = "".join(chr(code) for code in (97, 109, 97, 110, 105))
            conn.executescript(
                "CREATE TABLE framework_mappings(rationale TEXT);"
                "CREATE TABLE raw_artifacts(source_document TEXT);"
                "CREATE TABLE schema_migrations(description TEXT);"
                "CREATE TABLE catalog_artifact_id_aliases(old_artifact_id TEXT);"
            )
            conn.execute("INSERT INTO framework_mappings VALUES(?)", (token,))
            conn.execute("INSERT INTO raw_artifacts VALUES(?)", (token,))
            conn.execute("INSERT INTO schema_migrations VALUES(?)", (token,))
            conn.execute("INSERT INTO catalog_artifact_id_aliases VALUES(?)", (token,))
            conn.commit()
            conn.close()
            audit = audit_database(database)
            self.assertEqual(audit["ACTIVE_CURRENT"], ["framework_mappings.rationale:1"])
            self.assertEqual(audit["IMMUTABLE_HISTORY"], ["raw_artifacts.source_document:1", "schema_migrations.description:1"])
            self.assertEqual(audit["COMPATIBILITY_ALIAS"], ["catalog_artifact_id_aliases.old_artifact_id:1"])


if __name__ == "__main__":
    unittest.main()
