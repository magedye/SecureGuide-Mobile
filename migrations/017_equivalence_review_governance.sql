-- ============================================================================
-- SecureGuide — Migration 017: Equivalence decision review governance
-- ----------------------------------------------------------------------------
-- Adds accountable, reviewable metadata to non-destructive equivalence groups.
-- Group decisions remain reference/curation data; no profile state is stored.
-- ============================================================================

PRAGMA foreign_keys = ON;

ALTER TABLE equivalence_groups ADD COLUMN decision_method TEXT
    CHECK (decision_method IS NULL OR decision_method IN
        ('AI_CONSERVATIVE','EXACT_MATCH','AI_CONSERVATIVE+EXACT_MATCH','MANUAL'));
ALTER TABLE equivalence_groups ADD COLUMN decision_confidence REAL
    CHECK (decision_confidence IS NULL OR
        (decision_confidence >= 0.0 AND decision_confidence <= 1.0));
ALTER TABLE equivalence_groups ADD COLUMN decision_rationale TEXT;
ALTER TABLE equivalence_groups ADD COLUMN ai_review_status TEXT NOT NULL
    DEFAULT 'AIR-HUMAN-REVIEW'
    CHECK (ai_review_status IN
        ('AIR-AUTO-ACCEPTED','AIR-HUMAN-REVIEW','AIR-HUMAN-APPROVED','AIR-HUMAN-REJECTED'));
ALTER TABLE equivalence_groups ADD COLUMN requires_human_review INTEGER NOT NULL
    DEFAULT 1 CHECK (requires_human_review IN (0,1));
ALTER TABLE equivalence_groups ADD COLUMN reviewed_by TEXT;
ALTER TABLE equivalence_groups ADD COLUMN reviewed_at TEXT;

CREATE INDEX IF NOT EXISTS idx_equivalence_review
    ON equivalence_groups(ai_review_status, requires_human_review);

INSERT OR IGNORE INTO schema_migrations (version, description) VALUES
    ('017', 'Equivalence decision rationale, confidence, and human-review governance');
