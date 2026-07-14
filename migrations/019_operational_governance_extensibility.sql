-- ============================================================================
-- SecureGuide — Migration 019: Operational Governance & Content Extensibility
-- ----------------------------------------------------------------------------
-- Additive only. Keeps the Master Catalog separate from profile state while
-- adding: locale-neutral content, governed profile exceptions, periodic review
-- snapshots, and acyclic REL-DEP enforcement. Content enrichment is explicitly
-- independent from structural classification and may mature later.
-- ============================================================================

PRAGMA foreign_keys = ON;

INSERT OR IGNORE INTO schema_migrations (version, description)
VALUES ('019', 'Localized content, exception lifecycle, profile review cycles, and dependency DAG enforcement');

-- ----------------------------------------------------------------------------
-- 1) Locale-neutral content layer
-- Existing title_en/title_ar columns remain the compatibility/canonical surface.
-- New locales and later content improvements live here without schema changes.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS artifact_localizations (
    artifact_id                 TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    locale                      TEXT NOT NULL,
    is_primary                  INTEGER NOT NULL DEFAULT 0,
    title                       TEXT NOT NULL,
    description                 TEXT,
    definition_short            TEXT,
    definition_full             TEXT,
    objective                   TEXT,
    implementation_guidance     TEXT,
    verification_method_note    TEXT,
    evidence_required           TEXT,
    common_misinterpretations   TEXT,
    content_maturity            TEXT NOT NULL DEFAULT 'MINIMAL',
    content_review_status       TEXT NOT NULL DEFAULT 'NOT_REVIEWED',
    reviewed_by                 TEXT,
    reviewed_at                 TEXT,
    created_at                  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at                  TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (artifact_id, locale),
    CHECK (length(locale) BETWEEN 2 AND 15),
    CHECK (is_primary IN (0,1)),
    CHECK (content_maturity IN ('DRAFT','MINIMAL','ENRICHED','REVIEWED')),
    CHECK (content_review_status IN ('NOT_REVIEWED','NEEDS_REVIEW','APPROVED')),
    CHECK (content_review_status <> 'APPROVED' OR (reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL))
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_artifact_primary_locale
    ON artifact_localizations(artifact_id) WHERE is_primary=1;
CREATE INDEX IF NOT EXISTS idx_localizations_locale
    ON artifact_localizations(locale, content_maturity, content_review_status);

INSERT OR IGNORE INTO artifact_localizations (
    artifact_id, locale, is_primary, title, description, definition_short,
    definition_full, objective, implementation_guidance, verification_method_note,
    evidence_required, common_misinterpretations, content_maturity
)
SELECT id, 'en', 1, title_en, description_en, definition_short_en,
       definition_full_en, objective_en, implementation_guidance,
       verification_method_note, evidence_required, common_misinterpretations,
       CASE
         WHEN definition_short_en IS NULL OR trim(definition_short_en)='' THEN 'DRAFT'
         WHEN definition_full_en IS NOT NULL AND objective_en IS NOT NULL THEN 'ENRICHED'
         ELSE 'MINIMAL'
       END
  FROM security_artifacts;

INSERT OR IGNORE INTO artifact_localizations (
    artifact_id, locale, is_primary, title, description, definition_short,
    definition_full, objective, verification_method_note, evidence_required,
    content_maturity
)
SELECT id, 'ar', 0, COALESCE(title_ar, title_en), description_ar,
       definition_short_ar, definition_full_ar, objective_ar,
       verification_method_note_ar, evidence_required_ar,
       CASE
         WHEN definition_short_ar IS NULL OR trim(definition_short_ar)='' THEN 'DRAFT'
         WHEN definition_full_ar IS NOT NULL AND objective_ar IS NOT NULL THEN 'ENRICHED'
         ELSE 'MINIMAL'
       END
  FROM security_artifacts
 WHERE title_ar IS NOT NULL OR description_ar IS NOT NULL
    OR definition_short_ar IS NOT NULL OR definition_full_ar IS NOT NULL
    OR objective_ar IS NOT NULL OR verification_method_note_ar IS NOT NULL
    OR evidence_required_ar IS NOT NULL;

CREATE TRIGGER IF NOT EXISTS trg_artifact_localization_insert
AFTER INSERT ON security_artifacts
BEGIN
    INSERT OR IGNORE INTO artifact_localizations (
        artifact_id,locale,is_primary,title,description,definition_short,
        definition_full,objective,implementation_guidance,verification_method_note,
        evidence_required,common_misinterpretations,content_maturity
    ) VALUES (
        NEW.id,'en',1,NEW.title_en,NEW.description_en,NEW.definition_short_en,
        NEW.definition_full_en,NEW.objective_en,NEW.implementation_guidance,
        NEW.verification_method_note,NEW.evidence_required,NEW.common_misinterpretations,
        CASE
          WHEN NEW.definition_short_en IS NULL OR trim(NEW.definition_short_en)='' THEN 'DRAFT'
          WHEN NEW.definition_full_en IS NOT NULL AND NEW.objective_en IS NOT NULL THEN 'ENRICHED'
          ELSE 'MINIMAL'
        END
    );
    INSERT OR IGNORE INTO artifact_localizations (
        artifact_id,locale,is_primary,title,description,definition_short,
        definition_full,objective,verification_method_note,evidence_required,content_maturity
    )
    SELECT NEW.id,'ar',0,COALESCE(NEW.title_ar,NEW.title_en),NEW.description_ar,
           NEW.definition_short_ar,NEW.definition_full_ar,NEW.objective_ar,
           NEW.verification_method_note_ar,NEW.evidence_required_ar,
           CASE
             WHEN NEW.definition_short_ar IS NULL OR trim(NEW.definition_short_ar)='' THEN 'DRAFT'
             WHEN NEW.definition_full_ar IS NOT NULL AND NEW.objective_ar IS NOT NULL THEN 'ENRICHED'
             ELSE 'MINIMAL'
           END
     WHERE NEW.title_ar IS NOT NULL OR NEW.description_ar IS NOT NULL
        OR NEW.definition_short_ar IS NOT NULL OR NEW.definition_full_ar IS NOT NULL
        OR NEW.objective_ar IS NOT NULL OR NEW.verification_method_note_ar IS NOT NULL
        OR NEW.evidence_required_ar IS NOT NULL;
END;

CREATE TRIGGER IF NOT EXISTS trg_artifact_localization_update_en
AFTER UPDATE OF title_en,description_en,definition_short_en,definition_full_en,
                objective_en,implementation_guidance,verification_method_note,
                evidence_required,common_misinterpretations ON security_artifacts
BEGIN
    INSERT INTO artifact_localizations (
        artifact_id,locale,is_primary,title,description,definition_short,
        definition_full,objective,implementation_guidance,verification_method_note,
        evidence_required,common_misinterpretations,content_maturity,content_review_status,updated_at
    ) VALUES (
        NEW.id,'en',1,NEW.title_en,NEW.description_en,NEW.definition_short_en,
        NEW.definition_full_en,NEW.objective_en,NEW.implementation_guidance,
        NEW.verification_method_note,NEW.evidence_required,NEW.common_misinterpretations,
        CASE
          WHEN NEW.definition_short_en IS NULL OR trim(NEW.definition_short_en)='' THEN 'DRAFT'
          WHEN NEW.definition_full_en IS NOT NULL AND NEW.objective_en IS NOT NULL THEN 'ENRICHED'
          ELSE 'MINIMAL'
        END,
        'NEEDS_REVIEW',datetime('now')
    )
    ON CONFLICT(artifact_id,locale) DO UPDATE SET
        title=excluded.title,
        description=excluded.description,
        definition_short=excluded.definition_short,
        definition_full=excluded.definition_full,
        objective=excluded.objective,
        implementation_guidance=excluded.implementation_guidance,
        verification_method_note=excluded.verification_method_note,
        evidence_required=excluded.evidence_required,
        common_misinterpretations=excluded.common_misinterpretations,
        content_maturity=excluded.content_maturity,
        content_review_status='NEEDS_REVIEW',
        reviewed_by=NULL,
        reviewed_at=NULL,
        updated_at=datetime('now');
END;

CREATE TRIGGER IF NOT EXISTS trg_artifact_localization_update_ar
AFTER UPDATE OF title_ar,description_ar,definition_short_ar,definition_full_ar,
                objective_ar,verification_method_note_ar,evidence_required_ar ON security_artifacts
BEGIN
    INSERT INTO artifact_localizations (
        artifact_id,locale,is_primary,title,description,definition_short,
        definition_full,objective,verification_method_note,evidence_required,
        content_maturity,content_review_status,updated_at
    ) VALUES (
        NEW.id,'ar',0,COALESCE(NEW.title_ar,NEW.title_en),NEW.description_ar,
        NEW.definition_short_ar,NEW.definition_full_ar,NEW.objective_ar,
        NEW.verification_method_note_ar,NEW.evidence_required_ar,
        CASE
          WHEN NEW.definition_short_ar IS NULL OR trim(NEW.definition_short_ar)='' THEN 'DRAFT'
          WHEN NEW.definition_full_ar IS NOT NULL AND NEW.objective_ar IS NOT NULL THEN 'ENRICHED'
          ELSE 'MINIMAL'
        END,
        'NEEDS_REVIEW',datetime('now')
    )
    ON CONFLICT(artifact_id,locale) DO UPDATE SET
        title=excluded.title,
        description=excluded.description,
        definition_short=excluded.definition_short,
        definition_full=excluded.definition_full,
        objective=excluded.objective,
        verification_method_note=excluded.verification_method_note,
        evidence_required=excluded.evidence_required,
        content_maturity=excluded.content_maturity,
        content_review_status='NEEDS_REVIEW',
        reviewed_by=NULL,
        reviewed_at=NULL,
        updated_at=datetime('now');
END;

-- ----------------------------------------------------------------------------
-- 2) Governed profile exceptions (operational, never Master Catalog state)
-- ----------------------------------------------------------------------------
ALTER TABLE profile_exceptions ADD COLUMN workflow_status TEXT NOT NULL DEFAULT 'DRAFT'
    CHECK (workflow_status IN ('DRAFT','SUBMITTED','APPROVED','EXPIRED','REVOKED','CLOSED'));
