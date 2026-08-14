"""Build deterministic semantic-audit evidence from pinned raw catalogs."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from secureguide.catalog_validation import canonical_hash
from secureguide.catalog_curation import (
    build_projection,
    final_artifact_id,
    load_curation_candidates,
    prepare_curation_database,
)
from secureguide.semantic_classification import canonical_text, classify_record, normalize_text


ROOT = Path(__file__).resolve().parent.parent
CSF_SOURCES = (
    ROOT / "SecureGuide_Mobile_Docs" / "Raw_Catalogs" / "nist_csf_2_0.json",
    ROOT / "SecureGuide_Mobile_Docs" / "Raw_Catalogs" / "the_nist_cybersecurity_framework_csf_2_0.json",
)


def _raw_hash(record: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(record, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def build_csf_audit(sources: tuple[Path, ...] = CSF_SOURCES) -> dict[str, Any]:
    """Classify every pinned CSF outcome independently and retain no source prose."""

    records: list[dict[str, Any]] = []
    before: Counter[str] = Counter()
    after: Counter[str] = Counter()
    unresolved: list[dict[str, str]] = []
    for source in sources:
        envelope = json.loads(source.read_text(encoding="utf-8"))
        catalog_id = str((envelope.get("extraction_metadata") or {}).get("source_catalog_id"))
        for index, raw in enumerate(envelope.get("artifacts") or []):
            item = json.loads(json.dumps(raw))
            item.setdefault("source_metadata", {})["source_catalog_id"] = catalog_id
            raw_id = f"{catalog_id}::{index:04d}"
            before[str((raw.get("classification_status") or {}).get("usacm_type_assigned") or "UNCLASSIFIED")] += 1
            try:
                result = classify_record(item)
            except ValueError as error:
                unresolved.append({"rawId": raw_id, "rawHash": _raw_hash(raw), "reason": str(error)})
                continue
            after[result["proposed_type"]] += 1
            records.append({
                "rawId": raw_id,
                "rawHash": _raw_hash(raw),
                "type": result["proposed_type"],
                "abstractionLevel": result["proposed_abstraction_level"],
                "primaryDomain": result["proposed_primary_domain"],
                "subDomain": result["proposed_sub_domain"],
                "confidence": result["classification_confidence"],
                "requiresHumanReview": result["requires_human_review"],
                "method": result["classification_method"],
            })
    material = {
        "contract": "secureguide-csf-record-audit-v1",
        "sourceFiles": [source.relative_to(ROOT).as_posix() for source in sources],
        "totalRecords": len(records) + len(unresolved),
        "resolvedRecords": len(records),
        "unresolvedRecords": len(unresolved),
        "typeDistributionBefore": dict(sorted(before.items())),
        "typeDistributionAfter": dict(sorted(after.items())),
        "records": records,
        "unresolved": unresolved,
    }
    material["auditSha256"] = canonical_hash({**material, "auditSha256": None})
    return material


def _decision_hash(material: dict[str, Any]) -> str:
    return canonical_hash({**material, "ledger_sha256": None})


def _new_candidate(row: Any, result: dict[str, Any]) -> dict[str, Any]:
    artifact_type = result["proposed_type"]
    artifact_id = f"SG-{artifact_type[4:]}-SRC-{str(row['content_hash'])[:12].upper()}"
    title = result["title_en"]
    if not any(character.isalpha() for character in title):
        title = f"{row['source_document'] or row['source_catalog_id']} {row['source_section'] or title}"
    candidate = {
        "artifact_id": artifact_id,
        "candidate_id": f"STG-SRC-{str(row['content_hash'])[:12].upper()}",
        "source_key": "SRC",
        "raw_id": row["id"],
        "external_raw_id": row["external_raw_id"],
        "source_catalog_id": row["source_catalog_id"],
        "source_document": row["source_document"] or row["source_catalog_id"],
        "source_type_raw": row["source_type"] or "DOCUMENT",
        "source_version": row["source_version"] or "UNKNOWN",
        "source_section": row["source_section"],
        "title_en": title,
        "definition_short_en": result["definition_short_en"],
        "definition_full_en": canonical_text(row["raw_text_en"] or "") or None,
        "type": artifact_type,
        "abstraction_level": result["proposed_abstraction_level"],
        "primary_domain": result["proposed_primary_domain"],
        "sub_domain": result["proposed_sub_domain"],
        "obligation_level": result["proposed_obligation_level"],
        "requirement_type": result["proposed_requirement_type"],
        "control_nature": result["proposed_control_nature"],
        "control_function": result["proposed_control_function"],
        "testability": result["proposed_testability"],
        "priority": result["proposed_priority"],
        "classification_confidence": result["classification_confidence"],
        "classification_rationale": result["classification_rationale"],
        "requires_human_review": result["requires_human_review"],
        "mappings": [], "tags": [], "relationships": [], "actions": [],
        "external_references": result["external_references"],
    }
    return candidate


def build_semantic_ledger(base_database: Path) -> dict[str, Any]:
    """Create one source-hash-bound decision per record from pinned inputs."""

    import sqlite3
    from tempfile import TemporaryDirectory

    candidates = load_curation_candidates()
    projection = build_projection(candidates)
    existing_targets = {
        raw_id: final_artifact_id(candidates[selected])
        for raw_id, selected in projection["rawToCandidate"].items()
    }
    with TemporaryDirectory() as temporary:
        database = Path(temporary) / "raw.db"
        prepare_curation_database(base_database, database)
        conn = sqlite3.connect(database)
        conn.row_factory = sqlite3.Row
        try:
            # Legacy staging mappings carry source lineage for any catalog row
            # outside the selected curated/legacy inputs.
            for row in conn.execute(
                "SELECT promoted_artifact_id, proposed_mappings_json FROM staging_artifacts "
                "WHERE promoted_artifact_id IS NOT NULL"
            ):
                for mapping in json.loads(row["proposed_mappings_json"] or "[]"):
                    if mapping.get("raw_id"):
                        existing_targets.setdefault(mapping["raw_id"], row["promoted_artifact_id"])
            for row in conn.execute(
                "SELECT raw_artifact_id,artifact_id FROM artifact_source_lineage"
            ):
                existing_targets.setdefault(row["raw_artifact_id"], row["artifact_id"])
            existing_signatures = {
                (normalize_text(row["title_en"]), normalize_text(row["definition_short_en"])): row["id"]
                for row in conn.execute("SELECT id,title_en,definition_short_en FROM security_artifacts")
            }
            used_titles = {
                normalize_text(row["title_en"])
                for row in conn.execute("SELECT title_en FROM security_artifacts")
            }
            used_titles.update(
                normalize_text(candidates[candidate_id]["title_en"])
                for candidate_id in projection["selected"]
            )
            generated_signatures: dict[tuple[str, str, str, str], str] = {}
            decisions: list[dict[str, Any]] = []
            for row in conn.execute("SELECT * FROM raw_artifacts ORDER BY id"):
                raw_id = row["id"]
                target = existing_targets.get(raw_id)
                if target:
                    decisions.append({
                        "raw_id": raw_id, "source_content_sha256": row["content_hash"],
                        "disposition": "SUPPORTS_CANONICAL", "target_artifact_id": target,
                        "mapping_strength": "DIRECT", "decision_method": "PINNED_EXISTING_LINEAGE_V1",
                        "confidence_state": "1.00", "rationale": f"Pinned existing lineage selects canonical {target}.",
                    })
                    continue
                raw = json.loads(row["raw_json"])
                raw.setdefault("source_metadata", {})["source_catalog_id"] = row["source_catalog_id"]
                try:
                    result = classify_record(raw)
                except ValueError as error:
                    decisions.append({
                        "raw_id": raw_id, "source_content_sha256": row["content_hash"],
                        "disposition": "DEFERRED", "decision_method": "SEMANTIC_BOUNDARY_REVIEW_V1",
                        "confidence_state": "UNSCORED", "deferred_reason_code": "UNRESOLVED_SEMANTIC_BOUNDARY",
                        "rationale": f"{raw_id} has no defensible SDT classification from its own statement and approved source tie-breakers: {error}.",
                    })
                    continue
                signature = (normalize_text(result["title_en"]), normalize_text(result["definition_short_en"]))
                existing = existing_signatures.get(signature)
                if existing:
                    decisions.append({
                        "raw_id": raw_id, "source_content_sha256": row["content_hash"],
                        "disposition": "SUPPORTS_CANONICAL", "target_artifact_id": existing,
                        "mapping_strength": "DIRECT", "decision_method": "EXACT_SEMANTIC_MATCH_V1",
                        "confidence_state": "1.00", "rationale": f"Exact normalized title and statement match existing canonical {existing}.",
                    })
                    continue
                generated_signature = (
                    result["proposed_type"], result["proposed_primary_domain"],
                    result["proposed_sub_domain"], *signature,
                )
                target = generated_signatures.get(generated_signature)
                if target:
                    decisions.append({
                        "raw_id": raw_id, "source_content_sha256": row["content_hash"],
                        "disposition": "SUPPORTS_CANONICAL", "target_artifact_id": target,
                        "mapping_strength": "DIRECT", "decision_method": "EXACT_CROSS_SOURCE_MATCH_V1",
                        "confidence_state": "1.00", "rationale": f"Exact normalized atomic statement matches generated canonical {target}.",
                    })
                    continue
                candidate = _new_candidate(row, result)
                normalized_title = normalize_text(candidate["title_en"])
                if normalized_title in used_titles:
                    source_identity = row["external_raw_id"] or row["source_section"] or raw_id
                    candidate["title_en"] = f"{candidate['title_en']} [{source_identity}]"
                    normalized_title = normalize_text(candidate["title_en"])
                used_titles.add(normalized_title)
                target = candidate["artifact_id"]
                generated_signatures[generated_signature] = target
                decisions.append({
                    "raw_id": raw_id, "source_content_sha256": row["content_hash"],
                    "disposition": "SUPPORTS_CANONICAL", "target_artifact_id": target,
                    "new_canonical": candidate, "mapping_strength": "DIRECT",
                    "decision_method": "ATOMIC_SOURCE_CANONICAL_V1",
                    "confidence_state": f"{result['classification_confidence']:.2f}",
                    "rationale": (
                        f"Atomic source statement was classified as {result['proposed_type']} / "
                        f"{result['proposed_sub_domain']} and has no exact existing canonical match."
                    ),
                })
        finally:
            conn.close()
    material = {"schema_version": 1, "ledger_sha256": None, "decisions": decisions}
    material["ledger_sha256"] = _decision_hash(material)
    return material


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "consolidation" / "semantic_audit.json")
    parser.add_argument("--rebuild-ledger", action="store_true")
    parser.add_argument("--base-database", type=Path, default=ROOT / "catalog.db")
    args = parser.parse_args()
    if args.rebuild_ledger:
        report = build_semantic_ledger(args.base_database)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"decisions": len(report["decisions"]), "ledgerSha256": report["ledger_sha256"]}, indent=2))
        return
    report = build_csf_audit()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("totalRecords", "resolvedRecords", "unresolvedRecords", "auditSha256")}, indent=2))


if __name__ == "__main__":
    main()
