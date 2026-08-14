-- ============================================================================
-- SecureGuide - Migration 034: Neutral catalog identity and durable aliases
-- ----------------------------------------------------------------------------
-- Historical migrations retain their original names as immutable evidence.
-- This forward migration removes the former product identity from the active
-- schema while preserving every row and adds explicit old-to-current IDs for
-- transactional installed-catalog upgrades.
-- ============================================================================

PRAGMA foreign_keys = ON;

ALTER TABLE amani_domain_alias RENAME TO legacy_domain_alias;
ALTER TABLE legacy_domain_alias RENAME COLUMN amani_key TO legacy_key;

ALTER TABLE amani_threat_alias RENAME TO legacy_threat_alias;
ALTER TABLE legacy_threat_alias RENAME COLUMN amani_key TO legacy_key;

DROP INDEX IF EXISTS idx_amani_prov_amaniid;
ALTER TABLE catalog_amani_provenance RENAME TO catalog_legacy_provenance;
ALTER TABLE catalog_legacy_provenance RENAME COLUMN amani_id TO legacy_id;
ALTER TABLE catalog_legacy_provenance RENAME COLUMN amani_domain TO legacy_domain;
ALTER TABLE catalog_legacy_provenance RENAME COLUMN amani_sub TO legacy_sub;
CREATE INDEX IF NOT EXISTS idx_legacy_prov_legacy_id
    ON catalog_legacy_provenance(legacy_id);

ALTER TABLE catalog_amani_assets RENAME TO catalog_legacy_assets;
ALTER TABLE staging_artifacts
    RENAME COLUMN proposed_amani_provenance_json TO proposed_legacy_provenance_json;

CREATE TABLE IF NOT EXISTS catalog_artifact_id_aliases (
    old_artifact_id TEXT PRIMARY KEY,
    artifact_id     TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    reason          TEXT NOT NULL CHECK (length(trim(reason)) > 0),
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (old_artifact_id <> artifact_id)
);
CREATE INDEX IF NOT EXISTS idx_catalog_artifact_alias_target
    ON catalog_artifact_id_aliases(artifact_id);

INSERT OR IGNORE INTO schema_migrations(version, description)
VALUES ('034', 'Neutral active catalog identity and durable artifact ID aliases');
