"""Deterministic builder for governed SecureGuide databases.

One command, one reproducible artifact: apply every migration, seed the master
catalog, drive one full governance workflow, run integrity/FK/governance gates,
then emit the database next to a manifest and its SHA-256. The output is what
the standalone mobile application opens through its local SQLite runtime, so
UI work never waits on the real content-curation pipeline.

Modes:

* ``demo`` (default) — migrations + the shared test catalog + the governed
  demo workflow (2 profiles, selections, a template, an assessment, an approved
  blueprint, materialized tasks). Fully self-contained and runnable now.
* ``release`` — copy the checksum-pinned production catalog, apply every
  migration, install its reviewed template selection, and fail closed unless
  every shipped artifact has approved promotion and raw-source lineage.

Usage::

    python -m scripts.build_release_db --output dist/secureguide-demo.db
    python -m scripts.build_release_db --mode release --output mobile/assets/catalog.db
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from secureguide import Database, SecureGuideService, apply_migrations
from secureguide.catalog_curation import (
    backfill_source_provenance,
    close_existing_catalog,
    curate_complete_catalog,
    prepare_curation_database,
)
from secureguide.catalog_validation import (
    canonical_hash,
    file_hash,
    load_contract,
    minimum_result,
    strict_result,
)
from secureguide.catalog_workbook import catalog_state_hash
from secureguide.database import connect
from scripts.dump_read_model_contract import build_read_model_dataset
from tests.test_profile_workflow import seed_catalog

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RELEASE_SOURCE = ROOT / "catalog.db"
DEFAULT_RELEASE_CONFIG = ROOT / "consolidation" / "release_catalog.json"

# Governance views that must return zero rows in a healthy build.
GOVERNANCE_GATES = (
    "v_profile_evidence_integrity_issues",
    "v_profile_origin_governance_issues",
    "v_blueprint_governance_issues",
    "v_blueprint_enrichment_governance_issues",
)

COUNT_TABLES = (
    "security_artifacts",
    "staging_artifacts",
    "enterprise_profiles",
    "profile_artifacts",
    "profile_assessments",
    "profile_evidence",
    "profile_exceptions",
    "approved_blueprints",
    "profile_tasks",
    "templates",
)


class BuildError(RuntimeError):
    """A deterministic build failed a correctness gate."""


def _table_count(conn: sqlite3.Connection, table: str) -> int | None:
    try:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    except sqlite3.OperationalError:
        return None


def _schema_version(conn: sqlite3.Connection) -> str:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
    ).fetchone()
    if not row:
        return "unknown"
    version = conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0]
    return str(version)


def _run_gates(conn: sqlite3.Connection) -> None:
    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        raise BuildError(f"integrity_check failed: {integrity}")
    fk = conn.execute("PRAGMA foreign_key_check").fetchall()
    if fk:
        raise BuildError(f"foreign_key_check reported {len(fk)} violation(s)")
    for view in GOVERNANCE_GATES:
        try:
            rows = conn.execute(f"SELECT COUNT(*) FROM {view}").fetchone()[0]
        except sqlite3.OperationalError:
            continue  # view absent at this schema level
        if rows:
            raise BuildError(f"governance gate {view} reported {rows} issue(s)")


def _publication_breakdown(conn: sqlite3.Connection) -> dict[str, int]:
    try:
        rows = conn.execute(
            "SELECT publication_status,COUNT(*) FROM security_artifacts GROUP BY publication_status"
        ).fetchall()
    except sqlite3.OperationalError:
        return {}
    return {status: count for status, count in rows}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_release_configuration(path: Path) -> tuple[dict, dict]:
    if not path.is_file():
        raise BuildError(f"release configuration not found: {path}")
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("schema_version") != 1:
        raise BuildError("unsupported release configuration schema")
    baseline_path = path.parent / str(config.get("source_baseline", ""))
    if not baseline_path.is_file():
        raise BuildError(f"release source baseline not found: {baseline_path}")
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    return config, baseline


def _validate_release_source(source: Path, baseline: dict) -> None:
    if not source.is_file():
        raise BuildError(f"release source database not found: {source}")
    expected_name = baseline.get("database")
    if expected_name and source.name != expected_name:
        raise BuildError(
            f"release source must be the governed {expected_name}, got {source.name}"
        )
    expected_hash = str(baseline.get("sha256", "")).lower()
    actual_hash = _sha256(source)
    if not expected_hash or actual_hash != expected_hash:
        raise BuildError(
            "release source checksum does not match the reviewed production baseline"
        )


def _install_release_templates(conn: sqlite3.Connection, config: dict) -> None:
    templates = config.get("templates")
    if not isinstance(templates, list) or not templates:
        raise BuildError("release configuration contains no usable templates")

    for template in templates:
        items = template.get("items")
        if not isinstance(items, list) or not items:
            raise BuildError(f"release template {template.get('id')} has no items")
        conn.execute(
            """INSERT INTO templates
               (id,name,description,version,scope_note,category)
               VALUES (?,?,?,?,?,?)""",
            (
                template["id"],
                template["name"],
                template.get("description"),
                template["version"],
                template.get("scope_note"),
                template.get("category"),
            ),
        )
        for item in items:
            conn.execute(
                """INSERT INTO template_items
                   (id,template_id,artifact_id,inclusion_status,inclusion_reason,
                    applicability_condition,priority_override,review_frequency_override)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (
                    item["id"],
                    template["id"],
                    item["artifact_id"],
                    item["inclusion_status"],
                    item.get("inclusion_reason"),
                    item.get("applicability_condition"),
                    item.get("priority_override"),
                    item.get("review_frequency_override"),
                ),
            )


