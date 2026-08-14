-- SecureGuide migration 032: audited Excel catalog curation runs.
PRAGMA foreign_keys = ON;

INSERT OR IGNORE INTO schema_migrations(version, description)
VALUES('032', 'Audited and conflict-safe catalog workbook runs');

CREATE TABLE catalog_workbook_runs (
    id                       TEXT PRIMARY KEY,
    operation                TEXT NOT NULL,
    workbook_path            TEXT NOT NULL,
    baseline_db_sha256       TEXT NOT NULL,
    workbook_sha256          TEXT,
    status                   TEXT NOT NULL,
    actor                    TEXT NOT NULL,
    conflict_resolution_json TEXT,
    summary_json             TEXT,
    created_at               TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at             TEXT,
    CHECK(operation IN ('EXPORT','VALIDATE','PLAN','APPLY')),
    CHECK(status IN ('STARTED','VALID','INVALID','PLANNED','CONFLICT','APPLIED','FAILED')),
    CHECK(length(baseline_db_sha256)=64 AND lower(baseline_db_sha256) NOT GLOB '*[^0-9a-f]*'),
    CHECK(workbook_sha256 IS NULL OR
          (length(workbook_sha256)=64 AND lower(workbook_sha256) NOT GLOB '*[^0-9a-f]*'))
);
CREATE INDEX idx_workbook_runs_status ON catalog_workbook_runs(status, created_at);

CREATE TABLE catalog_workbook_row_audit (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id         TEXT NOT NULL REFERENCES catalog_workbook_runs(id) ON DELETE RESTRICT,
    sheet_name     TEXT NOT NULL,
    row_key        TEXT NOT NULL,
    action         TEXT NOT NULL,
    baseline_hash  TEXT,
    current_hash   TEXT,
    proposed_hash  TEXT,
    outcome        TEXT NOT NULL,
    resolution     TEXT,
    detail         TEXT,
    created_at     TEXT NOT NULL DEFAULT (datetime('now')),
    CHECK(action IN ('NO_CHANGE','UPSERT','DEPRECATE')),
    CHECK(outcome IN ('NO_CHANGE','VALID','INVALID','CONFLICT','APPLIED','FAILED')),
    CHECK(resolution IS NULL OR resolution IN ('USE_WORKBOOK','USE_DATABASE','MANUAL'))
);
CREATE INDEX idx_workbook_audit_run ON catalog_workbook_row_audit(run_id, sheet_name, row_key);
