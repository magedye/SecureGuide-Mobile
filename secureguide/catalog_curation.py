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


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE_MANIFEST = ROOT / "config" / "source_manifest.json"
DEFAULT_SOURCE_RIGHTS = ROOT / "config" / "source_rights.yaml"
DEFAULT_EQUIVALENCE = ROOT / "consolidation" / "unified" / "equivalence.json"
DEFAULT_CURATED_CLASSIFICATIONS = ROOT / "consolidation" / "curated" / "classifications.json"
DEFAULT_CURATED_RAW = ROOT / "SecureGuide_Mobile_Docs" / "Raw_Catalogs" / "securekit_curated_controls.json"
DEFAULT_AMANI_RAW = ROOT / "SecureGuide_Mobile_Docs" / "Raw_Catalogs" / "amani_v4_recovered.json"


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
    amani_raw: str | Path = DEFAULT_AMANI_RAW,
) -> dict[str, dict[str, Any]]:
    """Load the tracked 761 curated and 706 recovered amani candidates."""

    classified = json.loads(Path(curated_classifications).read_text(encoding="utf-8"))
    curated_envelope = json.loads(Path(curated_raw).read_text(encoding="utf-8"))
    amani_envelope = json.loads(Path(amani_raw).read_text(encoding="utf-8"))
    if len(classified) != len(curated_envelope["artifacts"]):
        raise CurationInputError("curated classifications do not cover the curated raw source")
    candidates: dict[str, dict[str, Any]] = {}
    for index, (classification, raw) in enumerate(zip(classified, curated_envelope["artifacts"])):
        raw_id = f"securekit_curated_controls::{index:04d}"
        if classification["raw_id"] != raw_id:
            raise CurationInputError(f"curated classification order mismatch at {raw_id}")
        source = raw.get("source_metadata") or {}
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
            "definition_full_en": (raw.get("original_content") or {}).get("raw_text_en"),
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
            "actions": [], "amani_provenance": None,
        }

    for index, raw in enumerate(amani_envelope["artifacts"]):
        recovery = raw.get("recovery_provenance") or {}
        evidence = recovery.get("staging_evidence") or {}
        candidate_id = f"STG-AMANI-{index:04d}"
        if recovery.get("staging_id") != candidate_id:
            raise CurationInputError(f"amani staging evidence mismatch at {candidate_id}")
        source = raw.get("source_metadata") or {}
        original = recovery.get("original_raw_record") or {}
        candidates[candidate_id] = {
            "candidate_id": candidate_id, "source_key": "AMANI",
            "raw_id": f"amani_v4::{index:04d}",
            "external_raw_id": raw.get("raw_artifact_id"),
            "source_catalog_id": "amani_v4",
            "source_document": source.get("source_document") or "amani SecureGuide v4",
            "source_type_raw": source.get("source_type") or "GUIDELINE",
            "source_version": source.get("source_version") or "4.1.0",
            "source_section": source.get("source_section"),
            "title_en": evidence.get("title_en") or (raw.get("extracted_elements") or {}).get("title_draft"),
            "definition_short_en": evidence.get("definition_short_en") or (raw.get("extracted_elements") or {}).get("description_draft"),
            "definition_full_en": evidence.get("definition_full_en") or (raw.get("original_content") or {}).get("raw_text_en"),
            "type": evidence.get("proposed_type"),
            "abstraction_level": evidence.get("proposed_abstraction_level"),
            "primary_domain": evidence.get("proposed_primary_domain"),
            "sub_domain": evidence.get("proposed_sub_domain"),
            "obligation_level": evidence.get("proposed_obligation_level"),
            "requirement_type": evidence.get("proposed_requirement_type"),
            "control_nature": evidence.get("proposed_control_nature"),
            "control_function": evidence.get("proposed_control_function"),
            "testability": evidence.get("proposed_testability"),
            "asset_type": evidence.get("proposed_asset_type"),
            "asset_criticality": evidence.get("proposed_asset_criticality"),
            "priority": evidence.get("proposed_priority") or "PRI-MEDIUM",
            "classification_confidence": evidence.get("classification_confidence"),
            "classification_rationale": evidence.get("classification_rationale"),
            "requires_human_review": bool(evidence.get("requires_human_review")),
            "threats": _decoded(evidence.get("proposed_threats_json"), []),
            "platforms": _decoded(evidence.get("proposed_platforms_json"), []),
            "mappings": _decoded(evidence.get("proposed_mappings_json"), []),
            "tags": _decoded(evidence.get("proposed_tags_json"), []),
            "relationships": _decoded(evidence.get("proposed_relationships_json"), []),
            "actions": _decoded(evidence.get("proposed_actions_json"), []),
            "amani_provenance": _decoded(evidence.get("proposed_amani_provenance_json"), None) or {
                "amani_id": original.get("id") or raw.get("raw_artifact_id"),
                "amani_domain": original.get("domain"), "amani_sub": original.get("sub_domain"),
                "assets": original.get("asset_ids") or [],
            },
        }
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
        rationale += " No numeric confidence was recorded in the curated evidence; a conservative 0.0 is stored and human review is required."
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
        valid_aliases = {row[0] for row in conn.execute("SELECT amani_key FROM amani_domain_alias")}
        for candidate_id, artifact_id in candidate_to_final.items():
            candidate = candidates[candidate_id]
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
            provenance = candidate.get("amani_provenance")
            if provenance and provenance.get("amani_id") and provenance.get("amani_domain") in valid_aliases:
                conn.execute(
                    """INSERT INTO catalog_amani_provenance(
                           artifact_id,amani_id,amani_domain,amani_sub
                       ) VALUES(?,?,?,?) ON CONFLICT(artifact_id) DO UPDATE SET
                         amani_id=excluded.amani_id,amani_domain=excluded.amani_domain,
                         amani_sub=excluded.amani_sub""",
                    (artifact_id, provenance["amani_id"], provenance["amani_domain"], provenance.get("amani_sub")),
                )
                for asset in sorted(set(provenance.get("assets") or [])):
                    conn.execute(
                        "INSERT OR IGNORE INTO catalog_amani_assets(artifact_id,asset_ref) VALUES(?,?)",
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
