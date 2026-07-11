-- ============================================================================
-- SecureGuide — Migration 004: Quality & Curation Layer
-- ----------------------------------------------------------------------------
-- Implements the pipeline of SECUREGUIDE_AI_AGENT_BRIEF.md:
--   raw_artifacts -> staging/curation -> English canonical draft ->
--   USACM+SDT classification -> similarity/merge -> review -> approved
--   security_artifacts.
-- Light-touch (flexibility before enterprise complexity). English-first.
-- Consolidation vocabulary follows docs/CONSOLIDATION_POLICY.md.
-- Nothing here is a global operational state; the catalog stays reference-only.
-- ============================================================================

PRAGMA foreign_keys = ON;

-- ---- Migration bookkeeping ----
CREATE TABLE IF NOT EXISTS schema_migrations (
    version     TEXT PRIMARY KEY,
    description TEXT,
    applied_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
INSERT OR IGNORE INTO schema_migrations (version, description) VALUES
    ('001', 'Core schema: intake + master catalog + child tables + templates + profiles'),
    ('002', 'Assets, threat indicators, embeddings & deduplication'),
    ('003', 'Reference data: per-list bilingual lookup tables (lk_*)'),
    ('004', 'Quality & Curation layer: staging, batches, consolidation decisions, lessons');

-- ---- Idempotent batch processing + pre-change snapshot marker ----
CREATE TABLE IF NOT EXISTS curation_batches (
    id                TEXT PRIMARY KEY,
    source_catalog_id TEXT REFERENCES source_catalogs(id) ON DELETE SET NULL,
    name              TEXT,
    status            TEXT NOT NULL DEFAULT 'OPEN',
    item_count        INTEGER NOT NULL DEFAULT 0,
    snapshot_ref      TEXT,                    -- pointer to a pre-batch DB snapshot/backup
    notes             TEXT,
    created_at        TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at      TEXT,
    CHECK (status IN ('OPEN','PROCESSING','COMPLETED','ROLLED_BACK')),
    CHECK (item_count >= 0)
);

-- ---- Staging: the working draft between raw and approved catalog ----
-- Proposed child collections are transient JSON here (normalized on promotion);
-- the no-JSON-array rule applies to security_artifacts, not to staging.
CREATE TABLE IF NOT EXISTS staging_artifacts (
    id                        TEXT PRIMARY KEY,
    batch_id                  TEXT REFERENCES curation_batches(id) ON DELETE SET NULL,
    raw_artifact_id           TEXT REFERENCES raw_artifacts(id) ON DELETE SET NULL,

    -- English canonical draft (AUTHORING_POLICY, English-first)
    title_en                  TEXT,
    definition_short_en       TEXT,
    definition_full_en        TEXT,
    objective_en              TEXT,
    canonical_statement       TEXT,

    -- proposed classification (USACM + SDT) — nullable until classified
    proposed_type             TEXT,
    proposed_abstraction_level TEXT,
    proposed_primary_domain   TEXT,
    proposed_sub_domain       TEXT,
    proposed_obligation_level TEXT,

    -- AI accountability
    classification_confidence REAL,
    classification_rationale  TEXT,
    rejected_alternatives     TEXT,            -- JSON
    requires_human_review     INTEGER NOT NULL DEFAULT 0,

    -- proposed child collections (transient JSON; normalized on promotion)
    proposed_tags_json          TEXT,
    proposed_mappings_json      TEXT,
    proposed_relationships_json TEXT,

    -- consolidation (see CONSOLIDATION_POLICY.md)
    canonical_group_id        TEXT REFERENCES equivalence_groups(id) ON DELETE SET NULL,
    merge_action              TEXT,            -- one of the 6 consolidation decisions

    -- curation workflow + quality (NOT a risk score)
    curation_status           TEXT NOT NULL DEFAULT 'DRAFT',
    quality_score             INTEGER,         -- 0-100 completeness/validation score
    reviewer                  TEXT,
    review_notes              TEXT,

    -- lineage to the promoted catalog record
    promoted_artifact_id      TEXT REFERENCES security_artifacts(id) ON DELETE SET NULL,

    created_at                TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at                TEXT NOT NULL DEFAULT (datetime('now')),

    CHECK (requires_human_review IN (0,1)),
    CHECK (quality_score IS NULL OR (quality_score >= 0 AND quality_score <= 100)),
    CHECK (classification_confidence IS NULL OR (classification_confidence >= 0 AND classification_confidence <= 1)),
    CHECK (curation_status IN ('DRAFT','CLASSIFIED','DEDUP_REVIEW','READY','APPROVED','REJECTED','NEEDS_REVIEW')),
    CHECK (merge_action IS NULL OR merge_action IN ('CANONICALIZE','EQUIVALENCE_GROUP','CROSSWALK_ONLY','RELATE_ONLY','KEEP_SEPARATE','DEPRECATE_DERIVED')),
    CHECK (proposed_type IS NULL OR proposed_type IN ('ART-REQ','ART-OBJ','ART-PRI','ART-POL','ART-STD','ART-CTR','ART-CTE','ART-PRO','ART-PRC','ART-PRG','ART-PLN','ART-TSK','ART-CFG','ART-RUL','ART-EVD','ART-MET','ART-EXC','ART-RSK','ART-AST','ART-THR','ART-VUL','ART-OWN')),
    CHECK (proposed_abstraction_level IS NULL OR proposed_abstraction_level IN ('ABS-GOV','ABS-RIS','ABS-POL','ABS-CTR','ABS-PRO','ABS-TEC','ABS-EVM')),
    CHECK (proposed_primary_domain IS NULL OR proposed_primary_domain IN ('SD-01','SD-02','SD-03','SD-04','SD-05','SD-06','SD-07','SD-08')),
    CHECK (proposed_sub_domain IS NULL OR proposed_sub_domain GLOB 'SD-0[1-8].0[1-5]'),
    CHECK (proposed_sub_domain IS NULL OR proposed_primary_domain IS NULL OR substr(proposed_sub_domain,1,5) = proposed_primary_domain),
    CHECK (proposed_obligation_level IS NULL OR proposed_obligation_level IN ('OBL-MND','OBL-CON','OBL-REC','OBL-OPT'))
);
CREATE INDEX IF NOT EXISTS idx_staging_status ON staging_artifacts(curation_status);
CREATE INDEX IF NOT EXISTS idx_staging_batch ON staging_artifacts(batch_id);
CREATE INDEX IF NOT EXISTS idx_staging_raw ON staging_artifacts(raw_artifact_id);
CREATE INDEX IF NOT EXISTS idx_staging_group ON staging_artifacts(canonical_group_id);
CREATE INDEX IF NOT EXISTS idx_staging_review ON staging_artifacts(requires_human_review, classification_confidence);

-- ---- Consolidation decisions (authoritative 6-value vocabulary) ----
CREATE TABLE IF NOT EXISTS consolidation_decisions (
    id                    TEXT PRIMARY KEY,
    decision              TEXT NOT NULL,
    canonical_artifact_id TEXT REFERENCES security_artifacts(id) ON DELETE SET NULL,
    equivalence_group_id  TEXT REFERENCES equivalence_groups(id) ON DELETE SET NULL,
    rationale             TEXT,
    decided_by            TEXT,
    decided_at            TEXT NOT NULL DEFAULT (datetime('now')),
    CHECK (decision IN ('CANONICALIZE','EQUIVALENCE_GROUP','CROSSWALK_ONLY','RELATE_ONLY','KEEP_SEPARATE','DEPRECATE_DERIVED'))
);

CREATE TABLE IF NOT EXISTS consolidation_members (
    decision_id TEXT NOT NULL REFERENCES consolidation_decisions(id) ON DELETE CASCADE,
    artifact_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    role        TEXT NOT NULL DEFAULT 'MEMBER',
    PRIMARY KEY (decision_id, artifact_id),
    CHECK (role IN ('CANONICAL','MEMBER','SOURCE'))
);

-- ---- Lessons learned (lightweight; CONSOLIDATION_POLICY §9) ----
CREATE TABLE IF NOT EXISTS curation_lessons (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    lesson_type TEXT NOT NULL,
    pattern     TEXT NOT NULL,
    example     TEXT,
    action      TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    CHECK (lesson_type IN ('CLASSIFICATION_PATTERN','MERGE_PATTERN','COMMON_ERROR','TIE_BREAKER','OTHER'))
);