def _normalize_release_build_timestamps(
    conn: sqlite3.Connection, config: dict, applied: list[str]
) -> str:
    """Normalize only build-created technical timestamps for bit reproducibility.

    The governed source database's audit timestamps remain untouched. The
    configured UTC source date is applied to migration/template rows and to
    compatibility rows introduced by migrations in this build.
    """

    configured = config.get("reproducible_build_timestamp_utc")
    if not isinstance(configured, str) or not configured.endswith("Z"):
        raise BuildError("release configuration requires a UTC reproducible timestamp")
    try:
        parsed = datetime.fromisoformat(configured[:-1] + "+00:00")
    except ValueError as exc:
        raise BuildError("invalid reproducible build timestamp") from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise BuildError("reproducible build timestamp must use UTC")
    sqlite_timestamp = parsed.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    # Normalize derived-release technical timestamps irrespective of whether a
    # preceding curated preparation step applied the migrations in this call.
    conn.execute("UPDATE schema_migrations SET applied_at=?", (sqlite_timestamp,))
    conn.execute(
        "UPDATE artifact_localizations SET created_at=?,updated_at=?",
        (sqlite_timestamp, sqlite_timestamp),
    )
    conn.execute(
        "UPDATE application_state SET updated_at=? WHERE singleton_id=1",
        (sqlite_timestamp,),
    )

    template_ids = [template["id"] for template in config["templates"]]
    placeholders = ",".join("?" for _ in template_ids)
    conn.execute(
        f"UPDATE templates SET created_at=? WHERE id IN ({placeholders})",
        (sqlite_timestamp, *template_ids),
    )
    return configured


