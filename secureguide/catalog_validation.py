"""Deterministic SecureGuide catalog validation and closure reporting."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import unicodedata
from pathlib import Path
from typing import Any, Iterable

from secureguide.database import connect


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONTRACT = ROOT / "config" / "catalog_minimum_fields.yaml"


def _normalize(value: Any) -> Any:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, dict):
        return {str(key): _normalize(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(
        _normalize(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def file_hash(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_contract(path: str | Path = DEFAULT_CONTRACT) -> dict[str, Any]:
    """Load the JSON-compatible YAML contract without an extra YAML runtime."""

    contract = json.loads(Path(path).read_text(encoding="utf-8"))
    if contract.get("schema_version") != 1:
        raise ValueError("unsupported minimum catalog contract schema")
    required = {
        "core_required",
        "type_required",
        "conditional_required",
        "raw_dispositions",
        "review_policy",
        "lineage_policy",
    }
    missing = sorted(required.difference(contract))
    if missing:
        raise ValueError(f"minimum catalog contract missing keys: {missing}")
    return contract


def _missing(row: sqlite3.Row, fields: Iterable[str]) -> list[str]:
    missing: list[str] = []
    for field in fields:
        value = row[field] if field in row.keys() else None
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append(field)
    return missing


def _has_risk_remediation(conn: sqlite3.Connection, artifact_id: str) -> bool:
    action = conn.execute(
        "SELECT 1 FROM remediation_actions WHERE artifact_id=? LIMIT 1", (artifact_id,)
    ).fetchone()
    mitigation = conn.execute(
        """SELECT 1 FROM artifact_relationships
             WHERE target_id=? AND relation_type='REL-MIT' LIMIT 1""",
        (artifact_id,),
    ).fetchone()
    return action is not None or mitigation is not None


def minimum_result(
    conn: sqlite3.Connection, row: sqlite3.Row, contract: dict[str, Any]
) -> dict[str, Any]:
    missing = _missing(row, contract["core_required"])
    # Some contract requirements are fulfilled by normalized child rows rather
    # than columns on security_artifacts (for example ART-RSK remediation).
    scalar_type_fields = [
        field
        for field in contract["type_required"].get(row["type"], [])
        if field in row.keys()
    ]
    missing.extend(_missing(row, scalar_type_fields))
    for rule in contract["conditional_required"]:
        if row["type"] in rule["types"] and all(
            row[key] == value for key, value in rule["when"].items()
        ):
            missing.extend(_missing(row, rule["fields"]))
    lineage_count = conn.execute(
        "SELECT COUNT(*) FROM artifact_source_lineage WHERE artifact_id=?", (row["id"],)
    ).fetchone()[0]
    if lineage_count < int(contract["lineage_policy"]["minimum_rows_per_canonical"]):
        missing.append("artifact_source_lineage")
    if row["type"] == "ART-RSK" and not _has_risk_remediation(conn, row["id"]):
        missing.append("risk_remediation")
    missing = sorted(set(missing))
    return {"valid": not missing, "missing": missing, "lineageRows": lineage_count}


def _lookup(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[0] for row in conn.execute(f"SELECT code FROM {table}")}


def _strict_errors(conn: sqlite3.Connection, row: sqlite3.Row) -> list[str]:
    errors: list[str] = []
    controlled = {
        "type": ("lk_artifact_type", row["type"]),
        "primary_domain": ("lk_sdt_domain", row["primary_domain"]),
        "sub_domain": ("lk_sdt_subdomain", row["sub_domain"]),
        "abstraction_level": ("lk_abstraction_level", row["abstraction_level"]),
        "source": ("lk_obligation_source", row["source"]),
        "source_type": ("lk_source_type", row["source_type"]),
        "obligation_level": ("lk_obligation_level", row["obligation_level"]),
        "granularity_level": ("lk_granularity_level", row["granularity_level"]),
        "priority": ("lk_priority", row["priority"]),
        "ai_review_status": ("lk_ai_review_status", row["ai_review_status"]),
    }
    tables = {
        item[0]
        for item in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    for field, (table, value) in controlled.items():
        if table in tables and value not in _lookup(conn, table):
            errors.append(f"USACM-VAL-001:{field}")
    if not row["sub_domain"].startswith(row["primary_domain"] + "."):
        errors.append("USACM-VAL-002")
    if row["type"] in ("ART-CTR", "ART-CTE"):
        if _missing(row, ("control_nature", "control_function", "testability")):
            errors.append("USACM-VAL-003")
    if row["type"] == "ART-REQ" and _missing(row, ("requirement_type",)):
        errors.append("USACM-VAL-004")
    if row["type"] == "ART-EXC" and _missing(
        row, ("exception_approval_date", "exception_expiry_date")
    ):
        errors.append("USACM-VAL-006")
    if row["type"] == "ART-AST" and _missing(
        row, ("asset_type", "asset_criticality")
    ):
        errors.append("USACM-VAL-007")
    if row["type"] == "ART-RSK" and not _has_risk_remediation(conn, row["id"]):
        errors.append("USACM-VAL-008")
    confidence = row["classification_confidence"]
    if confidence is not None and confidence <= 0.70 and not (
        row["requires_human_review"] == 1
        and row["ai_review_status"] == "AIR-HUMAN-REVIEW"
    ):
        errors.append("USACM-VAL-009")
    if confidence is not None and not (row["classification_rationale"] or "").strip():
        errors.append("USACM-VAL-010")
    conflicts = conn.execute(
        """SELECT COUNT(*) FROM artifact_relationships
             WHERE source_id=? AND relation_type='REL-CNF'
               AND (resolution_status IS NULL OR trim(COALESCE(resolution_note,''))='')""",
        (row["id"],),
    ).fetchone()[0]
    if conflicts:
        errors.append("USACM-VAL-012")
    mappings = conn.execute(
        """SELECT framework,version,reference,mapping_strength,rationale
             FROM framework_mappings WHERE artifact_id=?""",
        (row["id"],),
    ).fetchall()
    for mapping in mappings:
        if _missing(mapping, ("framework", "version", "reference", "mapping_strength")):
            errors.append("USACM-VAL-013")
        if mapping["mapping_strength"] != "DIRECT" and not (
            mapping["rationale"] or ""
        ).strip():
            errors.append("USACM-VAL-014")
    expected_weight = {
        "PRI-CRITICAL": 10,
        "PRI-HIGH": 7,
        "PRI-MEDIUM": 4,
        "PRI-LOW": 1,
    }.get(row["priority"])
    if expected_weight != row["priority_weight"]:
        errors.append("USACM-VAL-016")
    invalid_tags = conn.execute(
        """SELECT COUNT(*) FROM artifact_tags WHERE artifact_id=?
             AND tag_type NOT IN ('Technology','Framework','Concept','Context','Threat','Data','Party')""",
        (row["id"],),
    ).fetchone()[0]
    if invalid_tags:
        errors.append("USACM-VAL-017")
    if (
        row["type"] in ("ART-POL", "ART-STD", "ART-PRC")
        and row["publication_status"] == "PUBLISHED"
        and not row["effective_date"]
    ):
        errors.append("USACM-VAL-018")
    if row["review_frequency"] not in (None, "AD-HOC") and not row["next_review_date"]:
        errors.append("USACM-VAL-019")
    if any(
        value is not None and value < 0
        for value in (row["cost_estimate"], row["cost_estimate_min"], row["cost_estimate_max"])
    ) or (
        row["cost_estimate_min"] is not None
        and row["cost_estimate_max"] is not None
        and row["cost_estimate_max"] < row["cost_estimate_min"]
    ):
        errors.append("USACM-VAL-022")
    return sorted(set(errors))


def strict_result(conn: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
    errors = _strict_errors(conn, row)
    return {"valid": not errors, "errors": errors}


def _closure(conn: sqlite3.Connection, contract: dict[str, Any]) -> dict[str, Any]:
    def count(sql: str) -> int:
        return int(conn.execute(sql).fetchone()[0])

    raw_total = count("SELECT COUNT(*) FROM raw_artifacts")
    raw_disposed = count("SELECT COUNT(*) FROM raw_artifact_dispositions")
    canonical_total = count("SELECT COUNT(*) FROM security_artifacts")
    canonical_with_lineage = count(
        "SELECT COUNT(DISTINCT artifact_id) FROM artifact_source_lineage"
    )
    missing_dispositions = count(
        """SELECT COUNT(*) FROM raw_artifacts r WHERE NOT EXISTS(
               SELECT 1 FROM raw_artifact_dispositions d WHERE d.raw_artifact_id=r.id)"""
    )
    missing_canonical_lineage = count(
        """SELECT COUNT(*) FROM security_artifacts a WHERE NOT EXISTS(
               SELECT 1 FROM artifact_source_lineage l WHERE l.artifact_id=a.id)"""
    )
    supporting_without_lineage = count(
        """SELECT COUNT(*) FROM raw_artifact_dispositions d
             WHERE d.disposition IN ('SUPPORTS_CANONICAL','SPLIT') AND NOT EXISTS(
               SELECT 1 FROM artifact_source_lineage l
                WHERE l.raw_artifact_id=d.raw_artifact_id
                  AND l.lineage_role=d.disposition)"""
    )
    missing_manifests = count(
        "SELECT COUNT(*) FROM raw_artifacts WHERE source_manifest_id IS NULL"
    )
    missing_rights = count(
        """SELECT COUNT(*) FROM raw_artifacts r WHERE NOT EXISTS(
               SELECT 1 FROM source_rights_versions sr
                WHERE sr.source_catalog_id=r.source_catalog_id
                  AND sr.source_version=COALESCE(r.source_version,'UNKNOWN')
                  AND sr.is_current=1)"""
    )
    placeholders = ",".join("?" for _ in contract["raw_dispositions"])
    invalid_dispositions = int(
        conn.execute(
            f"SELECT COUNT(*) FROM raw_artifact_dispositions "
            f"WHERE disposition NOT IN ({placeholders})",
            tuple(contract["raw_dispositions"]),
        ).fetchone()[0]
    )
    issues = {
        "missingDispositions": missing_dispositions,
        "missingCanonicalLineage": missing_canonical_lineage,
        "supportingWithoutLineage": supporting_without_lineage,
        "missingSourceManifests": missing_manifests,
        "missingSourceRights": missing_rights,
        "invalidDispositions": invalid_dispositions,
    }
    return {
        "valid": all(value == 0 for value in issues.values()),
        "rawTotal": raw_total,
        "rawDisposed": raw_disposed,
        "canonicalTotal": canonical_total,
        "canonicalsWithLineage": canonical_with_lineage,
        **issues,
    }


def validate_catalog(
    database: str | Path, contract_path: str | Path = DEFAULT_CONTRACT
) -> dict[str, Any]:
    database = Path(database).resolve()
    contract_path = Path(contract_path).resolve()
    contract = load_contract(contract_path)
    conn = connect(database)
    try:
        artifacts: list[dict[str, Any]] = []
        for row in conn.execute("SELECT * FROM security_artifacts ORDER BY id"):
            artifacts.append(
                {
                    "id": row["id"],
                    "type": row["type"],
                    "primaryDomain": row["primary_domain"],
                    contract["result_names"]["minimum"]: minimum_result(conn, row, contract),
                    contract["result_names"]["strict"]: strict_result(conn, row),
                    "review": {
                        "aiReviewStatus": row["ai_review_status"],
                        "requiresHumanReview": bool(row["requires_human_review"]),
                    },
                }
            )
        closure = _closure(conn, contract)
        integrity_result = conn.execute("PRAGMA integrity_check").fetchone()[0]
        fk = conn.execute("PRAGMA foreign_key_check").fetchall()
        schema_version = conn.execute("PRAGMA user_version").fetchone()[0]
        if not schema_version:
            row = conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()
            schema_version = int(row[0]) if row and row[0] else 0
    finally:
        conn.close()
    minimum_name = contract["result_names"]["minimum"]
    strict_name = contract["result_names"]["strict"]
    report: dict[str, Any] = {
        "schemaVersion": schema_version,
        "databaseSha256": file_hash(database),
        "contract": {
            "id": contract["contract_id"],
            "version": contract["contract_version"],
            "sha256": file_hash(contract_path),
        },
        "artifacts": artifacts,
        "summary": {
            "canonicalTotal": len(artifacts),
            "minimumValid": sum(a[minimum_name]["valid"] for a in artifacts),
            "strictConformant": sum(a[strict_name]["valid"] for a in artifacts),
        },
        "reviewSummary": {
            "requiresHumanReview": sum(a["review"]["requiresHumanReview"] for a in artifacts),
            "notHumanApproved": sum(
                a["review"]["aiReviewStatus"] != "AIR-HUMAN-APPROVED" for a in artifacts
            ),
        },
        "closure": closure,
        "integrity": {
            "valid": integrity_result == "ok" and not fk,
            "integrityCheck": integrity_result,
            "foreignKeyViolations": len(fk),
        },
    }
    report["reportSha256"] = canonical_hash(report)
    return report
