-- ============================================================================
-- SecureGuide — Migration 028: Persistent Application Locale
-- ----------------------------------------------------------------------------
-- Stores the explicit Arabic/English preference beside the singleton active
-- profile context. This is application state, never Master Catalog metadata.
-- ============================================================================

PRAGMA foreign_keys = ON;

INSERT OR IGNORE INTO schema_migrations(version,description)
VALUES ('028','Persist the controlled Arabic or English application locale');

ALTER TABLE application_state ADD COLUMN locale TEXT NOT NULL DEFAULT 'ar'
    CHECK (locale IN ('ar','en'));

CREATE TRIGGER trg_application_state_locale_touch
AFTER UPDATE OF locale ON application_state
WHEN NEW.updated_at = OLD.updated_at
BEGIN
    UPDATE application_state SET updated_at=datetime('now') WHERE singleton_id=1;
END;
