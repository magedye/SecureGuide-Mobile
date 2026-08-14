"""Minimum-catalog, strict-USACM, and closure validation tests."""

from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from secureguide.catalog_validation import (
    canonical_hash,
    load_contract,
    validate_catalog,
)
from secureguide.database import apply_migrations
from scripts.batch_process import classify
from scripts.catalog_validate import main as validation_main


ROOT = Path(__file__).resolve().parent.parent


class CatalogValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "validation.db"
        apply_migrations(self.path)
        self.conn = sqlite3.connect(self.path)
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._seed_source()

    def tearDown(self) -> None:
        self.conn.close()
        self.temp.cleanup()

    def _seed_source(self) -> None:
        self.conn.execute(
            "INSERT INTO source_catalogs(id,name,source_type,version) VALUES('SRC','Source','STANDARD','1')"
        )
        self.conn.execute(
            """INSERT INTO source_import_manifests(
                   id,source_catalog_id,source_version,source_file,source_sha256,
                   manifest_sha256,importer_name,importer_version,raw_record_count
               ) VALUES('MAN','SRC','1','source.json',?,?, 'test','1',1)""",
            ("a" * 64, "b" * 64),
        )
        self.conn.execute(
            """INSERT INTO source_rights_versions(
                   id,source_catalog_id,source_version,rights_version,
                   redistribution_status,ship_raw_text,decision_reason,decided_by
               ) VALUES('RIGHT','SRC','1','1','UNKNOWN',0,'No permission evidence','test')"""
        )
        self.conn.execute(
            """INSERT INTO raw_artifacts(
                   id,source_catalog_id,source_document,source_type,source_version,
                   source_section,raw_text_en,raw_json,source_file,content_hash,
                   source_manifest_id
               ) VALUES('RAW','SRC','Source','STANDARD','1','1','raw','{}','source.json',?,'MAN')""",
            ("c" * 64,),
        )

    def _insert_artifact(
        self, artifact_id: str = "SG-CTR-1", *, with_closure: bool = True,
        **overrides: object
    ) -> None:
        values = {
            "id": artifact_id,
            "source_catalog_id": "SRC",
            "type": "ART-CTR",
            "title_en": "Maintain inventory",
            "definition_short_en": "Maintain an accurate inventory of enterprise assets.",
            "primary_domain": "SD-02",
            "sub_domain": "SD-02.01",
            "abstraction_level": "ABS-CTR",
            "source": "SRC-STD",
            "source_type": "STANDARD",
            "obligation_level": "OBL-MND",
            "granularity_level": "GRN-MEDIUM",
            "control_nature": "NAT-ORG",
            "control_function": "FUN-PRE",
            "testability": "TST-MAN",
            "priority": "PRI-MEDIUM",
            "priority_weight": 4,
            "review_frequency": "AD-HOC",
            "classification_confidence": 0.65,
            "classification_rationale": "This is a safeguard that reduces inventory risk.",
            "ai_review_status": "AIR-HUMAN-REVIEW",
            "requires_human_review": 1,
            "publication_status": "APPROVED",
            "source_document": "Source",
            "is_active": 1,
        }
        values.update(overrides)
        columns = ",".join(values)
        placeholders = ",".join("?" for _ in values)
        self.conn.execute(
            f"INSERT INTO security_artifacts({columns}) VALUES({placeholders})",
            tuple(values.values()),
        )
        if with_closure:
            self.conn.execute(
                """INSERT INTO artifact_source_lineage(
                       artifact_id,raw_artifact_id,lineage_role,mapping_strength,is_primary
                   ) VALUES(?, 'RAW', 'SUPPORTS_CANONICAL', 'DIRECT', 1)""",
                (artifact_id,),
            )
            self.conn.execute(
                """INSERT INTO raw_artifact_dispositions(
                       raw_artifact_id,disposition,rationale,decision_method,
                       decision_confidence,requires_human_review,decided_by
                   ) VALUES('RAW','SUPPORTS_CANONICAL','Primary source','TEST',0.65,1,'test')"""
            )
        self.conn.commit()

    def test_contract_is_json_compatible_yaml_and_hash_is_stable(self) -> None:
        contract = load_contract(ROOT / "config" / "catalog_minimum_fields.yaml")
        self.assertEqual(contract["result_names"]["minimum"], "MINIMUM_CATALOG_VALIDATION")
        left = canonical_hash({"b": "e\u0301", "a": None})
        right = canonical_hash({"a": None, "b": "é"})
        self.assertEqual(left, right)

    def test_low_confidence_and_not_reviewed_are_minimum_valid(self) -> None:
        self._insert_artifact()
        localization = self.conn.execute(
            "SELECT content_review_status FROM artifact_localizations "
            "WHERE artifact_id='SG-CTR-1' AND is_primary=1"
        ).fetchone()
        self.assertEqual(localization[0], "NOT_REVIEWED")
        report = validate_catalog(self.path)
        artifact = report["artifacts"][0]
        self.assertTrue(artifact["MINIMUM_CATALOG_VALIDATION"]["valid"])
        self.assertTrue(artifact["STRICT_USACM_CONFORMANCE"]["valid"])
        self.assertEqual(report["reviewSummary"]["requiresHumanReview"], 1)

    def test_minimum_reports_missing_type_fields_and_lineage(self) -> None:
        self._insert_artifact(
            "SG-POL-1", with_closure=False, type="ART-POL", control_nature=None,
            control_function=None, testability=None
        )
        report = validate_catalog(self.path)
        result = report["artifacts"][0]["MINIMUM_CATALOG_VALIDATION"]
        self.assertFalse(result["valid"])
        self.assertIn("artifact_source_lineage", result["missing"])

    def test_risk_requires_remediation_action_or_incoming_mitigation(self) -> None:
        self._insert_artifact("SG-RSK-1", type="ART-RSK", control_nature=None,
                              control_function=None, testability=None)
        first = validate_catalog(self.path)["artifacts"][0]["MINIMUM_CATALOG_VALIDATION"]
        self.assertIn("risk_remediation", first["missing"])
        self.conn.execute(
            """INSERT INTO remediation_actions(
                   artifact_id,action,priority,responsible_role
               ) VALUES('SG-RSK-1','Treat the risk','PRI-HIGH','Risk owner')"""
        )
        self.conn.commit()
        second = validate_catalog(self.path)["artifacts"][0]["MINIMUM_CATALOG_VALIDATION"]
        self.assertTrue(second["valid"])

    def test_strict_result_can_fail_without_changing_minimum_result(self) -> None:
        self._insert_artifact()
        # Lookup rows are not foreign-key parents of the catalog row. Removing
        # one simulates controlled-vocabulary drift that strict validation must
        # catch while the deliberately narrower minimum contract remains valid.
        self.conn.execute("DELETE FROM lk_priority WHERE code='PRI-MEDIUM'")
        self.conn.commit()
        report = validate_catalog(self.path)
        artifact = report["artifacts"][0]
        self.assertTrue(artifact["MINIMUM_CATALOG_VALIDATION"]["valid"])
        self.assertFalse(artifact["STRICT_USACM_CONFORMANCE"]["valid"])

    def test_zero_confidence_requires_explicit_unknown_semantics(self) -> None:
        self._insert_artifact(
            classification_confidence=0.0,
            classification_rationale="Unscored legacy evidence.",
        )
        first = validate_catalog(self.path)["artifacts"][0][
            "MINIMUM_CATALOG_VALIDATION"
        ]
        self.assertFalse(first["valid"])
        self.assertIn("classification_confidence_semantics", first["missing"])
        self.conn.execute(
            "UPDATE security_artifacts SET classification_rationale=? WHERE id='SG-CTR-1'",
            (
                "CONFIDENCE_UNASSESSED: no numeric score was available; "
                "0.0 is the explicit unknown sentinel.",
            ),
        )
        self.conn.commit()
        second = validate_catalog(self.path)["artifacts"][0][
            "MINIMUM_CATALOG_VALIDATION"
        ]
        self.assertTrue(second["valid"])

    def test_closure_reports_missing_dispositions_and_dangling_are_zero(self) -> None:
        self._insert_artifact()
        self.conn.execute(
            """INSERT INTO raw_artifacts(
                   id,source_catalog_id,source_document,source_version,raw_json,
                   source_file,content_hash,source_manifest_id
               ) VALUES('RAW-2','SRC','Source','1','{}','source.json',?,'MAN')""",
            ("d" * 64,),
        )
        self.conn.commit()
        report = validate_catalog(self.path)
        self.assertEqual(report["closure"]["rawTotal"], 2)
        self.assertEqual(report["closure"]["missingDispositions"], 1)
        self.assertFalse(report["closure"]["valid"])
        self.assertEqual(report["integrity"]["foreignKeyViolations"], 0)

    def test_closure_rejects_generic_deferred_and_requires_reason_category(self) -> None:
        self.conn.execute(
            """INSERT INTO raw_artifact_dispositions(
                   raw_artifact_id,disposition,rationale,decision_method,
                   decision_confidence,requires_human_review,decided_by
               ) VALUES('RAW','DEFERRED',?,?,0.0,1,'test')""",
            (
                "No defensible globally reconciled canonical was selected from the current tracked classification evidence.",
                "DETERMINISTIC_GLOBAL_RECONCILIATION",
            ),
        )
        self.conn.commit()
        first = validate_catalog(self.path)["closure"]
        self.assertFalse(first["valid"])
        self.assertEqual(first["genericDeferredRationales"], 1)
        self.assertEqual(first["deferredWithoutReasonCode"], 1)
        self.conn.execute(
            "UPDATE raw_artifact_dispositions SET rationale=?,decision_method=? WHERE raw_artifact_id='RAW'",
            (
                "The source statement combines two outcomes and authoritative text does not define an atomic split.",
                "SEMANTIC_RECONCILIATION_V1",
            ),
        )
        self.conn.execute(
            "INSERT INTO raw_artifact_deferred_reasons(raw_artifact_id,reason_code) VALUES('RAW','ATOMICITY_AMBIGUITY')"
        )
        self.conn.commit()
        second = validate_catalog(self.path)["closure"]
        self.assertTrue(second["valid"])

    def test_unresolved_type_is_deferred_without_art_ctr_default(self) -> None:
        raw = {
            "usacm_type_assigned": None,
            "sdt_domain_assigned": None,
            "sdt_subdomain_assigned": None,
            "context_paragraph": None,
            "title_draft": "Unclassified entry",
            "description_draft": "A neutral statement with no type signal.",
            "raw_text_en": "A neutral statement with no classification signal.",
            "source_type": "DOCUMENT",
            "is_ambiguous": 0,
        }
        result = classify(raw)
        self.assertIsNone(result["proposed_type"])
        self.assertIsNone(result["proposed_abstraction_level"])
        self.assertEqual(result["disposition"], "DEFERRED")
        self.assertEqual(result["curation_status"], "NEEDS_REVIEW")
        self.assertIn("without a default", result["rationale"])

    def test_cli_exit_code_and_report_hash_are_stable(self) -> None:
        self._insert_artifact()
        output = Path(self.temp.name) / "validation.json"
        with redirect_stdout(StringIO()):
            first_code = validation_main(["--db", str(self.path), "--output", str(output)])
        first = json.loads(output.read_text(encoding="utf-8"))
        with redirect_stdout(StringIO()):
            second_code = validation_main(["--db", str(self.path), "--output", str(output)])
        second = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(first_code, 0)
        self.assertEqual(second_code, 0)
        self.assertEqual(first["reportSha256"], second["reportSha256"])

        self.conn.execute(
            """INSERT INTO raw_artifacts(
                   id,source_catalog_id,source_document,source_version,raw_json,
                   source_file,content_hash,source_manifest_id
               ) VALUES('RAW-3','SRC','Source','1','{}','source.json',?,'MAN')""",
            ("e" * 64,),
        )
        self.conn.commit()
        with redirect_stdout(StringIO()):
            failure_code = validation_main(["--db", str(self.path)])
        self.assertEqual(failure_code, 1)


if __name__ == "__main__":
    unittest.main()
