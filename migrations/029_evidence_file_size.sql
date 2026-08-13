-- ============================================================================
-- SecureGuide — Migration 029: Evidence File Size
-- ----------------------------------------------------------------------------
-- Adds bounded local-file metadata alongside the existing content_hash. The
-- file remains profile-specific and external to SQLite; no binary is copied
-- into the Master Catalog or an operational JSON field.
-- ============================================================================

PRAGMA foreign_keys = ON;

INSERT OR IGNORE INTO schema_migrations(version,description)
VALUES ('029','Store non-negative local evidence file sizes');

ALTER TABLE profile_evidence ADD COLUMN file_size INTEGER
    CHECK (file_size IS NULL OR file_size>=0);
