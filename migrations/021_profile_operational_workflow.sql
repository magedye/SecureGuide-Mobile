-- ============================================================================
-- SecureGuide — Migration 021: Profile Operational Workflow
-- ----------------------------------------------------------------------------
-- Additive operational infrastructure for the offline-first profile workflow:
-- persistent active-profile context, normalized selection provenance, template
-- defaults distinct from user overrides, evidence/assessment integrity, and
-- profile-aware read models. No Master Catalog definition is copied or changed.
--
-- Recovery: restore the pre-migration database backup. SQLite cannot safely
-- drop added columns in place on every supported embedded version.
-- ============================================================================

PRAGMA foreign_keys = ON;

INSERT OR IGNORE INTO schema_migrations (version, description)
VALUES ('021', 'Active profile context, selection provenance, operational integrity, and profile read models');

-- One offline installation has one current profile context. The service layer
-- may still pass an explicit profile_id; this row is only the persisted default.
CREATE TABLE application_state (
    singleton_id       INTEGER PRIMARY KEY CHECK (singleton_id = 1),
    active_profile_id  TEXT REFERENCES enterprise_profiles(id) ON DELETE SET NULL,
    updated_at         TEXT NOT NULL DEFAULT (datetime('now'))
);

INSERT OR IGNORE INTO application_state(singleton_id) VALUES (1);

CREATE TRIGGER trg_application_state_no_delete
BEFORE DELETE ON application_state
BEGIN
    SELECT RAISE(ABORT, 'application_state singleton cannot be deleted');
END;

CREATE TRIGGER trg_application_state_singleton_id
BEFORE UPDATE OF singleton_id ON application_state
WHEN NEW.singleton_id <> 1
BEGIN
    SELECT RAISE(ABORT, 'application_state singleton_id must remain 1');
END;

CREATE TRIGGER trg_application_state_touch
AFTER UPDATE OF active_profile_id ON application_state
WHEN NEW.updated_at = OLD.updated_at
BEGIN
    UPDATE application_state SET updated_at=datetime('now') WHERE singleton_id=1;
END;

-- Template-provided defaults remain distinct from explicit organization-level
-- overrides. This prevents reapplying a template from overwriting a user choice.
ALTER TABLE profile_artifacts ADD COLUMN template_priority_default TEXT
    CHECK (template_priority_default IS NULL OR template_priority_default IN
           ('PRI-CRITICAL','PRI-HIGH','PRI-MEDIUM','PRI-LOW'));
ALTER TABLE profile_artifacts ADD COLUMN template_review_frequency_default TEXT
    CHECK (template_review_frequency_default IS NULL OR template_review_frequency_default IN
           ('DAILY','WEEKLY','MONTHLY','QUARTERLY','SEMI-ANNUAL','ANNUAL','BIENNIAL','AD-HOC','CONTINUOUS'));
ALTER TABLE profile_artifacts ADD COLUMN review_frequency_override TEXT
    CHECK (review_frequency_override IS NULL OR review_frequency_override IN
           ('DAILY','WEEKLY','MONTHLY','QUARTERLY','SEMI-ANNUAL','ANNUAL','BIENNIAL','AD-HOC','CONTINUOUS'));

-- Evidence remains external/profile-specific, but carries enough metadata for
-- offline integrity and later document-management integrations.
ALTER TABLE profile_evidence ADD COLUMN title TEXT;
ALTER TABLE profile_evidence ADD COLUMN collected_by TEXT;
ALTER TABLE profile_evidence ADD COLUMN content_hash TEXT
    CHECK (content_hash IS NULL OR (length(content_hash)=64 AND content_hash NOT GLOB '*[^0-9A-Fa-f]*'));
ALTER TABLE profile_evidence ADD COLUMN mime_type TEXT;

CREATE INDEX idx_prof_art_profile_priority_due
    ON profile_artifacts(profile_id, priority_override, template_priority_default, due_date);
CREATE INDEX idx_prof_assess_latest
    ON profile_assessments(profile_artifact_id, assessment_date DESC, id);
CREATE INDEX idx_prof_evidence_assessment
    ON profile_evidence(assessment_id);