def _release_gates(conn: sqlite3.Connection) -> dict[str, int | dict[str, int]]:
    counts = {
        "artifacts": _table_count(conn, "security_artifacts") or 0,
        "rawArtifacts": _table_count(conn, "raw_artifacts") or 0,
        "templates": _table_count(conn, "templates") or 0,
        "templateItems": _table_count(conn, "template_items") or 0,
    }
    if counts["artifacts"] == 0:
        raise BuildError("release catalog has no security artifacts")
    if counts["rawArtifacts"] == 0:
        raise BuildError("release catalog has no preserved raw source records")

    invalid_publication = conn.execute(
        """SELECT COUNT(*) FROM security_artifacts
           WHERE is_active<>1 OR publication_status NOT IN ('APPROVED','PUBLISHED')"""
    ).fetchone()[0]
    if invalid_publication:
        raise BuildError(
            f"release catalog contains {invalid_publication} inactive or unpublished artifact(s)"
        )

    demo_markers = conn.execute(
        """SELECT COUNT(*) FROM security_artifacts
           WHERE lower(id) LIKE '%demo%' OR lower(id) LIKE '%test%'
              OR lower(title_en) LIKE '%demo%' OR lower(title_en) LIKE '%test fixture%'
              OR lower(COALESCE(source_document,'')) LIKE '%test fixture%'"""
    ).fetchone()[0]
    if demo_markers:
        raise BuildError("release catalog contains demo/test fixture content")

    contract = load_contract()
    minimum_valid = strict_conformant = requires_review = human_approved = 0
    for row in conn.execute("SELECT * FROM security_artifacts ORDER BY id"):
        minimum_valid += int(minimum_result(conn, row, contract)["valid"])
        strict_conformant += int(strict_result(conn, row)["valid"])
        requires_review += int(bool(row["requires_human_review"]))
        human_approved += int(row["ai_review_status"] == "AIR-HUMAN-APPROVED")
    if minimum_valid != counts["artifacts"]:
        raise BuildError(
            f"release catalog has {counts['artifacts'] - minimum_valid} artifact(s) "
            "that fail MINIMUM_CATALOG_VALIDATION"
        )

    closure = conn.execute("SELECT * FROM v_catalog_closure").fetchone()
    if closure["missing_dispositions"] or closure["missing_canonical_lineage"]:
        raise BuildError(
            "release catalog does not have complete raw dispositions and final lineage"
        )
    inconsistent = conn.execute(
        """SELECT COUNT(*) FROM raw_artifact_dispositions d
             WHERE d.disposition IN ('SUPPORTS_CANONICAL','SPLIT') AND NOT EXISTS(
               SELECT 1 FROM artifact_source_lineage l
                WHERE l.raw_artifact_id=d.raw_artifact_id
                  AND l.lineage_role=d.disposition)"""
    ).fetchone()[0]
    if inconsistent:
        raise BuildError(f"release catalog has {inconsistent} disposition/lineage mismatch(es)")

    if counts["templates"] == 0 or counts["templateItems"] == 0:
        raise BuildError("release catalog has no usable template selection")
    unusable_templates = conn.execute(
        """SELECT COUNT(*) FROM templates t
            WHERE NOT EXISTS (
                SELECT 1 FROM template_items ti
                JOIN security_artifacts sa ON sa.id=ti.artifact_id
                WHERE ti.template_id=t.id
                  AND sa.is_active=1 AND sa.publication_status='APPROVED'
            )"""
    ).fetchone()[0]
    if unusable_templates:
        raise BuildError(f"release catalog has {unusable_templates} unusable template(s)")
    counts["quality"] = {
        "minimumValid": minimum_valid,
        "strictConformant": strict_conformant,
        "requiresHumanReview": requires_review,
        "humanApproved": human_approved,
    }
    counts["closure"] = {
        "rawDisposed": int(closure["raw_disposed"]),
        "canonicalsWithLineage": int(closure["canonicals_with_lineage"]),
    }
    return counts


def _scrub_unlicensed_raw_payload(conn: sqlite3.Connection) -> dict[str, int]:
    """Remove raw payload from the mobile derivative unless rights allow it."""
    total = conn.execute("SELECT COUNT(*) FROM raw_artifacts").fetchone()[0]
    allowed = conn.execute(
        """SELECT COUNT(*) FROM raw_artifacts r WHERE EXISTS(
               SELECT 1 FROM source_rights_versions sr
                WHERE sr.source_catalog_id=r.source_catalog_id
                  AND sr.source_version=COALESCE(r.source_version,'UNKNOWN')
                  AND sr.is_current=1 AND sr.redistribution_status='ALLOWED'
                  AND sr.ship_raw_text=1)"""
    ).fetchone()[0]
    conn.execute(
        """UPDATE raw_artifacts SET
               raw_text_en=NULL,raw_text_ar=NULL,raw_json='{}',title_draft=NULL,
               description_draft=NULL,original_heading=NULL,context_paragraph=NULL,
               keywords_json=NULL,entities_mentioned_json=NULL
             WHERE NOT EXISTS(
               SELECT 1 FROM source_rights_versions sr
                WHERE sr.source_catalog_id=raw_artifacts.source_catalog_id
                  AND sr.source_version=COALESCE(raw_artifacts.source_version,'UNKNOWN')
                  AND sr.is_current=1 AND sr.redistribution_status='ALLOWED'
                  AND sr.ship_raw_text=1)"""
    )
    # Staging is a work-product surface containing source-derived drafts; the
    # mobile runtime consumes canonical artifacts and final lineage instead.
    conn.execute("DELETE FROM promotion_batch_items")
    conn.execute("DELETE FROM staging_artifacts")
    return {
        "rawRecordsTotal": int(total),
        "rawPayloadsIncluded": int(allowed),
        "rawPayloadsExcluded": int(total - allowed),
    }


