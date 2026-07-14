-- ============================================================================
-- SecureGuide — Migration 022: Template Application Provenance
-- ----------------------------------------------------------------------------
-- Links every template-origin selection to the exact profile/template/version
-- application event. This preserves a reproducible item snapshot when the same
-- template is applied again after its version or membership changes.
-- ============================================================================

PRAGMA foreign_keys = ON;

INSERT OR IGNORE INTO schema_migrations (version, description)
VALUES ('022', 'Link template item origins to exact profile template application versions');

ALTER TABLE profile_artifact_origins ADD COLUMN profile_template_id TEXT
    REFERENCES profile_templates(id) ON DELETE RESTRICT;

-- Best-effort backfill for migration-021 rows. Unmatched legacy rows remain
-- visible in the governance view and can be resolved without deleting lineage.
UPDATE profile_artifact_origins
   SET profile_template_id=(
       SELECT pt.id
         FROM profile_artifacts pa
         JOIN template_items ti ON ti.id=profile_artifact_origins.template_item_id
         JOIN profile_templates pt
           ON pt.profile_id=pa.profile_id
          AND pt.template_id=ti.template_id
          AND profile_artifact_origins.origin_reference=
              pt.template_id || '@' || pt.template_version
        WHERE pa.id=profile_artifact_origins.profile_artifact_id
        ORDER BY pt.applied_at,pt.id
        LIMIT 1
   )
 WHERE origin_type='TEMPLATE' AND profile_template_id IS NULL;

DROP INDEX IF EXISTS uq_profile_artifact_template_origin;
CREATE UNIQUE INDEX uq_profile_artifact_template_version_origin
    ON profile_artifact_origins(profile_artifact_id,profile_template_id,template_item_id)
    WHERE origin_type='TEMPLATE';

CREATE INDEX idx_profile_artifact_origins_template_application
    ON profile_artifact_origins(profile_template_id,template_item_id);

DROP TRIGGER IF EXISTS trg_profile_artifact_origin_validate_insert;
DROP TRIGGER IF EXISTS trg_profile_artifact_origin_validate_update;

CREATE TRIGGER trg_profile_artifact_origin_validate_insert
BEFORE INSERT ON profile_artifact_origins
BEGIN
    SELECT CASE
      WHEN NEW.origin_type='TEMPLATE' AND
           (NEW.template_item_id IS NULL OR NEW.profile_template_id IS NULL)
      THEN RAISE(ABORT, 'template origin requires item and template application')
    END;
    SELECT CASE
      WHEN NEW.origin_type<>'TEMPLATE' AND NEW.profile_template_id IS NOT NULL
      THEN RAISE(ABORT, 'non-template origin cannot reference template application')
    END;
    SELECT CASE
      WHEN NEW.origin_type='TEMPLATE' AND NOT EXISTS (
          SELECT 1
            FROM profile_artifacts pa
            JOIN template_items ti ON ti.id=NEW.template_item_id
            JOIN profile_templates pt ON pt.id=NEW.profile_template_id
           WHERE pa.id=NEW.profile_artifact_id
             AND pa.artifact_id=ti.artifact_id
             AND pa.profile_id=pt.profile_id
             AND ti.template_id=pt.template_id
      )
      THEN RAISE(ABORT, 'template origin must match profile, artifact, and application')
    END;
END;

CREATE TRIGGER trg_profile_artifact_origin_validate_update
BEFORE UPDATE OF profile_artifact_id,origin_type,template_item_id,profile_template_id
ON profile_artifact_origins
BEGIN
    SELECT CASE
      WHEN NEW.origin_type='TEMPLATE' AND
           (NEW.template_item_id IS NULL OR NEW.profile_template_id IS NULL)
      THEN RAISE(ABORT, 'template origin requires item and template application')
    END;
    SELECT CASE
      WHEN NEW.origin_type<>'TEMPLATE' AND NEW.profile_template_id IS NOT NULL
      THEN RAISE(ABORT, 'non-template origin cannot reference template application')
    END;
    SELECT CASE
      WHEN NEW.origin_type='TEMPLATE' AND NOT EXISTS (
          SELECT 1
            FROM profile_artifacts pa
            JOIN template_items ti ON ti.id=NEW.template_item_id
            JOIN profile_templates pt ON pt.id=NEW.profile_template_id
           WHERE pa.id=NEW.profile_artifact_id
             AND pa.artifact_id=ti.artifact_id
             AND pa.profile_id=pt.profile_id
             AND ti.template_id=pt.template_id
      )
      THEN RAISE(ABORT, 'template origin must match profile, artifact, and application')
    END;
END;

CREATE VIEW v_profile_origin_governance_issues AS
SELECT o.id AS origin_id,
       pa.profile_id,
       pa.artifact_id,
       o.origin_type,
       o.template_item_id,
       o.profile_template_id,
       CASE
         WHEN o.origin_type='TEMPLATE' AND o.profile_template_id IS NULL
           THEN 'MISSING_TEMPLATE_APPLICATION'
         WHEN o.origin_type<>'TEMPLATE' AND o.profile_template_id IS NOT NULL
           THEN 'NON_TEMPLATE_WITH_APPLICATION'
         WHEN o.origin_type='TEMPLATE' AND
              (ti.id IS NULL OR pt.id IS NULL OR ti.artifact_id<>pa.artifact_id
               OR pt.profile_id<>pa.profile_id OR pt.template_id<>ti.template_id)
           THEN 'TEMPLATE_ORIGIN_MISMATCH'
       END AS issue_code
  FROM profile_artifact_origins o
  JOIN profile_artifacts pa ON pa.id=o.profile_artifact_id
  LEFT JOIN template_items ti ON ti.id=o.template_item_id
  LEFT JOIN profile_templates pt ON pt.id=o.profile_template_id
 WHERE (o.origin_type='TEMPLATE' AND
        (o.profile_template_id IS NULL OR ti.id IS NULL OR pt.id IS NULL
         OR ti.artifact_id<>pa.artifact_id OR pt.profile_id<>pa.profile_id
         OR pt.template_id<>ti.template_id))
    OR (o.origin_type<>'TEMPLATE' AND o.profile_template_id IS NOT NULL);