-- A profile may consume multiple templates and multiple versions over time.
-- This is application history; templates remain reference selections.
CREATE TABLE profile_templates (
    id                TEXT PRIMARY KEY,
    profile_id        TEXT NOT NULL REFERENCES enterprise_profiles(id) ON DELETE CASCADE,
    template_id       TEXT NOT NULL REFERENCES templates(id) ON DELETE RESTRICT,
    template_version  TEXT NOT NULL,
    applied_by        TEXT NOT NULL,
    applied_at        TEXT NOT NULL DEFAULT (datetime('now')),
    note              TEXT,
    UNIQUE (profile_id, template_id, template_version)
);

CREATE INDEX idx_profile_templates_profile
    ON profile_templates(profile_id, applied_at DESC);

-- Selection provenance is repeatable and normalized. One profile_artifact can
-- be selected manually and also be required by several templates without
-- cloning the security_artifact definition.
CREATE TABLE profile_artifact_origins (
    id                   TEXT PRIMARY KEY,
    profile_artifact_id  TEXT NOT NULL REFERENCES profile_artifacts(id) ON DELETE CASCADE,
    origin_type          TEXT NOT NULL,
    template_item_id     TEXT REFERENCES template_items(id) ON DELETE RESTRICT,
    origin_reference     TEXT,
    inclusion_status     TEXT,
    selection_reason     TEXT,
    selected_by          TEXT NOT NULL,
    selected_at          TEXT NOT NULL DEFAULT (datetime('now')),
    CHECK (origin_type IN ('MANUAL','TEMPLATE','IMPORT','RECOMMENDATION')),
    CHECK (inclusion_status IS NULL OR inclusion_status IN
           ('MANDATORY','RECOMMENDED','OPTIONAL','CONDITIONAL')),
    CHECK ((origin_type='TEMPLATE' AND template_item_id IS NOT NULL)
        OR (origin_type<>'TEMPLATE' AND template_item_id IS NULL))
);

CREATE UNIQUE INDEX uq_profile_artifact_template_origin
    ON profile_artifact_origins(profile_artifact_id, template_item_id)
    WHERE origin_type='TEMPLATE';
CREATE UNIQUE INDEX uq_profile_artifact_manual_origin
    ON profile_artifact_origins(profile_artifact_id)
    WHERE origin_type='MANUAL';
CREATE INDEX idx_profile_artifact_origins_pa
    ON profile_artifact_origins(profile_artifact_id, selected_at DESC);

CREATE TRIGGER trg_profile_artifact_origin_validate_insert
BEFORE INSERT ON profile_artifact_origins
WHEN NEW.origin_type='TEMPLATE'
BEGIN
    SELECT CASE WHEN NOT EXISTS (
        SELECT 1
          FROM profile_artifacts pa
          JOIN template_items ti ON ti.id=NEW.template_item_id
         WHERE pa.id=NEW.profile_artifact_id
           AND pa.artifact_id=ti.artifact_id
    ) THEN RAISE(ABORT, 'template origin artifact must match profile artifact') END;
END;

CREATE TRIGGER trg_profile_artifact_origin_validate_update
BEFORE UPDATE OF profile_artifact_id, origin_type, template_item_id ON profile_artifact_origins
WHEN NEW.origin_type='TEMPLATE'
BEGIN
    SELECT CASE WHEN NOT EXISTS (
        SELECT 1
          FROM profile_artifacts pa
          JOIN template_items ti ON ti.id=NEW.template_item_id
         WHERE pa.id=NEW.profile_artifact_id
           AND pa.artifact_id=ti.artifact_id
    ) THEN RAISE(ABORT, 'template origin artifact must match profile artifact') END;
END;

-- An evidence row may point only to an assessment of the same profile artifact.
CREATE TRIGGER trg_profile_evidence_assessment_insert
BEFORE INSERT ON profile_evidence
WHEN NEW.assessment_id IS NOT NULL
BEGIN
    SELECT CASE WHEN NOT EXISTS (
        SELECT 1 FROM profile_assessments a
         WHERE a.id=NEW.assessment_id
           AND a.profile_artifact_id=NEW.profile_artifact_id
    ) THEN RAISE(ABORT, 'evidence assessment must belong to the same profile artifact') END;
END;

CREATE TRIGGER trg_profile_evidence_assessment_update
BEFORE UPDATE OF profile_artifact_id, assessment_id ON profile_evidence
WHEN NEW.assessment_id IS NOT NULL
BEGIN
    SELECT CASE WHEN NOT EXISTS (
        SELECT 1 FROM profile_assessments a
         WHERE a.id=NEW.assessment_id
           AND a.profile_artifact_id=NEW.profile_artifact_id
    ) THEN RAISE(ABORT, 'evidence assessment must belong to the same profile artifact') END;