def _canonical_manifest_hash(manifest: dict) -> str:
    material = {key: value for key, value in manifest.items() if key != "manifestSha256"}
    return canonical_hash(material)


def _publish_pair(database_temp: Path, manifest_temp: Path, output: Path, manifest_path: Path) -> None:
    """Failure-atomic two-file promotion with rollback of any existing pair."""
    database_backup = output.with_name(f".{output.name}.previous")
    manifest_backup = manifest_path.with_name(f".{manifest_path.name}.previous")
    for backup in (database_backup, manifest_backup):
        if backup.exists():
            backup.unlink()
    moved_database = moved_manifest = False
    try:
        if output.exists():
            os.replace(output, database_backup)
            moved_database = True
        if manifest_path.exists():
            os.replace(manifest_path, manifest_backup)
            moved_manifest = True
        os.replace(database_temp, output)
        os.replace(manifest_temp, manifest_path)
    except Exception:
        if output.exists():
            output.unlink()
        if manifest_path.exists():
            manifest_path.unlink()
        if moved_database:
            os.replace(database_backup, output)
        if moved_manifest:
            os.replace(manifest_backup, manifest_path)
        raise
    finally:
        for backup in (database_backup, manifest_backup):
            if backup.exists():
                backup.unlink()


def build(
    output: Path,
    *,
    mode: str = "demo",
    migrations: Path | None = None,
    release_source: Path | None = None,
    release_config: Path | None = None,
) -> dict:
    if mode not in {"demo", "release", "curated"}:
        raise BuildError(f"unsupported mode: {mode}")
    migrations = migrations or (ROOT / "migrations")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.building")
    if temporary.exists():
        temporary.unlink()

    release_counts: dict[str, int] | None = None
    source_hash: str | None = None
    if mode in {"release", "curated"}:
        source = release_source or DEFAULT_RELEASE_SOURCE
        config_path = release_config or DEFAULT_RELEASE_CONFIG
        config, baseline = _load_release_configuration(config_path)
        _validate_release_source(source, baseline)
        source_hash = _sha256(source)
        if mode == "release":
            shutil.copy2(source, temporary)
        else:
            prepare_curation_database(source, temporary)
    else:
        temporary.touch()

    try:
        applied = apply_migrations(temporary, migrations)
        if mode == "demo":
            seed_catalog(temporary)
            service = SecureGuideService(Database(temporary))
            context = build_read_model_dataset(service)
        else:
            context = None
            reproducible_timestamp = None
            conn = connect(temporary)
            try:
                provenance = backfill_source_provenance(conn)
                curation = (
                    curate_complete_catalog(conn)
                    if mode == "curated" else close_existing_catalog(conn)
                )
                conn.execute("BEGIN IMMEDIATE")
                _install_release_templates(conn, config)
                reproducible_timestamp = _normalize_release_build_timestamps(
                    conn, config, list(applied)
                )
                rights_summary = _scrub_unlicensed_raw_payload(conn)
                sqlite_timestamp = reproducible_timestamp.replace("T", " ").replace("Z", "")
                for table, column in (
                    ("source_import_manifests", "created_at"),
                    ("artifact_source_lineage", "created_at"),
                    ("raw_artifact_dispositions", "decided_at"),
                    ("catalog_artifact_id_aliases", "created_at"),
                ):
                    conn.execute(f"UPDATE {table} SET {column}=?", (sqlite_timestamp,))
                if mode == "curated":
                    conn.execute(
                        "UPDATE source_catalogs SET imported_at=? WHERE id IN ('legacy_catalog_v4','securekit_curated_controls')",
                        (sqlite_timestamp,),
                    )
                    conn.execute(
                        "UPDATE raw_artifacts SET imported_at=? WHERE source_catalog_id IN ('legacy_catalog_v4','securekit_curated_controls')",
                        (sqlite_timestamp,),
                    )
                    conn.execute(
                        "UPDATE security_artifacts SET created_at=?,updated_at=? "
                        "WHERE id GLOB 'SG-*-CAT-*' OR id GLOB 'SG-*-CURATED-*'",
                        (sqlite_timestamp, sqlite_timestamp),
                    )
                    conn.execute(
                        "UPDATE artifact_localizations SET created_at=?,updated_at=? "
                        "WHERE artifact_id GLOB 'SG-*-CAT-*' OR artifact_id GLOB 'SG-*-CURATED-*'",
                        (sqlite_timestamp, sqlite_timestamp),
                    )
                conn.execute("COMMIT")
            except Exception:
                if conn.in_transaction:
                    conn.execute("ROLLBACK")
                raise
            finally:
                conn.close()

        conn = connect(temporary)
        try:
            _run_gates(conn)
            if mode in {"release", "curated"}:
                release_counts = _release_gates(conn)
            schema_version = _schema_version(conn)
            conn.execute(f"PRAGMA user_version={int(schema_version)}")
            manifest = {
                "name": "catalog.db" if mode in {"release", "curated"} else output.name,
                "builtWith": "scripts.build_release_db",
                "mode": mode,
                "generatedAt": (
                    reproducible_timestamp if mode in {"release", "curated"}
                    else datetime.now(timezone.utc).isoformat()
                ),
                "schemaVersion": schema_version,
                "appliedMigrations": list(applied),
                "publicationStatus": _publication_breakdown(conn),
                "counts": {table: _table_count(conn, table) for table in COUNT_TABLES},
                "gatesPassed": ["integrity_check", "foreign_key_check", *GOVERNANCE_GATES],
            }
            if context is not None:
                manifest["demoContext"] = context
            if release_counts is not None:
                manifest["releaseCounts"] = release_counts
                manifest["sourceSha256"] = source_hash
                manifest["sourceManifestSha256"] = provenance["manifestSha256"]
                manifest["rights"] = rights_summary
                manifest["curation"] = curation
                manifest["reproducibleBuildTimestampUtc"] = reproducible_timestamp
                manifest["minimumContractSha256"] = file_hash(
                    ROOT / "config" / "catalog_minimum_fields.yaml"
                )
                manifest["sourceRightsSha256"] = file_hash(
                    ROOT / "config" / "source_rights.yaml"
                )
                manifest["curatedClassificationsSha256"] = file_hash(
                    ROOT / "consolidation" / "curated" / "classifications.json"
                )
                manifest["legacyClassificationsSha256"] = file_hash(
                    ROOT / "consolidation" / "curated" / "legacy_classifications.json"
                )
                manifest["equivalenceDecisionsSha256"] = file_hash(
                    ROOT / "consolidation" / "unified" / "equivalence.json"
                )
                manifest["catalogContentSha256"] = catalog_state_hash(conn)
                manifest["gatesPassed"].extend(
                    ["minimum_catalog_validation", "raw_disposition_closure",
                     "raw_source_lineage", "source_rights", "usable_templates"]
                )
        finally:
            conn.close()
        conn = connect(temporary)
        try:
            conn.execute("VACUUM")
        finally:
            conn.close()
    except Exception:
        if temporary.exists():
            temporary.unlink()
        raise

    manifest["sizeBytes"] = temporary.stat().st_size
    manifest["sha256"] = _sha256(temporary)
    manifest["manifestSha256"] = _canonical_manifest_hash(manifest)
    manifest_path = output.with_suffix(output.suffix + ".manifest.json")
    manifest_temp = manifest_path.with_name(f".{manifest_path.name}.building")
    manifest_temp.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    _publish_pair(temporary, manifest_temp, output, manifest_path)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a governed SecureGuide seed database.")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "dist" / "secureguide-demo.db",
        help="path to write the seed database (default: dist/secureguide-demo.db)",
    )
    parser.add_argument("--mode", default="demo", choices=["demo", "release", "curated"])
    parser.add_argument("--migrations", type=Path, default=None)
    parser.add_argument("--release-source", type=Path, default=None)
    parser.add_argument("--release-config", type=Path, default=None)
    args = parser.parse_args()

    manifest = build(
        args.output,
        mode=args.mode,
        migrations=args.migrations,
        release_source=args.release_source,
        release_config=args.release_config,
    )
    print(f"built {args.output} (schema {manifest['schemaVersion']}, {manifest['sizeBytes']:,} bytes)")
    print(f"  publication: {manifest['publicationStatus']}")
    print(f"  profiles={manifest['counts'].get('enterprise_profiles')} "
          f"blueprints={manifest['counts'].get('approved_blueprints')} "
          f"tasks={manifest['counts'].get('profile_tasks')}")
    print(f"  gates passed: {', '.join(manifest['gatesPassed'])}")
    print(f"  sha256: {manifest['sha256']}")


if __name__ == "__main__":
    main()
