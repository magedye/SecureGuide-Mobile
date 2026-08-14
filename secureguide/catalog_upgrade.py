"""Transactional catalog-content upgrade with operational preservation gates."""

from __future__ import annotations

import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Iterable

from secureguide.catalog_validation import canonical_hash, file_hash, load_contract, minimum_result
from secureguide.database import apply_migrations, connect


OPERATIONAL_NAME_FILTERS = ("profile_", "approved_blueprint", "blueprint_")
STABLE_TABLES = (
    "source_catalogs", "source_import_manifests", "source_rights_versions",
    "security_artifacts", "raw_artifacts", "artifact_localizations",
    "artifact_source_lineage", "raw_artifact_dispositions", "artifact_platforms",
    "artifact_threats", "catalog_legacy_provenance", "catalog_legacy_assets",
    "catalog_artifact_id_aliases",
    "artifact_actions", "artifact_tags", "external_references",
    "templates", "template_items",
)


class CatalogUpgradeError(RuntimeError):
    pass


def _columns(conn: sqlite3.Connection, table: str) -> list[str]:
    return [row[1] for row in conn.execute(f"PRAGMA table_info([{table}])")]


def _primary_key(conn: sqlite3.Connection, table: str) -> list[str]:
    return [row[1] for row in sorted(
        conn.execute(f"PRAGMA table_info([{table}])"), key=lambda item: item[5]
    ) if row[5]]


def operational_snapshot(
    conn: sqlite3.Connection, aliases: dict[str, str] | None = None
) -> dict[str, Any]:
    tables = [row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ) if row[0] in {"application_state", "enterprise_profiles"}
        or row[0].startswith(OPERATIONAL_NAME_FILTERS)]
    payload: dict[str, Any] = {}
    for table in tables:
        columns = _columns(conn, table)
        order = _primary_key(conn, table) or columns
        rows = conn.execute(
            f"SELECT * FROM [{table}] ORDER BY " + ",".join(f"[{column}]" for column in order)
        ).fetchall()
        normalized_rows = []
        for row in rows:
            values = {column: row[index] for index, column in enumerate(columns)}
            if aliases:
                for column in columns:
                    if column == "artifact_id" and values[column] in aliases:
                        values[column] = aliases[values[column]]
            normalized_rows.append(values)
        payload[table] = normalized_rows
    return {"sha256": canonical_hash(payload), "tables": payload}


def _artifact_reference_columns(conn: sqlite3.Connection) -> list[tuple[str, str]]:
    """Return operational/template columns that directly reference catalog IDs."""

    result: list[tuple[str, str]] = []
    for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ):
        table = row[0]
        operational = (
            table in {"template_items"}
            or table.startswith(OPERATIONAL_NAME_FILTERS)
        )
        if not operational:
            continue
        for fk in conn.execute(f"PRAGMA foreign_key_list([{table}])"):
            if fk[2] == "security_artifacts" and fk[4] == "id":
                result.append((table, fk[3]))
    return result


def _remap_artifact_references(
    conn: sqlite3.Connection, aliases: dict[str, str]
) -> int:
    updated = 0
    for table, column in _artifact_reference_columns(conn):
        for old_id, artifact_id in sorted(aliases.items()):
            cursor = conn.execute(
                f"UPDATE [{table}] SET [{column}]=? WHERE [{column}]=?",
                (artifact_id, old_id),
            )
            updated += cursor.rowcount
    return updated