END;

-- Assessment rows are historical snapshots. Corrections create a new event.
CREATE TRIGGER trg_profile_assessment_immutable_update
BEFORE UPDATE ON profile_assessments
BEGIN
    SELECT RAISE(ABORT, 'profile assessment snapshots are immutable');
END;

-- Keep operational timestamps reliable even when a repository update omits it.
CREATE TRIGGER trg_profile_artifact_touch
AFTER UPDATE OF inclusion_status, priority_override, template_priority_default,
                template_review_frequency_default, review_frequency_override,
                implementation_status, verification_status, effectiveness,
                current_maturity_level, assigned_owner, due_date, notes
ON profile_artifacts
WHEN NEW.updated_at = OLD.updated_at
BEGIN
    UPDATE profile_artifacts SET updated_at=datetime('now') WHERE id=NEW.id;
END;

DROP VIEW IF EXISTS v_active_profile_context;
CREATE VIEW v_active_profile_context AS
SELECT s.active_profile_id AS profile_id,
       p.name AS profile_name,
       p.profile_kind,
       s.updated_at AS selected_at
  FROM application_state s
  LEFT JOIN enterprise_profiles p ON p.id=s.active_profile_id
 WHERE s.singleton_id=1;

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

-- Replace the older rollup with exception-aware applicable-item counts while
-- preserving its original columns for current consumers.
DROP VIEW IF EXISTS v_profile_dashboard;
CREATE VIEW v_profile_dashboard AS
SELECT p.id AS profile_id,
       p.name,
       COUNT(pa.id) AS total_items,
       SUM(CASE WHEN pa.exception_status NOT IN ('EXC-NOT-APPLICABLE','EXC-UNAVAILABLE') THEN 1 ELSE 0 END) AS applicable_items,
       SUM(CASE WHEN pa.implementation_status='STS-FULL' THEN 1 ELSE 0 END) AS implemented_full,
       SUM(CASE WHEN pa.implementation_status='STS-PARTIAL' THEN 1 ELSE 0 END) AS implemented_partial,
       SUM(CASE WHEN pa.implementation_status='STS-NOT-APPLIED' THEN 1 ELSE 0 END) AS not_applied,
       SUM(CASE WHEN pa.verification_status='VER-PASS' THEN 1 ELSE 0 END) AS verified_pass,
       SUM(CASE WHEN pa.verification_status='VER-FAIL' THEN 1 ELSE 0 END) AS verified_fail,
       SUM(CASE WHEN pa.exception_status<>'EXC-NONE' THEN 1 ELSE 0 END) AS with_exception,
       SUM(CASE WHEN pa.exception_status NOT IN ('EXC-NOT-APPLICABLE','EXC-UNAVAILABLE')
                 AND pa.implementation_status<>'STS-FULL' THEN 1 ELSE 0 END) AS open_gaps,
       SUM(CASE WHEN pa.due_date IS NOT NULL AND pa.due_date<date('now')
                 AND pa.implementation_status<>'STS-FULL' THEN 1 ELSE 0 END) AS overdue_items
  FROM enterprise_profiles p
  LEFT JOIN profile_artifacts pa ON pa.profile_id=p.id
 GROUP BY p.id,p.name;

-- N/A and unavailable leave the denominator. Deferred and accepted risk remain
-- visible gaps under profile-score-v1; they do not earn implementation credit.
DROP VIEW IF EXISTS v_gap_analysis;
CREATE VIEW v_gap_analysis AS
SELECT pa.profile_id,
       pa.artifact_id,
       a.title_en,
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

DROP VIEW IF EXISTS v_profile_evidence_integrity_issues;
CREATE VIEW v_profile_evidence_integrity_issues AS
SELECT e.id AS evidence_id,
       e.profile_artifact_id,
       e.assessment_id,
       a.profile_artifact_id AS assessment_profile_artifact_id,
       'CROSS_PROFILE_ARTIFACT_ASSESSMENT' AS issue_code
  FROM profile_evidence e
  JOIN profile_assessments a ON a.id=e.assessment_id
 WHERE e.profile_artifact_id<>a.profile_artifact_id;
