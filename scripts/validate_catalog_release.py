"""Validate an exact SecureGuide release candidate through V1-V4 gates."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.build_release_db import _canonical_manifest_hash
from scripts.rebuild_unified_equivalence import rebuild
from scripts.validate_catalog_identity import audit_database, scan as scan_identity
from secureguide.catalog_validation import (
    file_hash,
    load_contract,
    validate_catalog,
)
from secureguide.catalog_workbook import catalog_state_hash
from secureguide.database import connect


def _count(conn: sqlite3.Connection, sql: str) -> int:
    return int(conn.execute(sql).fetchone()[0])


def validate_release(
    database: Path,
    *,
    manifest_path: Path | None = None,
    comparison_database: Path | None = None,
) -> dict[str, Any]:
    database = database.resolve()
    manifest_path = (manifest_path or database.with_suffix(database.suffix + ".manifest.json")).resolve()
    contract = load_contract()
    catalog_validation = validate_catalog(database)
    conn = connect(database)
    started = time.perf_counter()
    try:
        integrity_started = time.perf_counter()
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        integrity_ms = round((time.perf_counter() - integrity_started) * 1000, 3)
        foreign_keys = len(conn.execute("PRAGMA foreign_key_check").fetchall())
        minimum = {
            "valid": catalog_validation["summary"]["minimumValid"]
            == catalog_validation["summary"]["canonicalTotal"],
            **catalog_validation["summary"],
        }
        strict = {
            "valid": catalog_validation["summary"]["strictConformant"]
            == catalog_validation["summary"]["canonicalTotal"],
            "strictConformant": catalog_validation["summary"]["strictConformant"],
        }
        closure = catalog_validation["closure"]

        source_count = _count(conn, "SELECT COUNT(*) FROM source_catalogs")
        manifest_count = _count(conn, "SELECT COUNT(*) FROM source_import_manifests")
        rights_count = _count(conn, "SELECT COUNT(*) FROM source_rights_versions WHERE is_current=1")
        raw_payload_count = _count(
            conn,
            """SELECT COUNT(*) FROM raw_artifacts
               WHERE raw_text_en IS NOT NULL OR raw_text_ar IS NOT NULL
                  OR (raw_json IS NOT NULL AND raw_json NOT IN ('','{}'))""",
        )
        dangling_mappings = _count(
            conn,
            """SELECT COUNT(*) FROM framework_mappings m
               LEFT JOIN security_artifacts a ON a.id=m.artifact_id WHERE a.id IS NULL""",
        )
        dangling_relationships = _count(
            conn,
            """SELECT COUNT(*) FROM artifact_relationships r
               LEFT JOIN security_artifacts s ON s.id=r.source_id
               LEFT JOIN security_artifacts t ON t.id=r.target_id
               WHERE s.id IS NULL OR t.id IS NULL""",
        )
        identity_audit = audit_database(database)
        active_identity_rows = len(identity_audit["ACTIVE_CURRENT"])

        query_started = time.perf_counter()
        for _ in range(50):
            conn.execute(
                """SELECT id,title_en,type,primary_domain FROM security_artifacts
                   WHERE is_active=1 AND title_en LIKE '%access%'
                   ORDER BY title_en,id LIMIT 25"""
            ).fetchall()
        query_ms = round((time.perf_counter() - query_started) * 1000 / 50, 3)
        logical_hash = catalog_state_hash(conn)
        type_distribution = dict(conn.execute(
            "SELECT type,COUNT(*) FROM security_artifacts GROUP BY type ORDER BY type"
        ))
        domain_distribution = dict(conn.execute(
            "SELECT primary_domain,COUNT(*) FROM security_artifacts GROUP BY primary_domain ORDER BY primary_domain"
        ))
    finally:
        conn.close()

    equivalence, equivalence_stats = rebuild(
        str(ROOT / "consolidation" / "unified" / "equivalence.json")
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_bindings = {
        "minimumContractSha256": file_hash(ROOT / "config" / "catalog_minimum_fields.yaml"),
        "sourceRightsSha256": file_hash(ROOT / "config" / "source_rights.yaml"),
        "curatedClassificationsSha256": file_hash(ROOT / "consolidation" / "curated" / "classifications.json"),
        "legacyClassificationsSha256": file_hash(ROOT / "consolidation" / "curated" / "legacy_classifications.json"),
        "equivalenceDecisionsSha256": file_hash(ROOT / "consolidation" / "unified" / "equivalence.json"),
        "catalogContentSha256": logical_hash,
    }
    binding_errors = {
        key: {"expected": value, "actual": manifest.get(key)}
        for key, value in expected_bindings.items()
        if manifest.get(key) != value
    }
    manifest_hash_valid = manifest.get("manifestSha256") == _canonical_manifest_hash(manifest)
    file_sha = file_hash(database)
    byte_reproducible = (
        comparison_database is not None
        and comparison_database.resolve().read_bytes() == database.read_bytes()
    )

    v1_valid = (
        integrity == "ok" and foreign_keys == 0 and minimum["valid"]
        and closure["valid"]
    )
    v2_valid = (
        source_count == manifest_count == rights_count
        and source_count > 0 and raw_payload_count == 0
    )
    v3_valid = (
        dangling_mappings == 0 and dangling_relationships == 0
        and active_identity_rows == 0
        and not scan_identity() and len(equivalence) == equivalence_stats["groups"]
        and len(type_distribution) > 1 and len(domain_distribution) == 8
    )
    v4_valid = (
        manifest.get("sha256") == file_sha
        and manifest.get("sizeBytes") == database.stat().st_size
        and manifest_hash_valid and not binding_errors and byte_reproducible
    )
    report = {
        "contract": "secureguide-catalog-release-validation-v1",
        "database": database.name,
        "sha256": file_sha,
        "schemaVersion": manifest.get("schemaVersion"),
        "V1": {"valid": v1_valid, "integrity": integrity, "foreignKeyViolations": foreign_keys,
               "minimum": minimum, "strict": strict, "closure": closure},
        "V2": {"valid": v2_valid, "sourceCatalogs": source_count,
               "sourceManifests": manifest_count, "currentRights": rights_count,
               "shippedRestrictedRawPayloads": raw_payload_count},
        "V3": {"valid": v3_valid, "danglingMappings": dangling_mappings,
               "danglingRelationships": dangling_relationships,
               "activeRetiredIdentityRows": active_identity_rows,
               "identityAudit": identity_audit,
               "equivalence": equivalence_stats, "typeDistribution": type_distribution,
               "domainDistribution": domain_distribution},
        "V4": {"valid": v4_valid, "manifestHashValid": manifest_hash_valid,
               "bindingErrors": binding_errors, "byteReproducible": byte_reproducible,
               "sizeBytes": database.stat().st_size},
        "performance": {"catalogQueryMeanMs": query_ms,
                        "integrityCheckMs": integrity_ms,
                        "totalValidationMs": round((time.perf_counter() - started) * 1000, 3)},
        "valid": v1_valid and v2_valid and v3_valid and v4_valid,
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--comparison-db", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = validate_release(
        args.db, manifest_path=args.manifest,
        comparison_database=args.comparison_db,
    )
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    raise SystemExit(0 if report["valid"] else 1)


if __name__ == "__main__":
    main()
