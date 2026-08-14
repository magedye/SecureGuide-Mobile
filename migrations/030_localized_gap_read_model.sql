-- ============================================================================
-- SecureGuide — Migration 030: Localized Gap Read Model
-- ----------------------------------------------------------------------------
-- Add the Arabic catalog title to the profile-scoped gap view. This is a
-- read-model-only change: reference content stays in security_artifacts and
-- operational state stays in profile_artifacts.
--
-- Recovery: reapply the v_gap_analysis definition from migration 021. No
-- stored data is changed by this migration.
-- ============================================================================

PRAGMA foreign_keys = ON;

INSERT OR IGNORE INTO schema_migrations (version, description)
VALUES ('030', 'Expose Arabic artifact titles in the profile gap read model');

DROP VIEW IF EXISTS v_gap_analysis;
CREATE VIEW v_gap_analysis AS
SELECT pa.profile_id,
       pa.artifact_id,
       a.title_en,
       a.title_ar,
       a.primary_domain,
       a.sub_domain,
       COALESCE(pa.priority_override,pa.template_priority_default,a.priority) AS priority,
       pa.implementation_status,
       pa.verification_status,
       pa.effectiveness,
       pa.exception_status,
       pa.assigned_owner,
       pa.due_date
  FROM profile_artifacts pa
  JOIN security_artifacts a ON a.id=pa.artifact_id
 WHERE a.is_active=1
   AND pa.implementation_status<>'STS-FULL'
   AND pa.exception_status NOT IN ('EXC-NOT-APPLICABLE','EXC-UNAVAILABLE');
