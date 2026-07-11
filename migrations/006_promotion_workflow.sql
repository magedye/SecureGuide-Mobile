-- ============================================================================
-- SecureGuide — Migration 006: Promotion Workflow
-- ----------------------------------------------------------------------------
-- Adds the fields and tables needed to promote APPROVED staging_artifacts into
-- the reference catalog (security_artifacts) safely: type-specific proposed
-- fields, final-review state, optimistic-locking hash, and batch/audit tables.
-- Additive only. Does NOT modify migrations 001-005.
-- Promotion rule: all components of an artifact are written in ONE transaction,
-- or nothing is written (enforced by scripts/promote.py).
-- ============================================================================

PRAGMA foreign_keys = ON;

INSERT OR IGNORE INTO schema_migrations (version, description)
VALUES ('006', 'Promotion workflow: staging promotion fields + batches/items/audit');

-- ---- Type-specific proposed fields on staging (filled during final review) ----
ALTER TABLE staging_artifacts ADD COLUMN proposed_requirement_type TEXT;   -- RQT-* for ART-REQ
ALTER TABLE staging_artifacts ADD COLUMN proposed_control_nature TEXT;      -- NAT-* for ART-CTR/CTE
ALTER TABLE staging_artifacts ADD COLUMN proposed_control_function TEXT;    -- FUN-* for ART-CTR/CTE
ALTER TABLE staging_artifacts ADD COLUMN proposed_testability TEXT;         -- TST-* for ART-CTR/CTE
ALTER TABLE staging_artifacts ADD COLUMN proposed_asset_type TEXT;          -- for ART-AST
ALTER TABLE staging_artifacts ADD COLUMN proposed_asset_criticality TEXT;   -- for ART-AST

-- ---- Final-review state on staging ----
ALTER TABLE staging_artifacts ADD COLUMN final_review_status TEXT;          -- APPROVED/REJECTED/SPLIT_AND_APPROVED/DEFERRED
ALTER TABLE staging_artifacts ADD COLUMN ready_for_promotion INTEGER NOT NULL DEFAULT 0;
ALTER TABLE staging_artifacts ADD COLUMN promotion_blockers TEXT;           -- JSON array; empty/null = none
ALTER TABLE staging_artifacts ADD COLUMN approved_at TEXT;
ALTER TABLE staging_artifacts ADD COLUMN approved_by TEXT;
ALTER TABLE staging_artifacts ADD COLUMN content_hash TEXT;                 -- optimistic-locking hash of promotable content

-- ---- Promotion batches (one plan -> one apply -> optional rollback) ----
CREATE TABLE IF NOT EXISTS promotion_batches (
    id             TEXT PRIMARY KEY,
    plan_hash      TEXT NOT NULL,
    status         TEXT NOT NULL DEFAULT 'PLANNED',
    item_count     INTEGER NOT NULL DEFAULT 0,
    created_at     TEXT NOT NULL DEFAULT (datetime('now')),
    applied_at     TEXT,
    rolled_back_at TEXT,
    notes          TEXT,
    CHECK (status IN ('PLANNED','APPLIED','ROLLED_BACK','FAILED'))
);

CREATE TABLE IF NOT EXISTS promotion_batch_items (
    batch_id            TEXT NOT NULL REFERENCES promotion_batches(id) ON DELETE CASCADE,
    staging_id          TEXT NOT NULL REFERENCES staging_artifacts(id) ON DELETE RESTRICT,
    final_artifact_id   TEXT,                    -- id written to security_artifacts
    source_staging_hash TEXT NOT NULL,           -- staging content_hash captured at plan time
    action              TEXT NOT NULL,           -- INSERT / UPDATE / SKIP
    mappings_created    INTEGER NOT NULL DEFAULT 0,
    tags_created        INTEGER NOT NULL DEFAULT 0,
    relationships_created INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (batch_id, staging_id),
    CHECK (action IN ('INSERT','UPDATE','SKIP'))
);
CREATE INDEX IF NOT EXISTS idx_pbi_final ON promotion_batch_items(final_artifact_id);

CREATE TABLE IF NOT EXISTS promotion_audit_log (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id TEXT,
    event    TEXT NOT NULL,                      -- PLAN/APPLY/APPLY_SKIP/ROLLBACK/REJECT/ERROR
    detail   TEXT,
    at       TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_pal_batch ON promotion_audit_log(batch_id, at);
