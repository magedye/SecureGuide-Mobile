"""Schema and export/validation tests for the nine-sheet catalog workbook."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from openpyxl import load_workbook

from secureguide.catalog_workbook import export_workbook, validate_workbook
from secureguide.database import apply_migrations


EXPECTED_SHEETS = [
    "00_Manifest", "01_Artifacts", "02_Source_Lineage",
    "03_Framework_Mappings", "04_Relationships", "05_Tags",
    "06_Type_Specific", "07_Reference_Lists", "08_Validation_Errors",
]


class WorkbookSchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "workbook.db"
        apply_migrations(self.db)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_audit_schema_is_additive_and_constrained(self) -> None:
        conn = sqlite3.connect(self.db)
        try:
            tables = {row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )}
            self.assertIn("catalog_workbook_runs", tables)
            self.assertIn("catalog_workbook_row_audit", tables)
            conn.execute(
                """INSERT INTO catalog_workbook_runs(
                       id,operation,workbook_path,baseline_db_sha256,status,actor
                   ) VALUES('RUN','EXPORT','catalog.xlsx',?,'STARTED','tester')""",
                ("a" * 64,),
            )
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute(
                    """INSERT INTO catalog_workbook_row_audit(
                           run_id,sheet_name,row_key,action,outcome
                       ) VALUES('RUN','01_Artifacts','A','DELETE','VALID')"""
                )
        finally:
            conn.close()

    def _seed_catalog(self) -> None:
        conn = sqlite3.connect(self.db)
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            conn.execute(
                "INSERT INTO source_catalogs(id,name,source_type,version) VALUES('SRC','Source','STANDARD','1')"
            )
            conn.execute(
                """INSERT INTO source_import_manifests(
                       id,source_catalog_id,source_version,source_file,source_sha256,
                       manifest_sha256,importer_name,importer_version,raw_record_count
                   ) VALUES('MAN','SRC','1','source.json',?,?, 'test','1',1)""",
                ("a" * 64, "b" * 64),
            )
            conn.execute(
                """INSERT INTO source_rights_versions(
                       id,source_catalog_id,source_version,rights_version,
                       redistribution_status,ship_raw_text,decision_reason,decided_by
                   ) VALUES('RIGHT','SRC','1','1','UNKNOWN',0,'No evidence','test')"""
            )
            conn.execute(
                """INSERT INTO raw_artifacts(
                       id,source_catalog_id,source_document,source_type,source_version,
                       source_section,raw_text_en,raw_json,source_file,content_hash,source_manifest_id
                   ) VALUES('RAW','SRC','Source','STANDARD','1','1','raw','{}','source.json',?,'MAN')""",
                ("c" * 64,),
            )
            conn.execute(
                """INSERT INTO security_artifacts(
                       id,source_catalog_id,type,title_en,definition_short_en,
                       primary_domain,sub_domain,abstraction_level,source,source_type,
                       obligation_level,granularity_level,control_nature,control_function,
                       testability,classification_confidence,classification_rationale,
                       ai_review_status,requires_human_review,publication_status,source_document
                   ) VALUES('SG-CTR-1','SRC','ART-CTR','Maintain inventory','Maintain an accurate inventory.',
                            'SD-02','SD-02.01','ABS-CTR','SRC-STD','STANDARD','OBL-MND',
                            'GRN-MEDIUM','NAT-ORG','FUN-PRE','TST-MAN',0.65,
                            'A safeguard that reduces inventory risk.','AIR-HUMAN-REVIEW',1,'APPROVED','Source')"""
            )
            conn.execute(
                """INSERT INTO artifact_source_lineage(
                       artifact_id,raw_artifact_id,lineage_role,mapping_strength,is_primary
                   ) VALUES('SG-CTR-1','RAW','SUPPORTS_CANONICAL','DIRECT',1)"""
            )
            conn.execute(
                """INSERT INTO raw_artifact_dispositions(
                       raw_artifact_id,disposition,rationale,decision_method,
                       decision_confidence,requires_human_review,decided_by
                   ) VALUES('RAW','SUPPORTS_CANONICAL','Primary source','TEST',0.65,1,'test')"""
            )
            conn.commit()
        finally:
            conn.close()

    def test_export_has_exact_sheets_named_lists_and_validates(self) -> None:
        self._seed_catalog()
        workbook = Path(self.temp.name) / "catalog.xlsx"
        result = export_workbook(self.db, workbook)
        self.assertEqual(result["sheets"], EXPECTED_SHEETS)
        wb = load_workbook(workbook, data_only=False)
        self.assertEqual(wb.sheetnames, EXPECTED_SHEETS)
        self.assertIn("REF_TYPE", wb.defined_names)
        self.assertGreater(len(wb["01_Artifacts"].data_validations.dataValidation), 1)
        validation = validate_workbook(workbook, self.db)
        self.assertTrue(validation["valid"], validation["errors"][:3])

    def test_formula_and_edit_without_action_are_rejected(self) -> None:
        self._seed_catalog()
        workbook = Path(self.temp.name) / "catalog.xlsx"
        export_workbook(self.db, workbook)
        wb = load_workbook(workbook)
        ws = wb["01_Artifacts"]
        headers = {cell.value: cell.column for cell in ws[1]}
        ws.cell(2, headers["title_en"], "=\"Changed\"")
        wb.save(workbook)
        result = validate_workbook(workbook, self.db)
        codes = {error["code"] for error in result["errors"]}
        self.assertIn("FORMULA", codes)
        self.assertIn("ACTION_REQUIRED", codes)


if __name__ == "__main__":
    unittest.main()