def _remap_catalog_identity_references(
    conn: sqlite3.Connection, aliases: dict[str, str]
) -> int:
    """Remap references while preserving immutable final source lineage."""

    conn.execute("DROP TABLE IF EXISTS temp.catalog_alias_map")
    conn.execute(
        "CREATE TEMP TABLE catalog_alias_map(old_id TEXT PRIMARY KEY,new_id TEXT NOT NULL)"
    )
    conn.executemany(
        "INSERT INTO temp.catalog_alias_map(old_id,new_id) VALUES(?,?)",
        sorted(aliases.items()),
    )
    updated = 0
    try:
        for table, column in _artifact_reference_columns(conn):
            updated += conn.execute(
                f'''UPDATE [{table}]
                       SET [{column}]=(SELECT new_id FROM temp.catalog_alias_map m
                                        WHERE m.old_id=[{table}].[{column}])
                     WHERE [{column}] IN (SELECT old_id FROM temp.catalog_alias_map)'''
            ).rowcount
        # Several former canonicals may consolidate into one target. Demoting
        # their primary flags first avoids the one-primary-per-canonical index;
        # candidate upserts restore the authoritative primary row.
        updated += conn.execute(
            """UPDATE artifact_source_lineage SET is_primary=0
                 WHERE artifact_id IN (SELECT old_id FROM temp.catalog_alias_map)"""
        ).rowcount
        updated += conn.execute(
            """UPDATE artifact_source_lineage
                  SET artifact_id=(SELECT new_id FROM temp.catalog_alias_map m
                                    WHERE m.old_id=artifact_source_lineage.artifact_id)
                WHERE artifact_id IN (SELECT old_id FROM temp.catalog_alias_map)"""
        ).rowcount
        updated += conn.execute(
            """UPDATE raw_artifacts
                  SET promoted_artifact_id=(SELECT new_id FROM temp.catalog_alias_map m
                                             WHERE m.old_id=raw_artifacts.promoted_artifact_id)
                WHERE promoted_artifact_id IN (SELECT old_id FROM temp.catalog_alias_map)"""
        ).rowcount
        updated += conn.execute(
            """UPDATE artifact_relationships
                  SET source_id=(SELECT new_id FROM temp.catalog_alias_map m
                                  WHERE m.old_id=artifact_relationships.source_id)
                WHERE source_id IN (SELECT old_id FROM temp.catalog_alias_map)"""
        ).rowcount
        updated += conn.execute(
            """UPDATE artifact_relationships
                  SET target_id=(SELECT new_id FROM temp.catalog_alias_map m
                                  WHERE m.old_id=artifact_relationships.target_id)
                WHERE target_id IN (SELECT old_id FROM temp.catalog_alias_map)"""
        ).rowcount
        return updated
    finally:
        conn.execute("DROP TABLE IF EXISTS temp.catalog_alias_map")


def _raw_identity_aliases(
    installed: sqlite3.Connection, candidate: sqlite3.Connection
) -> dict[str, tuple[str, str]]:
    """Match renamed raw rows by immutable record identity and content hash."""

    existing_ids = {row[0] for row in installed.execute("SELECT id FROM raw_artifacts")}
    by_evidence: dict[tuple[str, str], list[str]] = {}
    for row in installed.execute(
        "SELECT id,external_raw_id,content_hash FROM raw_artifacts"
    ):
        if row[1] and row[2]:
            by_evidence.setdefault((row[1], row[2]), []).append(row[0])
    aliases: dict[str, tuple[str, str]] = {}
    for row in candidate.execute(
        "SELECT id,source_catalog_id,external_raw_id,content_hash FROM raw_artifacts"
    ):
        if row[0] in existing_ids or not row[2] or not row[3]:
            continue
        matches = [value for value in by_evidence.get((row[2], row[3]), []) if value != row[0]]
        if len(matches) > 1:
            raise CatalogUpgradeError(
                f"ambiguous raw identity migration for candidate {row[0]}"
            )
        if matches:
            if matches[0] in aliases and aliases[matches[0]][0] != row[0]:
                raise CatalogUpgradeError(
                    f"multiple candidate raw identities match installed row {matches[0]}"
                )
            aliases[matches[0]] = (row[0], row[1])
    return aliases


def _remap_raw_identities(
    conn: sqlite3.Connection, aliases: dict[str, tuple[str, str]]
) -> int:
    updated = 0
    for old_id, (raw_id, source_catalog_id) in sorted(aliases.items()):
        for table, column in (
            ("artifact_source_lineage", "raw_artifact_id"),
            ("raw_artifact_dispositions", "raw_artifact_id"),
        ):
            cursor = conn.execute(
                f"UPDATE [{table}] SET [{column}]=? WHERE [{column}]=?",
                (raw_id, old_id),
            )
            updated += cursor.rowcount
        cursor = conn.execute(
            "UPDATE raw_artifacts SET id=?,source_catalog_id=? WHERE id=?",
            (raw_id, source_catalog_id, old_id),
        )
        updated += cursor.rowcount
    return updated


