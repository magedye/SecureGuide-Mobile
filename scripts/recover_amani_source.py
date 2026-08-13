"""Recover the DB-only amani v4 source snapshot without inventing metadata.

This one-time reproducibility repair reads preserved raw and staging rows from
the existing working database and emits a deterministic Raw_Catalogs envelope.
The original raw JSON and its content hash are retained inside every record.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "catalog_work.db"
DEFAULT_OUTPUT = ROOT / "SecureGuide_Mobile_Docs" / "Raw_Catalogs" / "amani_v4_recovered.json"


STAGING_FIELDS = (
    "title_en", "definition_short_en", "definition_full_en",
    "proposed_type", "proposed_abstraction_level", "proposed_primary_domain",
    "proposed_sub_domain", "proposed_obligation_level", "proposed_requirement_type",
    "proposed_control_nature", "proposed_control_function", "proposed_testability",
    "classification_confidence", "classification_rationale", "requires_human_review",
    "curation_status", "quality_score", "proposed_priority", "proposed_mappings_json",
    "proposed_tags_json", "proposed_relationships_json", "proposed_actions_json",
    "proposed_variants_json", "proposed_security_objectives_json",
    "proposed_csf_functions_json", "proposed_control_purposes_json",
    "proposed_implementation_types_json", "proposed_maturity_requirements_json",
    "proposed_verification_json", "proposed_threats_json", "proposed_platforms_json",
    "proposed_amani_provenance_json",
)


def recover(database: Path, output: Path) -> dict[str, object]:
    conn = sqlite3.connect(database)
    conn.row_factory = sqlite3.Row
    try:
        catalog = conn.execute(
            "SELECT * FROM source_catalogs WHERE id='amani_v4'"
        ).fetchone()
        if not catalog:
            raise ValueError("catalog_work.db has no amani_v4 source catalog")
        raw_rows = conn.execute(
            "SELECT * FROM raw_artifacts WHERE source_catalog_id='amani_v4' ORDER BY id"
        ).fetchall()
        if len(raw_rows) != 706:
            raise ValueError(f"expected 706 preserved amani rows, found {len(raw_rows)}")
        artifacts = []
        for raw in raw_rows:
            number = int(raw["id"].rsplit("::", 1)[1])
            staging = conn.execute(
                "SELECT * FROM staging_artifacts WHERE id=?", (f"STG-AMANI-{number:04d}",)
            ).fetchone()
            if not staging:
                raise ValueError(f"missing staging evidence for {raw['id']}")
            artifacts.append({
                "raw_artifact_id": raw["external_raw_id"],
                "source_metadata": {
                    "source_document": raw["source_document"],
                    "source_type": raw["source_type"],
                    "source_section": raw["source_section"],
                    "source_version": raw["source_version"],
                    "source_url": raw["source_url"],
                },
                "original_content": {
                    "raw_text_en": raw["raw_text_en"],
                    "raw_text_ar": raw["raw_text_ar"],
                    "original_heading": raw["original_heading"],
                    "context_paragraph": raw["context_paragraph"],
                },
                "extracted_elements": {
                    "title_draft": raw["title_draft"],
                    "description_draft": raw["description_draft"],
                    "keywords": json.loads(raw["keywords_json"] or "[]"),
                    "entities_mentioned": json.loads(raw["entities_mentioned_json"] or "[]"),
                },
                "classification_status": {
                    "usacm_type_assigned": raw["usacm_type_assigned"],
                    "sdt_domain_assigned": raw["sdt_domain_assigned"],
                    "sdt_subdomain_assigned": raw["sdt_subdomain_assigned"],
                    "requires_classification": bool(raw["requires_classification"]),
                },
                "quality_flags": {
                    "needs_human_review": bool(raw["needs_human_review"]),
                    "is_ambiguous": bool(raw["is_ambiguous"]),
                    "ambiguity_reason": raw["ambiguity_reason"],
                },
                "recovery_provenance": {
                    "preserved_raw_id": raw["id"],
                    "preserved_content_hash": raw["content_hash"],
                    "original_raw_record": json.loads(raw["raw_json"]),
                    "staging_id": staging["id"],
                    "staging_evidence": {field: staging[field] for field in STAGING_FIELDS},
                },
            })
        envelope = {
            "extraction_metadata": {
                "source_catalog_id": "amani_v4",
                "source_document": catalog["name"],
                "source_version": catalog["version"],
                "total_artifacts": len(artifacts),
                "recovery_source": "catalog_work.db preserved raw_artifacts and staging_artifacts",
                "recovery_policy": "No unavailable upstream metadata or rights were inferred.",
            },
            "artifacts": artifacts,
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(envelope, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8", newline="\n",
        )
        return {"output": str(output), "rawRecordCount": len(artifacts)}
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps(recover(args.db, args.output), indent=2))


if __name__ == "__main__":
    main()
