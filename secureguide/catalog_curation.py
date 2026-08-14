"""Deterministic catalog curation primitives.

The module deliberately separates mechanical provenance backfill from later
canonical selection.  It never invents a version, license, or rights grant.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
from pathlib import Path
from typing import Any

import yaml

from secureguide.catalog_validation import canonical_hash, file_hash
from secureguide.catalog_validation import validate_catalog
from secureguide.database import apply_migrations, connect
from secureguide.semantic_classification import canonical_text, external_references


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE_MANIFEST = ROOT / "config" / "source_manifest.json"
DEFAULT_SOURCE_RIGHTS = ROOT / "config" / "source_rights.yaml"
DEFAULT_EQUIVALENCE = ROOT / "consolidation" / "unified" / "equivalence.json"
DEFAULT_CURATED_CLASSIFICATIONS = ROOT / "consolidation" / "curated" / "classifications.json"
DEFAULT_CURATED_RAW = ROOT / "SecureGuide_Mobile_Docs" / "Raw_Catalogs" / "securekit_curated_controls.json"
DEFAULT_LEGACY_CLASSIFICATIONS = ROOT / "consolidation" / "curated" / "legacy_classifications.json"
DEFAULT_TEXT_CORRECTIONS = ROOT / "config" / "catalog_text_corrections.json"
DEFAULT_LEGACY_RAW = ROOT / "SecureGuide_Mobile_Docs" / "Raw_Catalogs" / "legacy_catalog_v4_recovered.json"


class CurationInputError(ValueError):
    """A pinned curation input is missing, stale, or internally inconsistent."""


def load_source_manifest(path: str | Path = DEFAULT_SOURCE_MANIFEST) -> dict[str, Any]:
    path = Path(path)
    manifest = json.loads(path.read_text(encoding="utf-8"))
    expected = manifest.get("manifest_sha256")
    hashed = dict(manifest)
    hashed["manifest_sha256"] = None
    actual = canonical_hash(hashed)
    if expected != actual:
        raise CurationInputError(
            f"source manifest semantic hash mismatch: expected {expected}, got {actual}"
        )
    if manifest.get("source_count") != len(manifest.get("sources", [])):
        raise CurationInputError("source manifest source_count mismatch")
    if manifest.get("raw_record_count") != sum(
        int(item["raw_record_count"]) for item in manifest["sources"]
    ):
        raise CurationInputError("source manifest raw_record_count mismatch")
    return manifest


def load_source_rights(path: str | Path = DEFAULT_SOURCE_RIGHTS) -> dict[str, Any]:
    rights = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if rights.get("schema_version") != 1 or not isinstance(rights.get("rights"), list):
        raise CurationInputError("unsupported source-rights contract")
    for item in rights["rights"]:
        if item["redistribution_status"] not in {"ALLOWED", "RESTRICTED", "UNKNOWN"}:
            raise CurationInputError(f"invalid rights status for {item['id']}")
        if item.get("ship_raw_text") and item["redistribution_status"] != "ALLOWED":
            raise CurationInputError(f"fail-closed rights violation for {item['id']}")
    return rights


def verify_pinned_sources(
    manifest: dict[str, Any], root: str | Path = ROOT
) -> dict[str, Any]:
    root = Path(root)
    errors: list[str] = []
    total_records = 0
    total_bytes = 0
    for item in manifest["sources"]:
        source = root / item["source_file"]
        if not source.is_file():
            errors.append(f"missing:{item['source_file']}")
            continue
        if file_hash(source) != item["source_sha256"]:
            errors.append(f"hash:{item['source_file']}")
        if source.stat().st_size != int(item["source_bytes"]):
            errors.append(f"bytes:{item['source_file']}")
        total_records += int(item["raw_record_count"])
        total_bytes += source.stat().st_size
    return {
        "valid": not errors,
        "errors": errors,
        "sourceCount": len(manifest["sources"]),
        "rawRecordCount": total_records,
        "totalBytes": total_bytes,
    }


def backfill_source_provenance(
    conn: sqlite3.Connection,
    manifest_path: str | Path = DEFAULT_SOURCE_MANIFEST,
    rights_path: str | Path = DEFAULT_SOURCE_RIGHTS,
    *,
    verify_files: bool = True,
    root: str | Path = ROOT,
) -> dict[str, Any]:
    """Backfill pinned manifests and fail-closed rights transactionally."""

    conn.row_factory = sqlite3.Row
    manifest = load_source_manifest(manifest_path)
    rights = load_source_rights(rights_path)
    source_check = verify_pinned_sources(manifest, root)
    if verify_files and not source_check["valid"]:
        raise CurationInputError("; ".join(source_check["errors"]))

    known_catalogs = {
        row[0] for row in conn.execute("SELECT id FROM source_catalogs")
    }
    configured_catalogs: set[str] = set()
    manifests_written = rights_written = rows_linked = 0
    try:
        conn.execute("BEGIN IMMEDIATE")
        for item in manifest["sources"]:
            catalog_id = item["source_catalog_id"]
            if catalog_id not in known_catalogs:
                continue
            configured_catalogs.add(catalog_id)
            source_version = item["source_version"]
            conn.execute(
                """INSERT INTO source_import_manifests(
                       id,source_catalog_id,source_version,version_unknown_reason,
                       source_file,source_sha256,manifest_sha256,retrieval_uri,
                       retrieved_at,importer_name,importer_version,raw_record_count
                   ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET
                     source_version=excluded.source_version,
                     version_unknown_reason=excluded.version_unknown_reason,
                     source_file=excluded.source_file,
                     source_sha256=excluded.source_sha256,
                     manifest_sha256=excluded.manifest_sha256,
                     retrieval_uri=excluded.retrieval_uri,
                     retrieved_at=excluded.retrieved_at,
                     importer_name=excluded.importer_name,
                     importer_version=excluded.importer_version,
                     raw_record_count=excluded.raw_record_count""",
                (
                    item["id"], catalog_id, source_version,
                    item.get("version_unknown_reason"), item["source_file"],
                    item["source_sha256"], manifest["manifest_sha256"],
                    item.get("retrieval_uri"), item.get("retrieved_at"),
                    manifest["importer"]["name"], manifest["importer"]["version"],
                    item["raw_record_count"],
                ),
            )
            manifests_written += 1
            cursor = conn.execute(
                """UPDATE raw_artifacts
                      SET source_manifest_id=?, source_version=?
                    WHERE source_catalog_id=?
                      AND (source_file=? OR source_file=?)""",
                (
                    item["id"], source_version, catalog_id, item["source_file"],
                    Path(item["source_file"]).name,
                ),
            )
            rows_linked += cursor.rowcount

        for item in rights["rights"]:
            if item["source_catalog_id"] not in known_catalogs:
                continue
            conn.execute(
                """INSERT INTO source_rights_versions(
                       id,source_catalog_id,source_version,rights_version,
                       redistribution_status,ship_raw_text,license_identifier,
                       terms_url,evidence_sha256,evidence_retrieved_at,
                       attribution_text,decision_reason,decided_by,decided_at,
                       supersedes_id,is_current
                   ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET
                     redistribution_status=excluded.redistribution_status,
                     ship_raw_text=excluded.ship_raw_text,
                     license_identifier=excluded.license_identifier,
                     terms_url=excluded.terms_url,
                     evidence_sha256=excluded.evidence_sha256,
                     evidence_retrieved_at=excluded.evidence_retrieved_at,
                     attribution_text=excluded.attribution_text,
                     decision_reason=excluded.decision_reason,
                     decided_by=excluded.decided_by,
                     decided_at=excluded.decided_at,
                     supersedes_id=excluded.supersedes_id,
                     is_current=excluded.is_current""",
                (
                    item["id"], item["source_catalog_id"], item["source_version"],
                    item["rights_version"], item["redistribution_status"],
                    int(bool(item["ship_raw_text"])), item.get("license_identifier"),
                    item.get("terms_url"), item.get("evidence_sha256"),
                    item.get("evidence_retrieved_at"), item.get("attribution_text"),
                    item["decision_reason"], item["decided_by"], item["decided_at"],
                    item.get("supersedes_id"), int(bool(item["is_current"])),
                ),
            )
            rights_written += 1
        conn.execute("COMMIT")
    except Exception:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise

    missing_manifest = conn.execute(
        "SELECT COUNT(*) FROM raw_artifacts WHERE source_manifest_id IS NULL"
    ).fetchone()[0]
    missing_rights = conn.execute(
        """SELECT COUNT(*) FROM raw_artifacts r WHERE NOT EXISTS(
               SELECT 1 FROM source_rights_versions sr
                WHERE sr.source_catalog_id=r.source_catalog_id
                  AND sr.source_version=COALESCE(r.source_version,'UNKNOWN')
                  AND sr.is_current=1)"""
    ).fetchone()[0]
    return {
        "manifestSha256": manifest["manifest_sha256"],
        "manifestsWritten": manifests_written,
        "rightsWritten": rights_written,
        "rawRowsLinked": rows_linked,
        "missingManifestRows": int(missing_manifest),
        "missingRightsRows": int(missing_rights),
        "unconfiguredCatalogs": sorted(known_catalogs - configured_catalogs),
        "sourceVerification": source_check,
    }


def _decoded(value: Any, default: Any) -> Any:
    if value in (None, ""):
        return default
    return json.loads(value) if isinstance(value, str) else value


def load_curation_candidates(
    curated_classifications: str | Path = DEFAULT_CURATED_CLASSIFICATIONS,
    curated_raw: str | Path = DEFAULT_CURATED_RAW,
    legacy_classifications: str | Path = DEFAULT_LEGACY_CLASSIFICATIONS,
    text_corrections: str | Path = DEFAULT_TEXT_CORRECTIONS,
    legacy_raw: str | Path = DEFAULT_LEGACY_RAW,
) -> dict[str, dict[str, Any]]:
    """Load the tracked 761 curated and 706 pinned recovered candidates."""

    classified = json.loads(Path(curated_classifications).read_text(encoding="utf-8"))
    curated_envelope = json.loads(Path(curated_raw).read_text(encoding="utf-8"))
    legacy_pinned = json.loads(Path(legacy_classifications).read_text(encoding="utf-8"))
    legacy_envelope = json.loads(Path(legacy_raw).read_text(encoding="utf-8"))
    if len(classified) != len(curated_envelope["artifacts"]):
        raise CurationInputError("curated classifications do not cover the curated raw source")
    pinned_hash = legacy_pinned.get("semantic_sha256")
    pinned_material = dict(legacy_pinned)
    pinned_material.pop("semantic_sha256", None)
    if pinned_hash != canonical_hash(pinned_material):
        raise CurationInputError("legacy classification semantic hash mismatch")
    if legacy_pinned.get("input_sha256") != file_hash(legacy_raw):
        raise CurationInputError("legacy classifications are stale for the recovered source")
    if legacy_pinned.get("reference_sha256") != file_hash(curated_classifications):
        raise CurationInputError("legacy classifications are stale for the curated reference")
    legacy_items = legacy_pinned.get("items") or []
    if legacy_pinned.get("item_count") != len(legacy_items) or len(legacy_items) != len(legacy_envelope["artifacts"]):
        raise CurationInputError("legacy classifications do not cover the recovered source")
    candidates: dict[str, dict[str, Any]] = {}
    for index, (classification, raw) in enumerate(zip(classified, curated_envelope["artifacts"])):
        raw_id = f"securekit_curated_controls::{index:04d}"
        if classification["raw_id"] != raw_id:
            raise CurationInputError(f"curated classification order mismatch at {raw_id}")
        source = raw.get("source_metadata") or {}
        full_text = (raw.get("original_content") or {}).get("raw_text_en") or ""
        candidates[f"STG-CURATED-{index:04d}"] = {
            "candidate_id": f"STG-CURATED-{index:04d}", "source_key": "CURATED",
            "raw_id": raw_id, "external_raw_id": raw.get("raw_artifact_id"),
            "source_catalog_id": "securekit_curated_controls",
            "source_document": source.get("source_document") or "SecureGuide Curated Controls v1",
            "source_type_raw": source.get("source_type") or "STANDARD",
            "source_version": source.get("source_version") or "1",
            "source_section": source.get("source_section"),
            "title_en": classification.get("title_en"),
            "definition_short_en": classification.get("definition_short_en"),
            "definition_full_en": canonical_text(full_text) or None,
            "type": classification.get("proposed_type"),
            "abstraction_level": classification.get("proposed_abstraction_level"),
            "primary_domain": classification.get("proposed_primary_domain"),
            "sub_domain": classification.get("proposed_sub_domain"),
            "obligation_level": classification.get("proposed_obligation_level"),
            "requirement_type": classification.get("proposed_requirement_type"),
            "control_nature": classification.get("proposed_control_nature"),
            "control_function": classification.get("proposed_control_function"),
            "testability": classification.get("proposed_testability"),
            "asset_type": classification.get("proposed_asset_type"),
            "asset_criticality": classification.get("proposed_asset_criticality"),
            "priority": classification.get("proposed_priority") or "PRI-MEDIUM",
            "classification_confidence": classification.get("classification_confidence"),
            "classification_rationale": classification.get("classification_rationale"),
            "requires_human_review": bool(classification.get("needs_split")),
            "threats": classification.get("proposed_threats") or [],
            "platforms": [], "mappings": [], "tags": [], "relationships": [],
            "actions": [], "external_references": external_references(full_text),
            "legacy_provenance": None,
        }

    for index, (classification, raw) in enumerate(zip(legacy_items, legacy_envelope["artifacts"])):
        recovery = raw.get("recovery_provenance") or {}
        evidence = recovery.get("staging_evidence") or {}
        candidate_id = f"STG-LEGACY-{index:04d}"
        expected_raw_id = f"legacy_catalog_v4::{index:04d}"
        if classification.get("raw_id") != expected_raw_id:
            raise CurationInputError(f"legacy classification order mismatch at {expected_raw_id}")
        source = raw.get("source_metadata") or {}
        original = recovery.get("original_raw_record") or {}
        full_text = evidence.get("definition_full_en") or (raw.get("original_content") or {}).get("raw_text_en") or ""
        candidates[candidate_id] = {
            "candidate_id": candidate_id, "source_key": "CAT",
            "raw_id": expected_raw_id,
            "external_raw_id": raw.get("raw_artifact_id"),
            "legacy_artifact_id": (
                str(recovery.get("staging_id") or "").replace(
                    "STG-", f"SG-{str(evidence.get('proposed_type') or 'ART-CTR')[4:]}-", 1
                )
                or None
            ),
            "source_catalog_id": "legacy_catalog_v4",
            "source_document": "SecureGuide Legacy Catalog v4",
            "source_type_raw": source.get("source_type") or "GUIDELINE",
            "source_version": source.get("source_version") or "4.1.0",
            "source_section": source.get("source_section"),
            "title_en": classification.get("title_en"),
            "definition_short_en": classification.get("definition_short_en"),
            "definition_full_en": canonical_text(full_text) or None,
            "type": classification.get("proposed_type"),
            "abstraction_level": classification.get("proposed_abstraction_level"),
            "primary_domain": classification.get("proposed_primary_domain"),
            "sub_domain": classification.get("proposed_sub_domain"),
            "obligation_level": classification.get("proposed_obligation_level"),
            "requirement_type": classification.get("proposed_requirement_type"),
            "control_nature": classification.get("proposed_control_nature"),
            "control_function": classification.get("proposed_control_function"),
            "testability": classification.get("proposed_testability"),
            "asset_type": classification.get("proposed_asset_type"),
            "asset_criticality": classification.get("proposed_asset_criticality"),
            "priority": classification.get("proposed_priority") or "PRI-MEDIUM",
            "classification_confidence": classification.get("classification_confidence"),
            "classification_rationale": classification.get("classification_rationale"),
            "requires_human_review": bool(classification.get("requires_human_review")),
            "threats": _decoded(evidence.get("proposed_threats_json"), []),
            "platforms": _decoded(evidence.get("proposed_platforms_json"), []),
            "mappings": _decoded(evidence.get("proposed_mappings_json"), []),
            "tags": _decoded(evidence.get("proposed_tags_json"), []),
            "relationships": _decoded(evidence.get("proposed_relationships_json"), []),
            "actions": _decoded(evidence.get("proposed_actions_json"), []),
            "external_references": [
                *(classification.get("external_references") or []),
                *external_references(full_text),
            ],
            "legacy_provenance": _decoded(next((
                value for key, value in evidence.items()
                if key.startswith("proposed_") and key.endswith("_provenance_json")
            ), None), None) or {
                "legacy_id": original.get("id") or raw.get("raw_artifact_id"),
                "legacy_domain": original.get("domain"), "legacy_sub": original.get("sub_domain"),
                "assets": original.get("asset_ids") or [],
            },
        }
        provenance = candidates[candidate_id]["legacy_provenance"]
        if "legacy_id" not in provenance:
            def legacy_value(suffix: str) -> Any:
                return next(
                    (value for key, value in provenance.items() if key.endswith(f"_{suffix}")),
                    None,
                )
            provenance = {
                "legacy_id": legacy_value("id"),
                "legacy_domain": legacy_value("domain"),
                "legacy_sub": legacy_value("sub"),
                "assets": provenance.get("assets") or [],
            }
            candidates[candidate_id]["legacy_provenance"] = provenance
    correction_envelope = json.loads(Path(text_corrections).read_text(encoding="utf-8"))
    if correction_envelope.get("schema_version") != 1:
        raise CurationInputError("unsupported catalog text-correction schema")
    for candidate_id, correction in correction_envelope.get("corrections", {}).items():
        if candidate_id not in candidates:
            raise CurationInputError(f"text correction references unknown candidate {candidate_id}")
        for field in ("title_en", "definition_short_en"):
            if correction.get(field):
                candidates[candidate_id][field] = correction[field]
        candidates[candidate_id]["classification_rationale"] = (
            candidates[candidate_id].get("classification_rationale", "")
            + " Canonical text correction: " + str(correction.get("reason") or "governed correction")
        ).strip()
    if len(candidates) != 1467:
        raise CurationInputError(f"expected 1467 curation candidates, found {len(candidates)}")
    return candidates


def _candidate_issues(candidate: dict[str, Any]) -> list[str]:
    core = (
        "type", "title_en", "definition_short_en", "primary_domain", "sub_domain",
        "abstraction_level", "source_document", "obligation_level",
        "classification_rationale",
    )
    issues = [field for field in core if candidate.get(field) in (None, "")]
    type_fields = {
        "ART-REQ": ("requirement_type",),
        "ART-CTR": ("control_nature", "control_function", "testability"),
        "ART-CTE": ("control_nature", "control_function", "testability"),
        "ART-AST": ("asset_type", "asset_criticality"),
    }
    issues.extend(
        field for field in type_fields.get(candidate.get("type"), ())
        if candidate.get(field) in (None, "")
    )
    if candidate.get("sub_domain") and not candidate["sub_domain"].startswith(candidate.get("primary_domain", "") + "."):
        issues.append("domain_membership")
    return sorted(set(issues))


def build_projection(
    candidates: dict[str, dict[str, Any]],
    equivalence_path: str | Path = DEFAULT_EQUIVALENCE,
) -> dict[str, Any]:
    groups = json.loads(Path(equivalence_path).read_text(encoding="utf-8"))
    member_group: dict[str, dict[str, Any]] = {}
    selected: set[str] = set(candidates)
    overrides: list[dict[str, Any]] = []
    for group in groups:
        members = group["members"]
        if any(member not in candidates for member in members):
            raise CurationInputError(f"equivalence group {group['id']} references a missing candidate")
        if any(member in member_group for member in members):
            raise CurationInputError(f"candidate appears in multiple equivalence groups: {group['id']}")
        for member in members:
            member_group[member] = group
            selected.discard(member)
        chosen = group["canonical"]
        if _candidate_issues(candidates[chosen]):
            alternatives = [member for member in members if not _candidate_issues(candidates[member])]
            if not alternatives:
                raise CurationInputError(f"equivalence group {group['id']} has no minimum-valid candidate")
            chosen = sorted(alternatives)[0]
            overrides.append({
                "groupId": group["id"], "declaredCanonical": group["canonical"],
                "selectedCanonical": chosen,
                "reason": "Declared canonical lacks type-required minimum fields; selected a structurally valid equivalent member.",
            })
        group["selected_canonical"] = chosen
        selected.add(chosen)
    raw_to_candidate: dict[str, str] = {}
    for candidate_id, candidate in candidates.items():
        group = member_group.get(candidate_id)
        chosen = group["selected_canonical"] if group else candidate_id
        raw_to_candidate[candidate["raw_id"]] = chosen
    return {
        "groups": groups, "selected": sorted(selected),
        "rawToCandidate": raw_to_candidate, "selectionOverrides": overrides,
        "equivalenceSha256": file_hash(equivalence_path),
    }


def final_artifact_id(candidate: dict[str, Any]) -> str:
    number = candidate["candidate_id"].rsplit("-", 1)[1]
    return f"SG-{candidate['type'][4:]}-{candidate['source_key']}-{number}"


def _source_fields(candidate: dict[str, Any]) -> tuple[str, str]:
    raw_type = (candidate.get("source_type_raw") or "").upper()
    source_type = {
        "STANDARD": "STANDARD", "REGULATION": "REGULATION", "SYSTEM": "SYSTEM",
        "TOOL": "TOOL", "INTERVIEW": "INTERVIEW", "OBSERVATION": "OBSERVATION",
    }.get(raw_type, "DOCUMENT")
    source = {
        "REGULATION": "SRC-REG", "STANDARD": "SRC-STD",
        "GUIDELINE": "SRC-BST", "POLICY_TEMPLATE": "SRC-BST",
    }.get(raw_type, "SRC-INT")
    return source, source_type


def _granularity(artifact_type: str) -> str:
    return {
        "ART-CFG": "GRN-TECHNICAL", "ART-RUL": "GRN-EXECUTABLE",
        "ART-EVD": "GRN-EVIDENTIARY", "ART-MET": "GRN-METRIC",
        "ART-TSK": "GRN-DETAILED",
    }.get(artifact_type, "GRN-MEDIUM")


def _insert_candidate(conn: sqlite3.Connection, candidate: dict[str, Any], group: dict[str, Any] | None) -> str:
    artifact_id = final_artifact_id(candidate)
    source, source_type = _source_fields(candidate)
    confidence = candidate.get("classification_confidence")
    rationale = (candidate.get("classification_rationale") or "").strip()
    if confidence is None:
        confidence = 0.0
        rationale += (
            " CONFIDENCE_UNASSESSED: no numeric confidence was recorded in the "
            "pinned evidence; 0.0 is an explicit unknown sentinel and human review "
            "is required."
        )
    requires_review = bool(candidate.get("requires_human_review")) or confidence <= 0.70 or bool(group)
    priority = candidate.get("priority") or "PRI-MEDIUM"
    weight = {"PRI-CRITICAL": 10, "PRI-HIGH": 7, "PRI-MEDIUM": 4, "PRI-LOW": 1}[priority]
    values = {
        "id": artifact_id, "source_catalog_id": candidate["source_catalog_id"],
        "source_artifact_id": candidate.get("external_raw_id"),
        "type": candidate["type"], "title_en": candidate["title_en"],
        "description_en": candidate["definition_short_en"],
        "definition_short_en": candidate["definition_short_en"],
        "definition_full_en": candidate.get("definition_full_en"),
        "primary_domain": candidate["primary_domain"], "sub_domain": candidate["sub_domain"],
        "abstraction_level": candidate["abstraction_level"], "source": source,
        "source_type": source_type, "source_location": candidate.get("source_section"),
        "obligation_level": candidate["obligation_level"],
        "requirement_type": candidate.get("requirement_type"),
        "granularity_level": _granularity(candidate["type"]),
        "control_nature": candidate.get("control_nature"),
        "control_function": candidate.get("control_function"),
        "testability": candidate.get("testability"),
        "priority": priority, "priority_weight": weight, "review_frequency": "AD-HOC",
        "asset_type": candidate.get("asset_type"), "asset_criticality": candidate.get("asset_criticality"),
        "classification_confidence": confidence, "classification_rationale": rationale,
        "ai_review_status": "AIR-HUMAN-REVIEW" if requires_review else "AIR-AUTO-ACCEPTED",
        "requires_human_review": int(requires_review), "publication_status": "APPROVED",
        "import_status": "MERGED" if group else "IMPORTED",
        "import_source": "secureguide.catalog_curation", "import_version": "1",
        "source_document": candidate["source_document"],
        "source_section": candidate.get("source_section"), "is_active": 1,
    }
    columns = list(values)
    updates = [column for column in columns if column != "id"]
    conn.execute(
        f"INSERT INTO security_artifacts({','.join(columns)}) VALUES({','.join('?' for _ in columns)}) "
        f"ON CONFLICT(id) DO UPDATE SET " + ",".join(f"{column}=excluded.{column}" for column in updates),
        tuple(values[column] for column in columns),
    )
    return artifact_id


def _legacy_lineage(conn: sqlite3.Connection) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for row in conn.execute(
        """SELECT promoted_artifact_id,proposed_mappings_json
             FROM staging_artifacts WHERE promoted_artifact_id IS NOT NULL"""
    ):
        result[row[0]] = _decoded(row[1], [])
    return result


def close_existing_catalog(conn: sqlite3.Connection) -> dict[str, int]:
    """Backfill normalized lineage and explicit dispositions for existing canonicals."""
    legacy = _legacy_lineage(conn)
    linked: set[str] = set()
    try:
        conn.execute("BEGIN IMMEDIATE")
        for artifact_id, mappings in legacy.items():
            for index, mapping in enumerate(mappings):
                raw_id = mapping.get("raw_id")
                if not raw_id or not conn.execute(
                    "SELECT 1 FROM raw_artifacts WHERE id=?", (raw_id,)
                ).fetchone():
                    continue
                strength = mapping.get("mapping_strength") or "DIRECT"
                rationale = mapping.get("rationale")
                if strength != "DIRECT" and not rationale:
                    rationale = "Legacy non-direct mapping retained during normalized lineage backfill."
                conn.execute(
                    """INSERT OR IGNORE INTO artifact_source_lineage(
                           artifact_id,raw_artifact_id,lineage_role,mapping_strength,
                           rationale,is_primary
                       ) VALUES(?,?,'SUPPORTS_CANONICAL',?,?,?)""",
                    (artifact_id, raw_id, strength, rationale, int(index == 0)),
                )
                conn.execute(
                    "UPDATE raw_artifacts SET promoted_artifact_id=? WHERE id=?",
                    (artifact_id, raw_id),
                )
                linked.add(raw_id)
        for row in conn.execute("SELECT id FROM raw_artifacts ORDER BY id"):
            raw_id = row[0]
            disposition = "SUPPORTS_CANONICAL" if raw_id in linked else "DEFERRED"
            rationale = (
                "Supports an existing governed canonical artifact."
                if raw_id in linked else
                "No existing governed canonical lineage selects this raw source record."
            )
            conn.execute(
                """INSERT OR IGNORE INTO raw_artifact_dispositions(
                       raw_artifact_id,disposition,rationale,decision_method,
                       decision_confidence,requires_human_review,decided_by,decision_batch_id
                   ) VALUES(?,?,?,?,?,?,?,?)""",
                (raw_id, disposition, rationale, "LEGACY_LINEAGE_BACKFILL",
                 1.0 if raw_id in linked else 0.0, 0 if raw_id in linked else 1,
                 "SecureGuide release builder", "LEGACY-CLOSURE-V1"),
            )
        conn.execute("COMMIT")
    except Exception:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    return {
        "rawTotal": conn.execute("SELECT COUNT(*) FROM raw_artifacts").fetchone()[0],
        "linkedRaw": len(linked),
        "dispositions": conn.execute("SELECT COUNT(*) FROM raw_artifact_dispositions").fetchone()[0],
        "canonicalsWithLineage": conn.execute("SELECT COUNT(DISTINCT artifact_id) FROM artifact_source_lineage").fetchone()[0],
    }


def curate_complete_catalog(
    conn: sqlite3.Connection,
    candidates: dict[str, dict[str, Any]] | None = None,
    equivalence_path: str | Path = DEFAULT_EQUIVALENCE,
) -> dict[str, Any]:
    """Curate the complete tracked corpus transactionally and close every raw row."""

    conn.row_factory = sqlite3.Row
    candidates = candidates or load_curation_candidates()
    projection = build_projection(candidates, equivalence_path)
    selected_set = set(projection["selected"])
    group_by_selected = {
        group["selected_canonical"]: group for group in projection["groups"]
    }
    candidate_to_final: dict[str, str] = {}
    try:
        conn.execute("BEGIN IMMEDIATE")
        for candidate_id in sorted(selected_set):
            candidate = candidates[candidate_id]
            issues = _candidate_issues(candidate)
            if issues:
                raise CurationInputError(f"selected candidate {candidate_id} is incomplete: {issues}")
            candidate_to_final[candidate_id] = _insert_candidate(
                conn, candidate, group_by_selected.get(candidate_id)
            )

        legacy = _legacy_lineage(conn)
        raw_to_final = {
            raw_id: candidate_to_final[candidate_id]
            for raw_id, candidate_id in projection["rawToCandidate"].items()
        }
        aliases_written: set[str] = set()

        def write_alias(old_id: str | None, target_id: str, reason: str) -> None:
            if not old_id or old_id == target_id:
                return
            conn.execute(
                """INSERT INTO catalog_artifact_id_aliases(
                       old_artifact_id,artifact_id,reason
                   ) VALUES(?,?,?)
                   ON CONFLICT(old_artifact_id) DO UPDATE SET
                     artifact_id=excluded.artifact_id,reason=excluded.reason""",
                (old_id, target_id, reason),
            )
            aliases_written.add(old_id)

        for candidate in candidates.values():
            selected_candidate = projection["rawToCandidate"][candidate["raw_id"]]
            target_id = candidate_to_final[selected_candidate]
            write_alias(
                candidate.get("legacy_artifact_id"),
                target_id,
                "Forward neutral-identity migration from the historical canonical ID.",
            )
            write_alias(
                final_artifact_id(candidate),
                target_id,
                "Forward canonical migration for an artifact consolidated by global equivalence.",
            )
        alias_count = len(aliases_written)
        for artifact_id, mappings in legacy.items():
            for mapping in mappings:
                raw_id = mapping.get("raw_id")
                if raw_id:
                    raw_to_final.setdefault(raw_id, artifact_id)

        raw_ids = {row[0] for row in conn.execute("SELECT id FROM raw_artifacts")}
        missing_candidate_raw = sorted(set(raw_to_final) - raw_ids)
        if missing_candidate_raw:
            raise CurationInputError(f"projection references missing raw rows: {missing_candidate_raw[:3]}")

        primary_raw_by_artifact = {
            candidate_to_final[candidate_id]: candidates[candidate_id]["raw_id"]
            for candidate_id in selected_set
        }
        for artifact_id, mappings in legacy.items():
            if mappings:
                primary_raw_by_artifact.setdefault(artifact_id, mappings[0].get("raw_id"))

        for raw_id in sorted(raw_ids):
            artifact_id = raw_to_final.get(raw_id)
            if artifact_id:
                is_primary = int(primary_raw_by_artifact.get(artifact_id) == raw_id)
                conn.execute(
                    """INSERT OR IGNORE INTO artifact_source_lineage(
                           artifact_id,raw_artifact_id,lineage_role,mapping_strength,
                           rationale,is_primary
                       ) VALUES(?,?,'SUPPORTS_CANONICAL','DIRECT',?,?)""",
                    (artifact_id, raw_id, "Deterministic global reconciliation.", is_primary),
                )
                disposition, rationale = (
                    "SUPPORTS_CANONICAL", f"Supports canonical artifact {artifact_id}."
                )
                conn.execute(
                    "UPDATE raw_artifacts SET promoted_artifact_id=? WHERE id=?",
                    (artifact_id, raw_id),
                )
            else:
                disposition, rationale = (
                    "DEFERRED",
                    "No defensible globally reconciled canonical was selected from the current tracked classification evidence.",
                )
            conn.execute(
                """INSERT INTO raw_artifact_dispositions(
                       raw_artifact_id,disposition,rationale,decision_method,
                       decision_confidence,requires_human_review,decided_by,decision_batch_id
                   ) VALUES(?,?,?,?,?,?,?,?)
                   ON CONFLICT(raw_artifact_id) DO UPDATE SET
                     disposition=excluded.disposition,rationale=excluded.rationale,
                     decision_method=excluded.decision_method,
                     decision_confidence=excluded.decision_confidence,
                     requires_human_review=excluded.requires_human_review,
                     decided_by=excluded.decided_by,decision_batch_id=excluded.decision_batch_id""",
                (raw_id, disposition, rationale, "DETERMINISTIC_GLOBAL_RECONCILIATION",
                 1.0 if artifact_id else 0.0, 0 if artifact_id else 1,
                 "SecureGuide curation pipeline", "COMPLETE-CATALOG-V1"),
            )

        valid_threats = {row[0] for row in conn.execute("SELECT code FROM lk_threat")}
        valid_platforms = {row[0] for row in conn.execute("SELECT code FROM lk_platform")}
        valid_aliases = {row[0] for row in conn.execute("SELECT legacy_key FROM legacy_domain_alias")}
        mapping_count = action_count = tag_count = relationship_count = external_reference_count = 0
        for candidate_id, artifact_id in candidate_to_final.items():
            candidate = candidates[candidate_id]
            seen_mappings: set[tuple[str, str, str]] = set()
            for mapping in candidate.get("mappings") or []:
                framework = mapping.get("source_document") or mapping.get("framework")
                version = mapping.get("source_version") or mapping.get("version") or "UNKNOWN"
                reference = mapping.get("source_section") or mapping.get("reference")
                strength = mapping.get("mapping_strength") or "INFORMATIVE"
                rationale = mapping.get("rationale")
                if not framework or not reference or strength not in {"DIRECT", "INDIRECT", "PARTIAL", "INFORMATIVE"}:
                    raise CurationInputError(f"invalid framework mapping on {candidate_id}")
                if strength != "DIRECT" and not (rationale or "").strip():
                    raise CurationInputError(f"non-direct framework mapping lacks rationale on {candidate_id}")
                signature = (framework, version, reference)
                if signature in seen_mappings:
                    continue
                seen_mappings.add(signature)
                conn.execute(
                    """INSERT INTO framework_mappings(
                           artifact_id,framework,version,reference,mapping_strength,rationale
                       ) VALUES(?,?,?,?,?,?)""",
                    (artifact_id, framework, version, reference, strength, rationale),
                )
                mapping_count += 1
            seen_actions: set[tuple[str, int]] = set()
            for action in candidate.get("actions") or []:
                kind = action.get("kind") or "ACTION"
                sequence = action.get("seq")
                text_en = action.get("text_en")
                if kind not in {"ACTION", "VERIFICATION"} or not isinstance(sequence, int) or sequence < 0 or not text_en:
                    raise CurationInputError(f"invalid action on {candidate_id}")
                signature = (kind, sequence)
                if signature in seen_actions:
                    continue
                seen_actions.add(signature)
                conn.execute(
                    """INSERT INTO artifact_actions(
                           artifact_id,kind,seq,text_en,text_ar
                       ) VALUES(?,?,?,?,?)""",
                    (artifact_id, kind, sequence, text_en, action.get("text_ar")),
                )
                action_count += 1
            for tag in candidate.get("tags") or []:
                tag_type, tag_value = tag.get("tag_type"), tag.get("tag_value")
                if tag_type not in {"Technology", "Framework", "Concept", "Context", "Threat", "Data", "Party"} or not tag_value:
                    raise CurationInputError(f"invalid normalized tag on {candidate_id}")
                conn.execute(
                    "INSERT OR IGNORE INTO artifact_tags(artifact_id,tag_type,tag_value) VALUES(?,?,?)",
                    (artifact_id, tag_type, tag_value),
                )
                tag_count += 1
            seen_external_references: set[tuple[str, str | None]] = set()
            for reference in candidate.get("external_references") or []:
                if reference.get("type") not in {"STANDARD", "GUIDE", "ARTICLE", "TOOL", "OTHER"} or not reference.get("title"):
                    raise CurationInputError(f"invalid external reference on {candidate_id}")
                signature = (str(reference["title"]), reference.get("url"))
                if signature in seen_external_references:
                    continue
                seen_external_references.add(signature)
                conn.execute(
                    """INSERT INTO external_references(
                           artifact_id,type,title,url,description
                       ) VALUES(?,?,?,?,?)""",
                    (artifact_id, reference["type"], reference["title"],
                     reference.get("url"), reference.get("description")),
                )
                external_reference_count += 1
            # Only final canonical IDs may be persisted as relationship targets.
            for relationship in candidate.get("relationships") or []:
                target_candidate = relationship.get("target_id")
                target_id = candidate_to_final.get(target_candidate, target_candidate)
                relation_type = relationship.get("relation_type")
                if target_id not in candidate_to_final.values() or relation_type not in {
                    "REL-DER", "REL-SAT", "REL-SUP", "REL-SPL", "REL-IMP", "REL-VER",
                    "REL-MEA", "REL-MIT", "REL-AFF", "REL-EXC", "REL-DEP", "REL-CNF",
                }:
                    raise CurationInputError(f"dangling or invalid relationship on {candidate_id}")
                if relation_type == "REL-CNF" and not (
                    relationship.get("resolution_status") and relationship.get("resolution_note")
                ):
                    raise CurationInputError(f"unresolved conflict relationship on {candidate_id}")
                conn.execute(
                    """INSERT INTO artifact_relationships(
                           source_id,target_id,relation_type,resolution_status,resolution_note
                       ) VALUES(?,?,?,?,?)""",
                    (artifact_id, target_id, relation_type,
                     relationship.get("resolution_status"), relationship.get("resolution_note")),
                )
                relationship_count += 1
            threats = []
            for threat in candidate.get("threats") or []:
                code = threat.get("threat_code") if isinstance(threat, dict) else threat
                if code in valid_threats:
                    threats.append(code)
            for code in sorted(set(threats or ["THR-NA"])):
                conn.execute(
                    "INSERT OR IGNORE INTO artifact_threats(artifact_id,threat_code) VALUES(?,?)",
                    (artifact_id, code),
                )
            for platform in candidate.get("platforms") or []:
                code = platform.get("platform_code") if isinstance(platform, dict) else platform
                if code in valid_platforms:
                    conn.execute(
                        "INSERT OR IGNORE INTO artifact_platforms(artifact_id,platform_code) VALUES(?,?)",
                        (artifact_id, code),
                    )
            provenance = candidate.get("legacy_provenance")
            if provenance and provenance.get("legacy_id") and provenance.get("legacy_domain") in valid_aliases:
                conn.execute(
                    """INSERT INTO catalog_legacy_provenance(
                           artifact_id,legacy_id,legacy_domain,legacy_sub
                       ) VALUES(?,?,?,?) ON CONFLICT(artifact_id) DO UPDATE SET
                         legacy_id=excluded.legacy_id,legacy_domain=excluded.legacy_domain,
                         legacy_sub=excluded.legacy_sub""",
                    (artifact_id, provenance["legacy_id"], provenance["legacy_domain"], provenance.get("legacy_sub")),
                )
                for asset in sorted(set(provenance.get("assets") or [])):
                    conn.execute(
                        "INSERT OR IGNORE INTO catalog_legacy_assets(artifact_id,asset_ref) VALUES(?,?)",
                        (artifact_id, asset),
                    )
            if candidate["type"] == "ART-RSK":
                conn.execute(
                    """INSERT OR IGNORE INTO remediation_actions(
                           artifact_id,action,priority,responsible_role
                       ) VALUES(?,?,'PRI-HIGH','Risk owner')""",
                    (artifact_id, "Define and execute a documented treatment that mitigates the described risk and verify its effectiveness."),
                )
        conn.execute("COMMIT")
    except Exception:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise

    domains = {
        row[0]: int(row[1]) for row in conn.execute(
            "SELECT primary_domain,COUNT(*) FROM security_artifacts WHERE is_active=1 GROUP BY primary_domain ORDER BY primary_domain"
        )
    }
    dispositions = {
        row[0]: int(row[1]) for row in conn.execute(
            "SELECT disposition,COUNT(*) FROM raw_artifact_dispositions GROUP BY disposition ORDER BY disposition"
        )
    }
    return {
        "candidateCount": len(candidates), "equivalenceGroupCount": len(projection["groups"]),
        "selectedProjectionCount": len(selected_set),
        "canonicalTotal": conn.execute("SELECT COUNT(*) FROM security_artifacts").fetchone()[0],
        "rawTotal": conn.execute("SELECT COUNT(*) FROM raw_artifacts").fetchone()[0],
        "lineageRows": conn.execute("SELECT COUNT(*) FROM artifact_source_lineage").fetchone()[0],
        "normalized": {
            "frameworkMappings": mapping_count,
            "actions": action_count,
            "tags": tag_count,
            "relationships": relationship_count,
            "externalReferences": external_reference_count,
            "artifactIdAliases": alias_count,
        },
        "dispositions": dispositions, "domains": domains,
        "selectionOverrides": projection["selectionOverrides"],
        "equivalenceSha256": projection["equivalenceSha256"],
    }


def prepare_curation_database(
    base_database: str | Path, output_database: str | Path,
    catalogs_dir: str | Path = ROOT / "SecureGuide_Mobile_Docs" / "Raw_Catalogs",
) -> Path:
    """Create a working candidate from the governed base and all pinned raw files."""
    base_database = Path(base_database).resolve()
    output_database = Path(output_database).resolve()
    release_asset = (ROOT / "mobile" / "assets" / "catalog.db").resolve()
    if output_database == release_asset:
        raise CurationInputError("curation output cannot be the production mobile asset")
    output_database.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_database.with_suffix(output_database.suffix + ".tmp")
    if temporary.exists():
        temporary.unlink()
    shutil.copyfile(base_database, temporary)
    try:
        apply_migrations(temporary)
        from scripts.ingest_raw import ingest_file
        conn = sqlite3.connect(temporary)
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            stats = {"files": [], "inserted": 0, "updated": 0, "unchanged": 0}
            for source in sorted(Path(catalogs_dir).glob("*.json")):
                ingest_file(conn, str(source), stats)
            conn.commit()
        finally:
            conn.close()
        temporary.replace(output_database)
    except Exception:
        if temporary.exists():
            temporary.unlink()
        raise
    return output_database