def _delete_rows_missing_from_candidate(
    installed: sqlite3.Connection,
    candidate: sqlite3.Connection,
    table: str,
    key: str = "id",
    *,
    extra_where: str = "",
) -> int:
    values = {row[0] for row in candidate.execute(f"SELECT [{key}] FROM [{table}]")}
    rows = [row[0] for row in installed.execute(f"SELECT [{key}] FROM [{table}] {extra_where}")]
    stale = [value for value in rows if value not in values]
    for value in stale:
        installed.execute(f"DELETE FROM [{table}] WHERE [{key}]=?", (value,))
    return len(stale)


def _remove_stale_artifact_dependents(
    installed: sqlite3.Connection, candidate: sqlite3.Connection
) -> dict[str, int]:
    """Remove candidate-owned RESTRICT children before obsolete parents."""

    candidate_ids = {
        row[0] for row in candidate.execute("SELECT id FROM security_artifacts")
    }
    stale_ids = [
        row[0]
        for row in installed.execute(
            "SELECT id FROM security_artifacts WHERE is_custom=0 ORDER BY id"
        )
        if row[0] not in candidate_ids
    ]
    counts = {"relationships": 0, "rawPromotionsCleared": 0}
    for artifact_id in stale_ids:
        counts["relationships"] += installed.execute(
            "DELETE FROM artifact_relationships WHERE source_id=? OR target_id=?",
            (artifact_id, artifact_id),
        ).rowcount
        counts["rawPromotionsCleared"] += installed.execute(
            "UPDATE raw_artifacts SET promoted_artifact_id=NULL WHERE promoted_artifact_id=?",
            (artifact_id,),
        ).rowcount
    return counts


def _upsert_stable_table(
    installed: sqlite3.Connection, candidate: sqlite3.Connection, table: str
) -> int:
    target_columns = _columns(installed, table)
    source_columns = set(_columns(candidate, table))
    columns = [column for column in target_columns if column in source_columns]
    keys = _primary_key(installed, table)
    if not keys:
        raise CatalogUpgradeError(f"catalog table {table} has no stable primary key")
    updates = [column for column in columns if column not in keys]
    count = 0
    for row in candidate.execute(
        f"SELECT {','.join(f'[{column}]' for column in columns)} FROM [{table}] "
        f"ORDER BY {','.join(f'[{key}]' for key in keys)}"
    ):
        values = tuple(row[column] for column in columns)
        sql = (
            f"INSERT INTO [{table}]({','.join(f'[{column}]' for column in columns)}) "
            f"VALUES({','.join('?' for _ in columns)}) ON CONFLICT({','.join(keys)}) "
        )
        if updates:
            sql += "DO UPDATE SET " + ",".join(
                f"[{column}]=excluded.[{column}]" for column in updates
            )
        else:
            sql += "DO NOTHING"
        installed.execute(sql, values)
        count += 1
    return count


def _merge_framework_mappings(installed: sqlite3.Connection, candidate: sqlite3.Connection) -> int:
    count = 0
    for row in candidate.execute(
        "SELECT artifact_id,framework,version,reference,mapping_strength,rationale "
        "FROM framework_mappings ORDER BY artifact_id,framework,version,reference"
    ):
        existing = installed.execute(
            """SELECT id FROM framework_mappings
                 WHERE artifact_id=? AND framework=? AND version=? AND reference=?""",
            (row["artifact_id"], row["framework"], row["version"], row["reference"]),
        ).fetchone()
        if existing:
            installed.execute(
                "UPDATE framework_mappings SET mapping_strength=?,rationale=? WHERE id=?",
                (row["mapping_strength"], row["rationale"], existing[0]),
            )
        else:
            installed.execute(
                """INSERT INTO framework_mappings(
                       artifact_id,framework,version,reference,mapping_strength,rationale
                   ) VALUES(?,?,?,?,?,?)""",
                tuple(row),
            )
        count += 1
    return count