ALTER TABLE profile_exceptions ADD COLUMN exception_source TEXT NOT NULL DEFAULT 'USER'
    CHECK (exception_source IN ('USER','IMPORT','POLICY','ASSESSMENT'));
ALTER TABLE profile_exceptions ADD COLUMN updated_at TEXT NOT NULL DEFAULT (datetime('now'));
ALTER TABLE profile_exceptions ADD COLUMN closed_at TEXT;
ALTER TABLE profile_exceptions ADD COLUMN closed_by TEXT;
ALTER TABLE profile_exceptions ADD COLUMN closure_note TEXT;

ALTER TABLE profile_artifacts ADD COLUMN active_exception_id TEXT
    REFERENCES profile_exceptions(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_prof_art_active_exception ON profile_artifacts(active_exception_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_profile_approved_exception
    ON profile_exceptions(profile_artifact_id) WHERE workflow_status='APPROVED';
CREATE INDEX IF NOT EXISTS idx_prof_exc_workflow
    ON profile_exceptions(workflow_status, expiry_date, profile_artifact_id);

CREATE TABLE IF NOT EXISTS profile_exception_events (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    exception_id        TEXT NOT NULL REFERENCES profile_exceptions(id) ON DELETE CASCADE,
    event_type          TEXT NOT NULL,
    status_from         TEXT,
    status_to           TEXT,
    actor               TEXT,
    note                TEXT,
    event_at            TEXT NOT NULL DEFAULT (datetime('now')),
    CHECK (event_type IN ('CREATED','SUBMITTED','APPROVED','RENEWED','EXPIRED','REVOKED','CLOSED','UPDATED'))
);
CREATE INDEX IF NOT EXISTS idx_prof_exc_events
    ON profile_exception_events(exception_id, event_at);

CREATE TRIGGER IF NOT EXISTS trg_profile_exception_validate_insert
BEFORE INSERT ON profile_exceptions
BEGIN
    SELECT CASE
      WHEN NEW.workflow_status='APPROVED'
       AND (NEW.approved_by IS NULL OR NEW.approval_date IS NULL)
      THEN RAISE(ABORT, 'approved exception requires approved_by and approval_date')
    END;
    SELECT CASE
      WHEN NEW.workflow_status='APPROVED'
       AND NEW.exception_status='EXC-RISK-ACCEPTED'
       AND NEW.risk_accepted_by IS NULL
      THEN RAISE(ABORT, 'risk acceptance requires risk_accepted_by')
    END;
    SELECT CASE
      WHEN NEW.approval_date IS NOT NULL AND NEW.expiry_date IS NOT NULL
       AND NEW.expiry_date <= NEW.approval_date
      THEN RAISE(ABORT, 'exception expiry_date must be after approval_date')
    END;
END;

CREATE TRIGGER IF NOT EXISTS trg_profile_exception_validate_update
BEFORE UPDATE ON profile_exceptions
BEGIN
    SELECT CASE
      WHEN NEW.workflow_status='APPROVED'
       AND (NEW.approved_by IS NULL OR NEW.approval_date IS NULL)
      THEN RAISE(ABORT, 'approved exception requires approved_by and approval_date')
    END;
    SELECT CASE
      WHEN NEW.workflow_status='APPROVED'
       AND NEW.exception_status='EXC-RISK-ACCEPTED'
       AND NEW.risk_accepted_by IS NULL
      THEN RAISE(ABORT, 'risk acceptance requires risk_accepted_by')
    END;
    SELECT CASE
      WHEN NEW.approval_date IS NOT NULL AND NEW.expiry_date IS NOT NULL
       AND NEW.expiry_date <= NEW.approval_date
      THEN RAISE(ABORT, 'exception expiry_date must be after approval_date')
    END;
END;

CREATE TRIGGER IF NOT EXISTS trg_profile_exception_event_insert
AFTER INSERT ON profile_exceptions
BEGIN
    INSERT INTO profile_exception_events(exception_id,event_type,status_to,actor,note)
    VALUES (NEW.id,
            CASE NEW.workflow_status
              WHEN 'DRAFT' THEN 'CREATED'
              WHEN 'SUBMITTED' THEN 'SUBMITTED'
              WHEN 'APPROVED' THEN 'APPROVED'
              WHEN 'EXPIRED' THEN 'EXPIRED'
              WHEN 'REVOKED' THEN 'REVOKED'
              ELSE 'CLOSED'
            END,
            NEW.workflow_status,
            COALESCE(NEW.approved_by, NEW.closed_by, 'SYSTEM'),
            NEW.justification);
END;

CREATE TRIGGER IF NOT EXISTS trg_profile_exception_event_status
AFTER UPDATE OF workflow_status ON profile_exceptions
WHEN OLD.workflow_status <> NEW.workflow_status
BEGIN
    INSERT INTO profile_exception_events(exception_id,event_type,status_from,status_to,actor,note)
    VALUES (NEW.id, NEW.workflow_status, OLD.workflow_status, NEW.workflow_status,
            COALESCE(NEW.approved_by, NEW.closed_by, 'SYSTEM'),
            COALESCE(NEW.closure_note, NEW.justification));
END;

CREATE TRIGGER IF NOT EXISTS trg_profile_exception_event_renewal
AFTER UPDATE OF expiry_date ON profile_exceptions
WHEN OLD.expiry_date IS NOT NULL
 AND OLD.expiry_date IS NOT NEW.expiry_date
 AND NEW.workflow_status='APPROVED'
BEGIN
    INSERT INTO profile_exception_events(exception_id,event_type,status_from,status_to,actor,note)
    VALUES (NEW.id, 'RENEWED', NEW.workflow_status, NEW.workflow_status,
            COALESCE(NEW.approved_by, 'SYSTEM'), 'expiry date changed');
END;

CREATE TRIGGER IF NOT EXISTS trg_profile_exception_activate_insert
AFTER INSERT ON profile_exceptions
WHEN NEW.workflow_status='APPROVED'
BEGIN
    UPDATE profile_artifacts
       SET exception_status=NEW.exception_status,
           active_exception_id=NEW.id,
           updated_at=datetime('now')
     WHERE id=NEW.profile_artifact_id;
END;

CREATE TRIGGER IF NOT EXISTS trg_profile_exception_activate_update
AFTER UPDATE OF workflow_status, exception_status ON profile_exceptions
WHEN NEW.workflow_status='APPROVED'
BEGIN
    UPDATE profile_artifacts
       SET exception_status=NEW.exception_status,
           active_exception_id=NEW.id,
           updated_at=datetime('now')
     WHERE id=NEW.profile_artifact_id;
END;

CREATE TRIGGER IF NOT EXISTS trg_profile_exception_deactivate
AFTER UPDATE OF workflow_status ON profile_exceptions
WHEN NEW.workflow_status IN ('EXPIRED','REVOKED','CLOSED')
BEGIN
    UPDATE profile_artifacts
       SET exception_status='EXC-NONE',
           active_exception_id=NULL,
           updated_at=datetime('now')
     WHERE id=NEW.profile_artifact_id AND active_exception_id=NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_profile_exception_delete_sync
BEFORE DELETE ON profile_exceptions
BEGIN
    UPDATE profile_artifacts
       SET exception_status='EXC-NONE', active_exception_id=NULL, updated_at=datetime('now')
     WHERE active_exception_id=OLD.id;
END;

-- ----------------------------------------------------------------------------
-- 3) Periodic profile review cycles and immutable completion snapshots
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS profile_review_cycles (
    id                  TEXT PRIMARY KEY,
    profile_id          TEXT NOT NULL REFERENCES enterprise_profiles(id) ON DELETE CASCADE,
    title               TEXT NOT NULL,
    review_type         TEXT NOT NULL DEFAULT 'PERIODIC',
    status              TEXT NOT NULL DEFAULT 'PLANNED',
    reviewer            TEXT,
    scoring_policy_id   TEXT REFERENCES scoring_policy(id) ON DELETE SET NULL,
    started_at          TEXT,
    completed_at        TEXT,
    notes               TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now')),
    CHECK (review_type IN ('PERIODIC','AD_HOC','AUDIT','POST_INCIDENT','BASELINE')),
    CHECK (status IN ('PLANNED','IN_PROGRESS','COMPLETED','CANCELLED')),
    CHECK (status <> 'COMPLETED' OR (reviewer IS NOT NULL AND completed_at IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS idx_profile_review_cycles
    ON profile_review_cycles(profile_id, status, created_at);

CREATE TABLE IF NOT EXISTS profile_review_cycle_items (
    cycle_id               TEXT NOT NULL REFERENCES profile_review_cycles(id) ON DELETE CASCADE,
    profile_artifact_id     TEXT NOT NULL REFERENCES profile_artifacts(id) ON DELETE RESTRICT,
    implementation_status   TEXT NOT NULL,
    verification_status     TEXT NOT NULL,
    effectiveness           TEXT NOT NULL,
    exception_status        TEXT NOT NULL,
    effective_priority      TEXT NOT NULL,
    assessment_score        REAL,
    evidence_count          INTEGER NOT NULL DEFAULT 0,
    active_exception_id     TEXT REFERENCES profile_exceptions(id) ON DELETE SET NULL,
    captured_at             TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (cycle_id, profile_artifact_id),
    CHECK (implementation_status IN ('STS-NOT-APPLIED','STS-PARTIAL','STS-FULL','STS-PLANNED','STS-NEEDS-IMPROVEMENT')),
    CHECK (verification_status IN ('VER-NOT-VERIFIED','VER-PASS','VER-FAIL')),
    CHECK (effectiveness IN ('EFF-LOW','EFF-MEDIUM','EFF-HIGH','EFF-UNKNOWN')),
    CHECK (exception_status IN ('EXC-NONE','EXC-NOT-APPLICABLE','EXC-RISK-ACCEPTED','EXC-DEFERRED','EXC-UNAVAILABLE')),
    CHECK (effective_priority IN ('PRI-CRITICAL','PRI-HIGH','PRI-MEDIUM','PRI-LOW')),
    CHECK (assessment_score IS NULL OR (assessment_score >= 0 AND assessment_score <= 100)),
    CHECK (evidence_count >= 0)
);
CREATE INDEX IF NOT EXISTS idx_profile_review_items_artifact
    ON profile_review_cycle_items(profile_artifact_id, cycle_id);

CREATE TABLE IF NOT EXISTS profile_review_metrics (
    cycle_id          TEXT NOT NULL REFERENCES profile_review_cycles(id) ON DELETE CASCADE,
    metric_code       TEXT NOT NULL,
    metric_value      REAL NOT NULL,
    metric_unit       TEXT NOT NULL,
    formula_version   TEXT NOT NULL,
    PRIMARY KEY (cycle_id, metric_code),
    CHECK (metric_code IN ('OVERALL_SCORE','ASSESSMENT_COVERAGE','VERIFICATION_COVERAGE',
                           'EFFECTIVENESS_KNOWN','CRITICAL_REMAINING','APPLICABLE_COUNT',
                           'IMPLEMENTED_COUNT','VERIFIED_COUNT','EXCEPTION_COUNT')),
    CHECK (metric_unit IN ('PERCENT','COUNT','SCORE')),
    CHECK (metric_value >= 0)
);

CREATE TRIGGER IF NOT EXISTS trg_review_item_same_profile_insert
BEFORE INSERT ON profile_review_cycle_items
BEGIN
    SELECT CASE WHEN
      (SELECT profile_id FROM profile_artifacts WHERE id=NEW.profile_artifact_id)
      <>
      (SELECT profile_id FROM profile_review_cycles WHERE id=NEW.cycle_id)
    THEN RAISE(ABORT, 'review item and review cycle must belong to the same profile') END;
END;

CREATE TRIGGER IF NOT EXISTS trg_review_item_same_profile_update
BEFORE UPDATE OF cycle_id, profile_artifact_id ON profile_review_cycle_items
BEGIN
    SELECT CASE WHEN
      (SELECT profile_id FROM profile_artifacts WHERE id=NEW.profile_artifact_id)
      <>
      (SELECT profile_id FROM profile_review_cycles WHERE id=NEW.cycle_id)
    THEN RAISE(ABORT, 'review item and review cycle must belong to the same profile') END;
END;

CREATE TRIGGER IF NOT EXISTS trg_completed_review_immutable
BEFORE UPDATE ON profile_review_cycles
WHEN OLD.status='COMPLETED'
BEGIN
    SELECT RAISE(ABORT, 'completed review cycles are immutable');
END;

CREATE TRIGGER IF NOT EXISTS trg_completed_review_no_delete
BEFORE DELETE ON profile_review_cycles
WHEN OLD.status='COMPLETED'
BEGIN
    SELECT RAISE(ABORT, 'completed review cycles cannot be deleted');
END;

CREATE TRIGGER IF NOT EXISTS trg_completed_review_items_immutable_update
BEFORE UPDATE ON profile_review_cycle_items
WHEN (SELECT status FROM profile_review_cycles WHERE id=OLD.cycle_id)='COMPLETED'
BEGIN
    SELECT RAISE(ABORT, 'completed review snapshots are immutable');
END;

CREATE TRIGGER IF NOT EXISTS trg_completed_review_items_immutable_delete
BEFORE DELETE ON profile_review_cycle_items
WHEN (SELECT status FROM profile_review_cycles WHERE id=OLD.cycle_id)='COMPLETED'
BEGIN
    SELECT RAISE(ABORT, 'completed review snapshots are immutable and cannot be deleted');
END;

-- ----------------------------------------------------------------------------
-- 4) REL-DEP is a directed acyclic graph. Other relationship types remain N:M.
-- ----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_rel_dep_graph
    ON artifact_relationships(source_id, target_id) WHERE relation_type='REL-DEP';

CREATE TRIGGER IF NOT EXISTS trg_rel_dep_no_cycle_insert
BEFORE INSERT ON artifact_relationships
WHEN NEW.relation_type='REL-DEP'
BEGIN
    SELECT CASE WHEN NEW.source_id=NEW.target_id
      THEN RAISE(ABORT, 'REL-DEP self-dependency is not allowed') END;
    WITH RECURSIVE reachable(id) AS (
        SELECT target_id FROM artifact_relationships
         WHERE source_id=NEW.target_id AND relation_type='REL-DEP'
        UNION
        SELECT r.target_id FROM artifact_relationships r
        JOIN reachable x ON r.source_id=x.id
         WHERE r.relation_type='REL-DEP'
    )
    SELECT RAISE(ABORT, 'REL-DEP cycle is not allowed')
      FROM reachable WHERE id=NEW.source_id LIMIT 1;
END;

CREATE TRIGGER IF NOT EXISTS trg_rel_dep_no_cycle_update
BEFORE UPDATE OF source_id, target_id, relation_type ON artifact_relationships
WHEN NEW.relation_type='REL-DEP'
BEGIN
    SELECT CASE WHEN NEW.source_id=NEW.target_id
      THEN RAISE(ABORT, 'REL-DEP self-dependency is not allowed') END;
    WITH RECURSIVE reachable(id) AS (
        SELECT target_id FROM artifact_relationships
         WHERE id<>OLD.id AND source_id=NEW.target_id AND relation_type='REL-DEP'
        UNION
        SELECT r.target_id FROM artifact_relationships r
        JOIN reachable x ON r.source_id=x.id
         WHERE r.id<>OLD.id AND r.relation_type='REL-DEP'
    )
    SELECT RAISE(ABORT, 'REL-DEP cycle is not allowed')
      FROM reachable WHERE id=NEW.source_id LIMIT 1;
END;

CREATE VIEW IF NOT EXISTS v_dependency_governance_issues AS
SELECT r.id AS relationship_id,
       r.source_id,
       r.target_id,
       CASE
         WHEN target.is_active=0 THEN 'INACTIVE_TARGET'
         WHEN source.publication_status IN ('APPROVED','PUBLISHED')
          AND target.publication_status NOT IN ('APPROVED','PUBLISHED')
         THEN 'APPROVED_DEPENDS_ON_UNAPPROVED'
       END AS issue_code
  FROM artifact_relationships r
  JOIN security_artifacts source ON source.id=r.source_id
  JOIN security_artifacts target ON target.id=r.target_id
 WHERE r.relation_type='REL-DEP'
   AND (target.is_active=0
        OR (source.publication_status IN ('APPROVED','PUBLISHED')
            AND target.publication_status NOT IN ('APPROVED','PUBLISHED')));

CREATE VIEW IF NOT EXISTS v_profile_current_exceptions AS
SELECT pa.profile_id, pa.id AS profile_artifact_id, pa.artifact_id,
       pa.exception_status, pa.active_exception_id,
       pe.workflow_status, pe.justification, pe.approved_by,
       pe.approval_date, pe.expiry_date, pe.risk_accepted_by
  FROM profile_artifacts pa
  LEFT JOIN profile_exceptions pe ON pe.id=pa.active_exception_id;
