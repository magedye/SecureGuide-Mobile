-- ============================================================================
-- SecureGuide — Migration 026: Performance Indexes
-- ============================================================================

PRAGMA foreign_keys = ON;

INSERT OR IGNORE INTO schema_migrations (version, description)
VALUES ('026', 'Add strategic indexes for catalog search performance');

CREATE INDEX IF NOT EXISTS idx_artifacts_source ON security_artifacts(source);
