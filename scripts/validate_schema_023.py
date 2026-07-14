"""Validate migration 023 structure and storage-boundary governance."""

from __future__ import annotations

import tempfile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from secureguide.database import apply_migrations, connect


def main() -> int:
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "schema-023.db"
        applied = apply_migrations(path, ROOT / "migrations")
        if "023" not in applied:
            raise AssertionError("migration 023 was not applied")
        conn = connect(path)
        try:
            expected_tables = {
                "approved_blueprints", "approved_blueprint_rules",
                "approved_blueprint_actions", "approved_blueprint_action_rules",
                "approved_blueprint_outputs", "approved_blueprint_output_rules",
                "approved_blueprint_evidence", "approved_blueprint_evidence_rules",
                "approved_blueprint_review_findings", "blueprint_review_events",
                "profile_tasks", "profile_task_events",
            }
            tables = {
                row[0] for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            missing = expected_tables - tables
            if missing:
                raise AssertionError(f"missing tables: {sorted(missing)}")
            expected_views = {
                "v_profile_blueprints", "v_profile_task_queue",
                "v_blueprint_governance_issues",
            }
            views = {
                row[0] for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='view'"
                ).fetchall()
            }
            if expected_views - views:
                raise AssertionError(f"missing views: {sorted(expected_views - views)}")
            trigger_count = conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='trigger' AND name LIKE 'trg_blueprint_%' OR type='trigger' AND name LIKE 'trg_profile_task_%'"
            ).fetchone()[0]
            if trigger_count < 20:
                raise AssertionError(f"expected storage governance triggers, found {trigger_count}")
            if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise AssertionError("integrity_check failed")
            if conn.execute("PRAGMA foreign_key_check").fetchall():
                raise AssertionError("foreign_key_check failed")
        finally:
            conn.close()
    print("PASS - migration 023 tables, views, and governance triggers are present")
    print("PASS - SQLite integrity and foreign keys are clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
