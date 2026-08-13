"""Deterministic catalog curation primitives.

The module deliberately separates mechanical provenance backfill from later
canonical selection.  It never invents a version, license, or rights grant.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

import yaml

from secureguide.catalog_validation import canonical_hash, file_hash


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE_MANIFEST = ROOT / "config" / "source_manifest.json"
DEFAULT_SOURCE_RIGHTS = ROOT / "config" / "source_rights.yaml"


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
