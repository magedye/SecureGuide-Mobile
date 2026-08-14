-- SecureGuide migration 033: audited catalog-content upgrades.
PRAGMA foreign_keys = ON;

INSERT OR IGNORE INTO schema_migrations(version, description)
VALUES('033', 'Transactional catalog-content upgrade audit');

CREATE TABLE catalog_upgrade_runs (
    id                         TEXT PRIMARY KEY,
    candidate_sha256           TEXT NOT NULL,
    installed_sha256_before    TEXT NOT NULL,
    installed_sha256_after     TEXT,
    operational_snapshot_before TEXT NOT NULL,
    operational_snapshot_after  TEXT,
    status                     TEXT NOT NULL,
    old_artifact_count         INTEGER NOT NULL,
    new_artifact_count         INTEGER,
    actor                      TEXT NOT NULL,
    error_detail               TEXT,
    started_at                 TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at               TEXT,
    CHECK(status IN ('STARTED','APPLIED','FAILED')),
    CHECK(length(candidate_sha256)=64),
    CHECK(length(installed_sha256_before)=64),
    CHECK(installed_sha256_after IS NULL OR length(installed_sha256_after)=64),
    CHECK(length(operational_snapshot_before)=64),
    CHECK(operational_snapshot_after IS NULL OR length(operational_snapshot_after)=64)
);
CREATE INDEX idx_catalog_upgrade_status ON catalog_upgrade_runs(status, started_at);
