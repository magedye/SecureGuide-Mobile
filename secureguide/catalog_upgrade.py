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
    "artifact_threats", "catalog_amani_provenance", "catalog_amani_assets",
    "artifact_actions", "artifact_tags", "templates", "template_items",
)


class CatalogUpgradeError(RuntimeError):
    pass


def _columns(conn: sqlite3.Connection, table: str) -> list[str]:
    return [row[1] for row in conn.execute(f"PRAGMA table_info([{table}])")]


def _primary_key(conn: sqlite3.Connection, table: str) -> list[str]:
    return [row[1] for row in sorted(
        conn.execute(f"PRAGMA table_info([{table}])"), key=lambda item: item[5]
    ) if row[5]]


def operational_snapshot(conn: sqlite3.Connection) -> dict[str, Any]:
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
        payload[table] = [
            {column: row[index] for index, column in enumerate(columns)} for row in rows
        ]
    return {"sha256": canonical_hash(payload), "tables": payload}


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
        missing_ids = [row[0] for row in old_rows if row[0] not in candidate_types]
        changed_types = [row[0] for row in old_rows if candidate_types.get(row[0]) != row[1]]
        if missing_ids or changed_types:
            raise CatalogUpgradeError(
                f"stable-ID guard failed: missing={missing_ids[:3]} changedTypes={changed_types[:3]}"
            )

        before = operational_snapshot(installed)
        installed_hash_before = file_hash(installed_path)
        candidate_hash = file_hash(candidate_path)
        counts: dict[str, int] = {}
        installed.execute("BEGIN IMMEDIATE")
        try:
            for table in STABLE_TABLES:
                try:
                    counts[table] = _upsert_stable_table(installed, candidate, table)
                except Exception as exc:
                    raise CatalogUpgradeError(f"failed to merge catalog table {table}: {exc}") from exc
            counts["framework_mappings"] = _merge_framework_mappings(installed, candidate)
            counts["remediation_actions"] = _merge_remediation_actions(installed, candidate)
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
                    f"post-upgrade integrity failed: integrity={integrity}, fk={len(fk)}"
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
