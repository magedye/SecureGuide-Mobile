-- SecureGuide migration 027: non-destructive enterprise-profile archival.
-- Operational history remains intact; archived profiles cannot become active.

ALTER TABLE enterprise_profiles
    ADD COLUMN archived_at TEXT
    CHECK (archived_at IS NULL OR datetime(archived_at) IS NOT NULL);

CREATE INDEX idx_enterprise_profiles_archived
    ON enterprise_profiles(archived_at, created_at DESC);

CREATE TRIGGER trg_application_state_reject_archived_profile
BEFORE UPDATE OF active_profile_id ON application_state
WHEN NEW.active_profile_id IS NOT NULL
 AND NOT EXISTS (
     SELECT 1
       FROM enterprise_profiles p
      WHERE p.id=NEW.active_profile_id
        AND p.archived_at IS NULL
 )
BEGIN
    SELECT RAISE(ABORT, 'active profile must exist and not be archived');
END;

CREATE TRIGGER trg_enterprise_profile_archive_deactivate
AFTER UPDATE OF archived_at ON enterprise_profiles
WHEN OLD.archived_at IS NULL
 AND NEW.archived_at IS NOT NULL
 AND (SELECT active_profile_id FROM application_state WHERE singleton_id=1)=NEW.id
BEGIN
    UPDATE application_state
       SET active_profile_id=NULL
     WHERE singleton_id=1;
END;

INSERT INTO schema_migrations(version, description)
VALUES ('027', 'Non-destructive enterprise-profile archival');
