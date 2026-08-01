-- ============================================================================
-- SecureGuide — Migration 025: Operational View Overrides
-- ----------------------------------------------------------------------------
-- Expose raw priority_override and review_frequency_override in the
-- v_profile_operational_items view for list and UI consistency.
-- ============================================================================

PRAGMA foreign_keys = ON;

INSERT OR IGNORE INTO schema_migrations (version, description)
VALUES ('025', 'Expose raw priority and review overrides in operational items view');

DROP VIEW IF EXISTS v_profile_operational_items;
CREATE VIEW v_profile_operational_items AS
SELECT pa.id AS profile_artifact_id,
       pa.profile_id,
       pa.artifact_id,
       a.type,
       a.title_en,
       a.title_ar,
       a.definition_short_en,
       a.definition_short_ar,
       a.primary_domain,
       a.sub_domain,
       a.source,
       a.source_document,
       a.obligation_level,
       a.testability,
       COALESCE(pa.priority_override,pa.template_priority_default,a.priority) AS effective_priority,
       COALESCE(pa.review_frequency_override,pa.template_review_frequency_default,a.review_frequency) AS effective_review_frequency,
       pa.priority_override,
       pa.review_frequency_override,
       pa.inclusion_status,
       pa.implementation_status,
       pa.verification_status,
       pa.effectiveness,
       pa.exception_status,
       pa.active_exception_id,
       pa.current_maturity_level,
       pa.assigned_owner,
       pa.due_date,
       pa.notes,
       pa.created_at AS selected_at,
       pa.updated_at,
       (SELECT COUNT(*) FROM profile_evidence e
         WHERE e.profile_artifact_id=pa.id) AS evidence_count,
       (SELECT MAX(x.assessment_date) FROM profile_assessments x
         WHERE x.profile_artifact_id=pa.id) AS last_assessment_at,
       (SELECT COUNT(*) FROM profile_artifact_origins o
         WHERE o.profile_artifact_id=pa.id) AS origin_count
  FROM profile_artifacts pa
  JOIN security_artifacts a ON a.id=pa.artifact_id
 WHERE a.is_active=1;
