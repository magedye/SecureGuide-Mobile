-- ============================================================================
-- SecureGuide - Migration 035: Semantic reconciliation closure evidence
-- ----------------------------------------------------------------------------
-- Adds normalized, source-preserving evidence for non-lineage reconciliation
-- outcomes and individually classified deferred records. Existing raw rows,
-- final lineage, aliases, and profile/operational data remain untouched.
-- ============================================================================

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS raw_artifact_deferred_reasons (
    raw_artifact_id TEXT PRIMARY KEY
        REFERENCES raw_artifacts(id) ON DELETE RESTRICT,
    reason_code TEXT NOT NULL CHECK (reason_code IN (
        'INSUFFICIENT_AUTHORITATIVE_CONTEXT',
        'ATOMICITY_AMBIGUITY',
        'AUTHORITATIVE_CONFLICT',
        'UNRESOLVED_SEMANTIC_BOUNDARY',
        'MISSING_SOURCE_METADATA'
    )),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS raw_artifact_reconciliation_links (
    raw_artifact_id TEXT NOT NULL
        REFERENCES raw_artifacts(id) ON DELETE RESTRICT,
    link_index INTEGER NOT NULL CHECK (link_index >= 0),
    disposition TEXT NOT NULL CHECK (disposition IN (
        'DUPLICATE', 'CROSSWALK_ONLY', 'RELATION_ONLY'
    )),
    target_artifact_id TEXT REFERENCES security_artifacts(id) ON DELETE RESTRICT,
    target_raw_artifact_id TEXT REFERENCES raw_artifacts(id) ON DELETE RESTRICT,
    mapping_strength TEXT NOT NULL CHECK (mapping_strength IN (
        'DIRECT', 'INDIRECT', 'PARTIAL', 'INFORMATIVE'
    )),
    rationale TEXT NOT NULL CHECK (length(trim(rationale)) > 0),
    evidence_method TEXT NOT NULL CHECK (length(trim(evidence_method)) > 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (raw_artifact_id, link_index),
    CHECK (
        (target_artifact_id IS NOT NULL AND target_raw_artifact_id IS NULL)
        OR (target_artifact_id IS NULL AND target_raw_artifact_id IS NOT NULL)
    ),
    CHECK (mapping_strength = 'DIRECT' OR length(trim(rationale)) > 0)
);
CREATE INDEX IF NOT EXISTS idx_reconciliation_links_artifact
    ON raw_artifact_reconciliation_links(target_artifact_id, raw_artifact_id);
CREATE INDEX IF NOT EXISTS idx_reconciliation_links_raw_target
    ON raw_artifact_reconciliation_links(target_raw_artifact_id, raw_artifact_id);

INSERT OR IGNORE INTO schema_migrations(version, description)
VALUES ('035', 'Semantic reconciliation links and deferred reason evidence');