def _merge_remediation_actions(installed: sqlite3.Connection, candidate: sqlite3.Connection) -> int:
    count = 0
    for row in candidate.execute(
        "SELECT artifact_id,action,priority,effort_estimate,responsible_role "
        "FROM remediation_actions ORDER BY artifact_id,action"
    ):
        existing = installed.execute(
            "SELECT id FROM remediation_actions WHERE artifact_id=? AND action=?",
            (row["artifact_id"], row["action"]),
        ).fetchone()
        if existing:
            installed.execute(
                """UPDATE remediation_actions SET priority=?,effort_estimate=?,responsible_role=?
                     WHERE id=?""",
                (row["priority"], row["effort_estimate"], row["responsible_role"], existing[0]),
            )
        else:
            installed.execute(
                """INSERT INTO remediation_actions(
                       artifact_id,action,priority,effort_estimate,responsible_role
                   ) VALUES(?,?,?,?,?)""",
                tuple(row),
            )
        count += 1
    return count


def upgrade_catalog(
    installed_database: str | Path,
    candidate_database: str | Path,
    *,
    actor: str = "codex",
) -> dict[str, Any]:
    installed_path = Path(installed_database).resolve()
    candidate_path = Path(candidate_database).resolve()
    if installed_path == candidate_path:
        raise CatalogUpgradeError("installed and candidate databases must differ")
    if not installed_path.is_file() or not candidate_path.is_file():
        raise CatalogUpgradeError("installed and candidate databases must exist")

    started = time.perf_counter()
    apply_migrations(installed_path)
    installed = connect(installed_path)
    candidate = connect(candidate_path)
    run_id = f"CUG-{uuid.uuid4()}"
    try:
        candidate_integrity = candidate.execute("PRAGMA integrity_check").fetchone()[0]
        if candidate_integrity != "ok" or candidate.execute("PRAGMA foreign_key_check").fetchall():
            raise CatalogUpgradeError("candidate integrity validation failed")
        installed_tables = {row[0] for row in installed.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
        candidate_tables = {row[0] for row in candidate.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
        required = set(STABLE_TABLES) | {"framework_mappings", "remediation_actions"}
        missing = sorted(required - installed_tables | required - candidate_tables)
        if missing:
            raise CatalogUpgradeError(f"upgrade schema is missing tables: {missing}")

        old_rows = installed.execute(
            "SELECT id,type FROM security_artifacts WHERE is_custom=0 ORDER BY id"
        ).fetchall()
        candidate_types = {
            row[0]: row[1] for row in candidate.execute("SELECT id,type FROM security_artifacts")
        }
        aliases = {
            row[0]: row[1]
            for row in candidate.execute(
                "SELECT old_artifact_id,artifact_id FROM catalog_artifact_id_aliases"
            )
        }
        raw_aliases = _raw_identity_aliases(installed, candidate)
        missing_ids = [
            row[0] for row in old_rows
            if row[0] not in candidate_types and row[0] not in aliases
        ]
        changed_types = [
            row[0] for row in old_rows
            if row[0] in candidate_types and candidate_types[row[0]] != row[1]
        ]
        if missing_ids or changed_types:
            raise CatalogUpgradeError(
                f"stable-ID guard failed: missing={missing_ids[:3]} changedTypes={changed_types[:3]}"
            )

        before = operational_snapshot(installed, aliases)
        installed_hash_before = file_hash(installed_path)
        candidate_hash = file_hash(candidate_path)
        counts: dict[str, int] = {}
        installed.execute("BEGIN IMMEDIATE")
        try:
            installed.execute("PRAGMA defer_foreign_keys=ON")
            for table in ("source_catalogs", "security_artifacts"):
                counts[table] = _upsert_stable_table(installed, candidate, table)
            counts["remappedArtifactReferences"] = _remap_catalog_identity_references(
                installed, aliases
            )
            counts["remappedRawIdentities"] = _remap_raw_identities(
                installed, raw_aliases
            )
            for table in STABLE_TABLES:
                if table in {"source_catalogs", "security_artifacts"}:
                    continue
                try:
                    counts[table] = _upsert_stable_table(installed, candidate, table)
                except Exception as exc:
                    raise CatalogUpgradeError(f"failed to merge catalog table {table}: {exc}") from exc
            counts["framework_mappings"] = _merge_framework_mappings(installed, candidate)
            counts["remediation_actions"] = _merge_remediation_actions(installed, candidate)
            counts["removedStaleArtifactDependents"] = _remove_stale_artifact_dependents(
                installed, candidate
            )
            counts["removedStaleArtifacts"] = _delete_rows_missing_from_candidate(
                installed,
                candidate,
                "security_artifacts",
                extra_where="WHERE is_custom=0",
            )
            counts["removedStaleRawArtifacts"] = _delete_rows_missing_from_candidate(
                installed, candidate, "raw_artifacts"
            )
            counts["removedStaleSourceManifests"] = _delete_rows_missing_from_candidate(
                installed, candidate, "source_import_manifests"
            )
            counts["removedStaleSourceRights"] = _delete_rows_missing_from_candidate(
                installed, candidate, "source_rights_versions"
            )
            counts["removedStaleSourceCatalogs"] = _delete_rows_missing_from_candidate(
                installed, candidate, "source_catalogs"
            )
            installed.execute("DELETE FROM promotion_batch_items")
            installed.execute("DELETE FROM staging_artifacts")
            after = operational_snapshot(installed)
            if after["sha256"] != before["sha256"]:
                raise CatalogUpgradeError("operational/profile snapshot changed during catalog upgrade")
            contract = load_contract()
            invalid = []
            for row in installed.execute(
                "SELECT * FROM security_artifacts WHERE is_active=1 AND is_custom=0 ORDER BY id"
            ):
                result = minimum_result(installed, row, contract)
                if not result["valid"]:
                    invalid.append({"id": row["id"], "missing": result["missing"]})
            if invalid:
                raise CatalogUpgradeError(f"post-upgrade minimum validation failed: {invalid[:3]}")
            integrity = installed.execute("PRAGMA integrity_check").fetchone()[0]
            fk = installed.execute("PRAGMA foreign_key_check").fetchall()
            if integrity != "ok" or fk:
                raise CatalogUpgradeError(
                    f"post-upgrade integrity failed: integrity={integrity}, "
                    f"fk={len(fk)} sample={[tuple(row) for row in fk[:3]]}"
                )
            installed.execute(
                """INSERT INTO catalog_upgrade_runs(
                       id,candidate_sha256,installed_sha256_before,
                       operational_snapshot_before,operational_snapshot_after,status,
                       old_artifact_count,new_artifact_count,actor,completed_at
                   ) VALUES(?,?,?,?,?,'APPLIED',?,?,?,datetime('now'))""",
                (run_id, candidate_hash, installed_hash_before, before["sha256"],
                 after["sha256"], len(old_rows),
                 installed.execute("SELECT COUNT(*) FROM security_artifacts").fetchone()[0], actor),
            )
            installed.execute("COMMIT")
        except Exception:
            if installed.in_transaction:
                installed.execute("ROLLBACK")
            raise
        installed_hash_after = file_hash(installed_path)
        installed.execute(
            "UPDATE catalog_upgrade_runs SET installed_sha256_after=? WHERE id=?",
            (installed_hash_after, run_id),
        )
        installed.commit()
        result = {
            "status": "APPLIED", "runId": run_id,
            "candidateSha256": candidate_hash,
            "installedSha256Before": installed_hash_before,
            "installedSha256After": file_hash(installed_path),
            "operationalSnapshotBefore": before["sha256"],
            "operationalSnapshotAfter": after["sha256"],
            "oldArtifactCount": len(old_rows),
            "newArtifactCount": installed.execute("SELECT COUNT(*) FROM security_artifacts").fetchone()[0],
            "durationMs": round((time.perf_counter() - started) * 1000, 3),
            "rowsProcessed": counts,
        }
        return result
    finally:
        candidate.close()
        installed.close()
