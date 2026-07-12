-- ============================================================================
-- SecureGuide — Migration 014: Staging columns for SADP-conformant promotion
-- ----------------------------------------------------------------------------
-- Additive staging fields so authored/imported content flows through promote.py
-- without tags: the intrinsic baseline priority (PRI-*, preserved losslessly from
-- sources like amani), and amani provenance that used to ride on tags (moved to
-- the typed catalog_amani_provenance / catalog_amani_assets tables at promotion).
-- ============================================================================

INSERT OR IGNORE INTO schema_migrations (version, description)
VALUES ('014', 'Staging: proposed_priority + proposed_amani_provenance_json (SADP no-tags promotion)');

ALTER TABLE staging_artifacts ADD COLUMN proposed_priority TEXT;               -- PRI-* baseline priority
ALTER TABLE staging_artifacts ADD COLUMN proposed_amani_provenance_json TEXT;  -- {amani_id, amani_domain, amani_sub, assets:[...]}
