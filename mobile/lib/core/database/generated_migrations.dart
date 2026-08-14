// GENERATED CODE - DO NOT EDIT.
// Run: python -m scripts.generate_mobile_migrations
// dart format off

final class EmbeddedMigration {
  const EmbeddedMigration({
    required this.version,
    required this.filename,
    required this.sha256,
    required this.sql,
  });

  final String version;
  final String filename;
  final String sha256;
  final String sql;
}

const embeddedMigrations = <EmbeddedMigration>[
  EmbeddedMigration(
    version: '017',
    filename: '017_equivalence_review_governance.sql',
    sha256: '618074bd6294952f88df89457feb046ddfbd9f11c1410d84d67088046dc70b56',
    sql:
        r'''-- ============================================================================
-- SecureGuide — Migration 017: Equivalence decision review governance
-- ----------------------------------------------------------------------------
-- Adds accountable, reviewable metadata to non-destructive equivalence groups.
-- Group decisions remain reference/curation data; no profile state is stored.
-- ============================================================================

PRAGMA foreign_keys = ON;

ALTER TABLE equivalence_groups ADD COLUMN decision_method TEXT
    CHECK (decision_method IS NULL OR decision_method IN
        ('AI_CONSERVATIVE','EXACT_MATCH','AI_CONSERVATIVE+EXACT_MATCH','MANUAL'));
ALTER TABLE equivalence_groups ADD COLUMN decision_confidence REAL
    CHECK (decision_confidence IS NULL OR
        (decision_confidence >= 0.0 AND decision_confidence <= 1.0));
ALTER TABLE equivalence_groups ADD COLUMN decision_rationale TEXT;
ALTER TABLE equivalence_groups ADD COLUMN ai_review_status TEXT NOT NULL
    DEFAULT 'AIR-HUMAN-REVIEW'
    CHECK (ai_review_status IN
        ('AIR-AUTO-ACCEPTED','AIR-HUMAN-REVIEW','AIR-HUMAN-APPROVED','AIR-HUMAN-REJECTED'));
ALTER TABLE equivalence_groups ADD COLUMN requires_human_review INTEGER NOT NULL
    DEFAULT 1 CHECK (requires_human_review IN (0,1));
ALTER TABLE equivalence_groups ADD COLUMN reviewed_by TEXT;
ALTER TABLE equivalence_groups ADD COLUMN reviewed_at TEXT;

CREATE INDEX IF NOT EXISTS idx_equivalence_review
    ON equivalence_groups(ai_review_status, requires_human_review);

INSERT OR IGNORE INTO schema_migrations (version, description) VALUES
    ('017', 'Equivalence decision rationale, confidence, and human-review governance');
''',
  ),
  EmbeddedMigration(
    version: '018',
    filename: '018_fallback_governance.sql',
    sha256: '94b606597c20f444f6af8c99bd939797b48ac28c14bc51cb810b70054953fb5a',
    sql:
        r'''-- ============================================================================
-- SecureGuide — Migration 018: Classification Fallback Governance
-- ----------------------------------------------------------------------------
-- Makes the SADP fallback vocabulary explicit without weakening the normative
-- USACM/SDT catalog constraints.  Lookup membership alone is not permission to
-- publish a value: UNKNOWN/MULTI are review signals, type/domain/sub-domain
-- never have fallbacks, and type-conditional N/A is represented structurally.
-- ============================================================================

PRAGMA foreign_keys = ON;

INSERT OR IGNORE INTO schema_migrations (version, description)
VALUES ('018', 'Explicit fallback disposition and fail-closed publication governance');

CREATE TABLE IF NOT EXISTS classification_fallback_policy (
    dimension            TEXT PRIMARY KEY,
    lookup_table         TEXT NOT NULL,
    fallback_mode        TEXT NOT NULL,
    not_applicable_code  TEXT,
    unknown_code         TEXT,
    multi_code           TEXT,
    na_disposition       TEXT NOT NULL,
    unknown_disposition  TEXT NOT NULL,
    multi_disposition    TEXT NOT NULL,
    rationale            TEXT NOT NULL,
    CHECK (fallback_mode IN ('NONE','TRIPLE')),
    CHECK (na_disposition IN ('FORBIDDEN','PUBLISHABLE','STRUCTURAL_NULL','REVIEW_ONLY','NORMALIZE_VALUES')),
    CHECK (unknown_disposition IN ('FORBIDDEN','PUBLISHABLE','STRUCTURAL_NULL','REVIEW_ONLY','NORMALIZE_VALUES')),
    CHECK (multi_disposition IN ('FORBIDDEN','PUBLISHABLE','STRUCTURAL_NULL','REVIEW_ONLY','NORMALIZE_VALUES')),
    CHECK (
        (fallback_mode = 'NONE'
         AND not_applicable_code IS NULL AND unknown_code IS NULL AND multi_code IS NULL
         AND na_disposition = 'FORBIDDEN'
         AND unknown_disposition = 'FORBIDDEN'
         AND multi_disposition = 'FORBIDDEN')
        OR
        (fallback_mode = 'TRIPLE'
         AND not_applicable_code IS NOT NULL AND unknown_code IS NOT NULL AND multi_code IS NOT NULL)
    )
);

-- Identity and lifecycle dimensions use their native controlled values only.
INSERT OR REPLACE INTO classification_fallback_policy VALUES
 ('artifact_type','lk_artifact_type','NONE',NULL,NULL,NULL,'FORBIDDEN','FORBIDDEN','FORBIDDEN','An artifact must have one real USACM type.'),
 ('primary_domain','lk_sdt_domain','NONE',NULL,NULL,NULL,'FORBIDDEN','FORBIDDEN','FORBIDDEN','Every artifact must have one real SDT primary domain.'),
 ('sub_domain','lk_sdt_subdomain','NONE',NULL,NULL,NULL,'FORBIDDEN','FORBIDDEN','FORBIDDEN','Every artifact must have one real SDT sub-domain belonging to its primary domain.'),
 ('implementation_status','lk_implementation_status','NONE',NULL,NULL,NULL,'FORBIDDEN','FORBIDDEN','FORBIDDEN','Use native STS-* operational states.'),
 ('verification_status','lk_verification_status','NONE',NULL,NULL,NULL,'FORBIDDEN','FORBIDDEN','FORBIDDEN','Use VER-NOT-VERIFIED rather than a generic fallback.'),
 ('relationship_type','lk_relationship_type','NONE',NULL,NULL,NULL,'FORBIDDEN','FORBIDDEN','FORBIDDEN','A relationship row must state one real REL-* meaning.'),
 ('ai_review_status','lk_ai_review_status','NONE',NULL,NULL,NULL,'FORBIDDEN','FORBIDDEN','FORBIDDEN','Use the native AI review workflow values.'),
 ('publication_status','lk_publication_status','NONE',NULL,NULL,NULL,'FORBIDDEN','FORBIDDEN','FORBIDDEN','Use the native publication lifecycle values.'),
 ('source_type','lk_source_type','NONE',NULL,NULL,NULL,'FORBIDDEN','FORBIDDEN','FORBIDDEN','Use a real controlled source type.'),
 ('asset_type','lk_asset_type','NONE',NULL,NULL,NULL,'FORBIDDEN','FORBIDDEN','FORBIDDEN','ART-AST requires one real asset type; other types use structural NULL.'),
 ('maturity_level','lk_maturity_level','NONE',NULL,NULL,NULL,'FORBIDDEN','FORBIDDEN','FORBIDDEN','Use a native maturity value or an optional NULL where the schema permits it.'),
 ('cost_category','lk_cost_category','NONE',NULL,NULL,NULL,'FORBIDDEN','FORBIDDEN','FORBIDDEN','Use a native cost category or an optional NULL.'),
 ('import_status','lk_import_status','NONE',NULL,NULL,NULL,'FORBIDDEN','FORBIDDEN','FORBIDDEN','Use the native import workflow values.'),
 ('tag_type','lk_tag_type','NONE',NULL,NULL,NULL,'FORBIDDEN','FORBIDDEN','FORBIDDEN','Tags use the seven approved normalized tag types.'),

-- Triple-bearing dimensions.  REVIEW_ONLY values may exist in lookup/UI review
-- vocabulary but are never valid in APPROVED/PUBLISHED catalog records.
 ('abstraction_level','lk_abstraction_level','TRIPLE','ABS-NA','ABS-UNKNOWN','ABS-MULTI','REVIEW_ONLY','REVIEW_ONLY','REVIEW_ONLY','The normalized catalog requires one real abstraction level.'),
 ('obligation_source','lk_obligation_source','TRIPLE','SRC-NA','SRC-UNKNOWN','SRC-MULTI','REVIEW_ONLY','REVIEW_ONLY','REVIEW_ONLY','The normalized catalog requires one real obligation source.'),
 ('obligation_level','lk_obligation_level','TRIPLE','OBL-NA','OBL-UNKNOWN','OBL-MULTI','REVIEW_ONLY','REVIEW_ONLY','REVIEW_ONLY','The normalized catalog requires one real obligation level.'),
 ('granularity_level','lk_granularity_level','TRIPLE','GRN-NA','GRN-UNKNOWN','GRN-MULTI','REVIEW_ONLY','REVIEW_ONLY','REVIEW_ONLY','The normalized catalog requires one real granularity level.'),
 ('priority','lk_priority','TRIPLE','PRI-NA','PRI-UNKNOWN','PRI-MULTI','REVIEW_ONLY','REVIEW_ONLY','REVIEW_ONLY','The catalog baseline priority must be a real PRI-* value.'),
 ('control_nature','lk_control_nature','TRIPLE','NAT-NA','NAT-UNKNOWN','NAT-MULTI','STRUCTURAL_NULL','REVIEW_ONLY','REVIEW_ONLY','Non-controls use NULL; ART-CTR/ART-CTE require one real nature.'),
 ('control_function','lk_control_function','TRIPLE','FUN-NA','FUN-UNKNOWN','FUN-MULTI','STRUCTURAL_NULL','REVIEW_ONLY','REVIEW_ONLY','Non-controls use NULL; ART-CTR/ART-CTE require one real function.'),
 ('requirement_type','lk_requirement_type','TRIPLE','RQT-NA','RQT-UNKNOWN','RQT-MULTI','STRUCTURAL_NULL','REVIEW_ONLY','REVIEW_ONLY','Non-requirements use NULL; ART-REQ requires one real requirement type.'),
 ('testability','lk_testability','TRIPLE','TST-NA','TST-UNKNOWN','TST-MULTI','PUBLISHABLE','REVIEW_ONLY','REVIEW_ONLY','TST-NA is a native USACM value; uncertainty still requires review.'),
 ('effectiveness','lk_effectiveness','TRIPLE','EFF-NA','EFF-UNKNOWN','EFF-MULTI','REVIEW_ONLY','PUBLISHABLE','REVIEW_ONLY','EFF-UNKNOWN is the native reference baseline, not an unresolved classification.'),
 ('exception_status','lk_exception_status','TRIPLE','EXC-NOT-APPLICABLE','EXC-UNKNOWN','EXC-MULTI','PUBLISHABLE','REVIEW_ONLY','REVIEW_ONLY','EXC-NOT-APPLICABLE is a native profile exception; uncertainty is not publishable.'),
 ('threat','lk_threat','TRIPLE','THR-NA','THR-UNKNOWN','THR-MULTI','PUBLISHABLE','REVIEW_ONLY','NORMALIZE_VALUES','Multiple threats are stored as multiple artifact_threats rows, never as THR-MULTI in an approved artifact.'),
 ('review_frequency','lk_review_frequency','TRIPLE','NA','UNKNOWN','MULTI','REVIEW_ONLY','REVIEW_ONLY','REVIEW_ONLY','Use a real cadence; the catalog baseline is AD-HOC.'),
 ('mapping_strength','lk_mapping_strength','TRIPLE','NA','UNKNOWN','MULTI','REVIEW_ONLY','REVIEW_ONLY','NORMALIZE_VALUES','Each mapping row has one real strength; multiple mappings use multiple rows.');

CREATE VIEW IF NOT EXISTS v_nonpublishable_fallback_codes AS
SELECT dimension, not_applicable_code AS code, na_disposition AS disposition
  FROM classification_fallback_policy WHERE fallback_mode='TRIPLE' AND na_disposition <> 'PUBLISHABLE'
UNION ALL
SELECT dimension, unknown_code, unknown_disposition
  FROM classification_fallback_policy WHERE fallback_mode='TRIPLE' AND unknown_disposition <> 'PUBLISHABLE'
UNION ALL
SELECT dimension, multi_code, multi_disposition
  FROM classification_fallback_policy WHERE fallback_mode='TRIPLE' AND multi_disposition <> 'PUBLISHABLE';
''',
  ),
  EmbeddedMigration(
    version: '019',
    filename: '019_operational_governance_extensibility.sql',
    sha256: 'd682a1926da230fe95e066f3a094aeb854e11b434d7ae22bd038145c66bde436',
    sql:
        r'''-- ============================================================================
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
''',
  ),
  EmbeddedMigration(
    version: '020',
    filename: '020_exception_state_invariants.sql',
    sha256: 'ed40432fa8bb48182795195b0a756c0aa60117285f33f457fe92dfb90ba41a53',
    sql:
        r'''-- ============================================================================
-- SecureGuide — Migration 020: Exception State-Machine Invariants
-- ----------------------------------------------------------------------------
-- Strengthens migration 019 without rewriting it: approved exceptions expire,
-- terminal states stay terminal, event logging covers draft rework, and current
-- profile exception state can only point to a matching approved exception row.
-- ============================================================================

PRAGMA foreign_keys = ON;

INSERT OR IGNORE INTO schema_migrations (version, description)
VALUES ('020', 'Enforce governed exception transitions and profile-state consistency');

DROP TRIGGER IF EXISTS trg_profile_exception_validate_insert;
DROP TRIGGER IF EXISTS trg_profile_exception_validate_update;
DROP TRIGGER IF EXISTS trg_profile_exception_event_status;

CREATE TRIGGER trg_profile_exception_validate_insert
BEFORE INSERT ON profile_exceptions
BEGIN
    SELECT CASE
      WHEN NEW.workflow_status='APPROVED'
       AND (NEW.approved_by IS NULL OR NEW.approval_date IS NULL OR NEW.expiry_date IS NULL)
      THEN RAISE(ABORT, 'approved exception requires approver, approval date, and expiry date')
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
    SELECT CASE
      WHEN NEW.workflow_status IN ('CLOSED','REVOKED')
       AND (NEW.closed_by IS NULL OR NEW.closed_at IS NULL)
      THEN RAISE(ABORT, 'closed or revoked exception requires closed_by and closed_at')
    END;
END;

CREATE TRIGGER trg_profile_exception_validate_update
BEFORE UPDATE ON profile_exceptions
BEGIN
    SELECT CASE
      WHEN OLD.workflow_status IN ('EXPIRED','REVOKED','CLOSED')
       AND NEW.workflow_status <> OLD.workflow_status
      THEN RAISE(ABORT, 'terminal exception workflow state is immutable')
    END;
    SELECT CASE
      WHEN NOT (
        NEW.workflow_status=OLD.workflow_status
        OR (OLD.workflow_status='DRAFT' AND NEW.workflow_status IN ('SUBMITTED','APPROVED','CLOSED'))
        OR (OLD.workflow_status='SUBMITTED' AND NEW.workflow_status IN ('DRAFT','APPROVED','REVOKED','CLOSED'))
        OR (OLD.workflow_status='APPROVED' AND NEW.workflow_status IN ('EXPIRED','REVOKED','CLOSED'))
      )
      THEN RAISE(ABORT, 'invalid exception workflow transition')
    END;
    SELECT CASE
      WHEN NEW.workflow_status='APPROVED'
       AND (NEW.approved_by IS NULL OR NEW.approval_date IS NULL OR NEW.expiry_date IS NULL)
      THEN RAISE(ABORT, 'approved exception requires approver, approval date, and expiry date')
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
    SELECT CASE
      WHEN NEW.workflow_status IN ('CLOSED','REVOKED')
       AND (NEW.closed_by IS NULL OR NEW.closed_at IS NULL)
      THEN RAISE(ABORT, 'closed or revoked exception requires closed_by and closed_at')
    END;
END;

CREATE TRIGGER trg_profile_exception_event_status
AFTER UPDATE OF workflow_status ON profile_exceptions
WHEN OLD.workflow_status <> NEW.workflow_status
BEGIN
    INSERT INTO profile_exception_events(exception_id,event_type,status_from,status_to,actor,note)
    VALUES (
        NEW.id,
        CASE NEW.workflow_status WHEN 'DRAFT' THEN 'UPDATED' ELSE NEW.workflow_status END,
        OLD.workflow_status,
        NEW.workflow_status,
        COALESCE(NEW.closed_by, NEW.approved_by, 'SYSTEM'),
        COALESCE(NEW.closure_note, NEW.justification)
    );
END;

CREATE TRIGGER IF NOT EXISTS trg_profile_artifact_exception_insert
BEFORE INSERT ON profile_artifacts
WHEN NEW.exception_status <> 'EXC-NONE' OR NEW.active_exception_id IS NOT NULL
BEGIN
    SELECT RAISE(ABORT, 'create profile artifact with EXC-NONE, then approve a profile exception');
END;

CREATE TRIGGER IF NOT EXISTS trg_profile_artifact_exception_update
BEFORE UPDATE OF exception_status, active_exception_id ON profile_artifacts
BEGIN
    SELECT CASE
      WHEN NEW.exception_status='EXC-NONE' AND NEW.active_exception_id IS NOT NULL
      THEN RAISE(ABORT, 'EXC-NONE cannot reference an active exception')
    END;
    SELECT CASE
      WHEN NEW.exception_status<>'EXC-NONE' AND NEW.active_exception_id IS NULL
      THEN RAISE(ABORT, 'non-empty exception status requires an approved active exception')
    END;
    SELECT CASE
      WHEN NEW.active_exception_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM profile_exceptions pe
         WHERE pe.id=NEW.active_exception_id
           AND pe.profile_artifact_id=NEW.id
           AND pe.workflow_status='APPROVED'
           AND pe.exception_status=NEW.exception_status
      )
      THEN RAISE(ABORT, 'active exception must be approved and match the profile artifact')
    END;
END;

CREATE VIEW IF NOT EXISTS v_exception_governance_issues AS
SELECT pa.id AS profile_artifact_id,
       pa.profile_id,
       pa.artifact_id,
       pa.exception_status,
       pa.active_exception_id,
       CASE
         WHEN pa.exception_status<>'EXC-NONE' AND pa.active_exception_id IS NULL
           THEN 'STATUS_WITHOUT_ACTIVE_EXCEPTION'
         WHEN pa.exception_status='EXC-NONE' AND pa.active_exception_id IS NOT NULL
           THEN 'ACTIVE_EXCEPTION_WITH_NONE_STATUS'
         WHEN pe.id IS NULL AND pa.active_exception_id IS NOT NULL
           THEN 'MISSING_EXCEPTION'
         WHEN pe.workflow_status<>'APPROVED' AND pa.active_exception_id IS NOT NULL
           THEN 'ACTIVE_EXCEPTION_NOT_APPROVED'
         WHEN pe.exception_status<>pa.exception_status
           THEN 'EXCEPTION_STATUS_MISMATCH'
         WHEN pe.expiry_date IS NOT NULL AND pe.expiry_date<=date('now')
           THEN 'APPROVED_EXCEPTION_EXPIRED_BY_DATE'
       END AS issue_code
  FROM profile_artifacts pa
  LEFT JOIN profile_exceptions pe ON pe.id=pa.active_exception_id
 WHERE (pa.exception_status<>'EXC-NONE' AND pa.active_exception_id IS NULL)
    OR (pa.exception_status='EXC-NONE' AND pa.active_exception_id IS NOT NULL)
    OR (pa.active_exception_id IS NOT NULL AND
        (pe.id IS NULL OR pe.workflow_status<>'APPROVED'
         OR pe.exception_status<>pa.exception_status
         OR (pe.expiry_date IS NOT NULL AND pe.expiry_date<=date('now'))));
''',
  ),
  EmbeddedMigration(
    version: '021',
    filename: '021_profile_operational_workflow.sql',
    sha256: 'f27930a920c50bae793f96234fba3550003bbce1c30765a97ccaefe2e79a0855',
    sql:
        r'''-- ============================================================================
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
''',
  ),
  EmbeddedMigration(
    version: '022',
    filename: '022_template_application_provenance.sql',
    sha256: '17517eb4ce48537c23e9f3ddcd3ef7d5937cb7bdc433f98d270df7e2d60cf458',
    sql:
        r'''-- ============================================================================
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
''',
  ),
  EmbeddedMigration(
    version: '023',
    filename: '023_blueprint_approval_tasks.sql',
    sha256: 'b9185f1bbda7d3c4e03bc812864b25835d7ad99779e8a878472238e481943f1c',
    sql:
        r'''-- ============================================================================
-- SecureGuide — Migration 023: Approved Blueprint and Task Workflow
-- ----------------------------------------------------------------------------
-- Profile-specific, versioned approval snapshots for generated blueprints.
-- Generated suggestions remain transient; only an explicit human-created draft
-- snapshot enters this operational layer. Task materialization is allowed only
-- from an APPROVED snapshot and is idempotent per approved action.
--
-- Recovery: restore the pre-023 backup. This additive migration does not alter
-- Master Catalog content. Existing profile data remains valid if 023 is absent.
-- ============================================================================

PRAGMA foreign_keys = ON;

INSERT OR IGNORE INTO schema_migrations(version,description)
VALUES ('023','Versioned blueprint approval, normalized rule lineage, and idempotent profile tasks');

CREATE TABLE approved_blueprints (
    id                         TEXT PRIMARY KEY,
    profile_id                 TEXT NOT NULL REFERENCES enterprise_profiles(id) ON DELETE CASCADE,
    artifact_id                TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE RESTRICT,
    profile_artifact_id        TEXT NOT NULL REFERENCES profile_artifacts(id) ON DELETE CASCADE,
    version                    INTEGER NOT NULL,
    parent_blueprint_id        TEXT REFERENCES approved_blueprints(id) ON DELETE RESTRICT,
    source_blueprint_id        TEXT NOT NULL,
    source_payload_hash        TEXT NOT NULL,
    engine_version             TEXT NOT NULL,
    blueprint_version          TEXT NOT NULL,
    rule_set_id                TEXT NOT NULL,
    rule_set_version           TEXT NOT NULL,
    rule_set_hash              TEXT NOT NULL,
    action_plan_type           TEXT NOT NULL,
    title                      TEXT NOT NULL,
    generation_confidence      REAL NOT NULL,
    generation_requires_review INTEGER NOT NULL DEFAULT 0,
    workflow_status            TEXT NOT NULL DEFAULT 'DRAFT',
    created_by                 TEXT NOT NULL,
    created_at                 TEXT NOT NULL DEFAULT (datetime('now')),
    submitted_by               TEXT,
    submitted_at               TEXT,
    approved_by                TEXT,
    approved_at                TEXT,
    closed_by                  TEXT,
    closed_at                  TEXT,
    change_summary             TEXT,
    review_resolution_note     TEXT,
    last_actor                 TEXT NOT NULL,
    last_actor_role            TEXT NOT NULL,
    updated_at                 TEXT NOT NULL DEFAULT (datetime('now')),
    row_version                INTEGER NOT NULL DEFAULT 1,
    UNIQUE(profile_artifact_id,version),
    CHECK (version>0),
    CHECK (length(source_payload_hash)=64 AND source_payload_hash NOT GLOB '*[^0-9A-Fa-f]*'),
    CHECK (length(rule_set_hash)=64 AND rule_set_hash NOT GLOB '*[^0-9A-Fa-f]*'),
    CHECK (generation_confidence>=0 AND generation_confidence<=1),
    CHECK (generation_requires_review IN (0,1)),
    CHECK (workflow_status IN ('DRAFT','UNDER_REVIEW','APPROVED','SUPERSEDED','CANCELLED')),
    CHECK (last_actor_role IN ('AUTHOR','REVIEWER','APPROVER','SYSTEM')),
    CHECK (row_version>0)
);

CREATE UNIQUE INDEX uq_blueprint_one_candidate
    ON approved_blueprints(profile_artifact_id)
    WHERE workflow_status IN ('DRAFT','UNDER_REVIEW');
CREATE UNIQUE INDEX uq_blueprint_one_approved
    ON approved_blueprints(profile_artifact_id)
    WHERE workflow_status='APPROVED';
CREATE INDEX idx_blueprint_profile_status
    ON approved_blueprints(profile_id,workflow_status,updated_at DESC);
CREATE INDEX idx_blueprint_artifact_version
    ON approved_blueprints(profile_artifact_id,version DESC);

CREATE TABLE approved_blueprint_rules (
    blueprint_id      TEXT NOT NULL REFERENCES approved_blueprints(id) ON DELETE CASCADE,
    rule_id           TEXT NOT NULL,
    rule_version      TEXT NOT NULL,
    stage             TEXT NOT NULL,
    priority          INTEGER NOT NULL,
    rationale         TEXT NOT NULL,
    base_confidence   REAL NOT NULL,
    PRIMARY KEY(blueprint_id,rule_id,rule_version),
    CHECK (stage IN ('ARTIFACT_TYPE','CONTROL_NATURE','CONTROL_FUNCTION','SECURITY_DOMAIN','OBLIGATION_LEVEL')),
    CHECK (base_confidence>=0 AND base_confidence<=1)
);

CREATE TABLE approved_blueprint_actions (
    id                     TEXT PRIMARY KEY,
    blueprint_id           TEXT NOT NULL REFERENCES approved_blueprints(id) ON DELETE CASCADE,
    source_action_id       TEXT NOT NULL,
    action_code            TEXT NOT NULL,
    semantic_key           TEXT NOT NULL,
    title                  TEXT NOT NULL,
    description            TEXT NOT NULL,
    category               TEXT NOT NULL,
    phase                  TEXT NOT NULL,
    display_order          INTEGER NOT NULL,
    rationale              TEXT NOT NULL,
    confidence             REAL NOT NULL,
    taskable               INTEGER NOT NULL DEFAULT 1,
    requires_human_review  INTEGER NOT NULL DEFAULT 0,
    source_artifact_id     TEXT,
    source_citation        TEXT,
    UNIQUE(blueprint_id,semantic_key),
    UNIQUE(blueprint_id,source_action_id),
    CHECK (display_order>0),
    CHECK (confidence>=0 AND confidence<=1),
    CHECK (taskable IN (0,1)),
    CHECK (requires_human_review IN (0,1))
);
CREATE INDEX idx_blueprint_actions_order
    ON approved_blueprint_actions(blueprint_id,display_order,id);

CREATE TABLE approved_blueprint_action_rules (
    action_id       TEXT NOT NULL REFERENCES approved_blueprint_actions(id) ON DELETE CASCADE,
    rule_id         TEXT NOT NULL,
    rule_version    TEXT NOT NULL,
    PRIMARY KEY(action_id,rule_id,rule_version)
);

CREATE TABLE approved_blueprint_outputs (
    id                TEXT PRIMARY KEY,
    blueprint_id      TEXT NOT NULL REFERENCES approved_blueprints(id) ON DELETE CASCADE,
    source_output_id  TEXT NOT NULL,
    output_code       TEXT NOT NULL,
    semantic_key      TEXT NOT NULL,
    title             TEXT NOT NULL,
    description       TEXT NOT NULL,
    rationale         TEXT NOT NULL,
    UNIQUE(blueprint_id,semantic_key),
    UNIQUE(blueprint_id,source_output_id)
);

CREATE TABLE approved_blueprint_output_rules (
    output_id       TEXT NOT NULL REFERENCES approved_blueprint_outputs(id) ON DELETE CASCADE,
    rule_id         TEXT NOT NULL,
    rule_version    TEXT NOT NULL,
    PRIMARY KEY(output_id,rule_id,rule_version)
);

CREATE TABLE approved_blueprint_evidence (
    id                     TEXT PRIMARY KEY,
    blueprint_id           TEXT NOT NULL REFERENCES approved_blueprints(id) ON DELETE CASCADE,
    source_evidence_id     TEXT NOT NULL,
    evidence_code          TEXT NOT NULL,
    semantic_key           TEXT NOT NULL,
    title                  TEXT NOT NULL,
    evidence_type          TEXT NOT NULL,
    description            TEXT NOT NULL,
    rationale              TEXT NOT NULL,
    mandatory              INTEGER NOT NULL DEFAULT 0,
    confidence             REAL NOT NULL,
    requires_human_review  INTEGER NOT NULL DEFAULT 0,
    source_artifact_id     TEXT,
    source_citation        TEXT,
    UNIQUE(blueprint_id,semantic_key),
    UNIQUE(blueprint_id,source_evidence_id),
    CHECK (evidence_type IN ('DOCUMENT','SCREENSHOT','LOG','REPORT','CONFIG','ATTESTATION','LINK','OTHER')),
    CHECK (mandatory IN (0,1)),
    CHECK (confidence>=0 AND confidence<=1),
    CHECK (requires_human_review IN (0,1))
);
CREATE INDEX idx_blueprint_evidence_type
    ON approved_blueprint_evidence(blueprint_id,evidence_type,mandatory);

CREATE TABLE approved_blueprint_evidence_rules (
    evidence_id     TEXT NOT NULL REFERENCES approved_blueprint_evidence(id) ON DELETE CASCADE,
    rule_id         TEXT NOT NULL,
    rule_version    TEXT NOT NULL,
    PRIMARY KEY(evidence_id,rule_id,rule_version)
);

CREATE TABLE blueprint_review_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    blueprint_id    TEXT NOT NULL REFERENCES approved_blueprints(id) ON DELETE CASCADE,
    event_type      TEXT NOT NULL,
    status_from     TEXT,
    status_to       TEXT,
    actor           TEXT NOT NULL,
    actor_role      TEXT NOT NULL,
    note            TEXT,
    event_at        TEXT NOT NULL DEFAULT (datetime('now')),
    CHECK (event_type IN ('CREATED','SUBMITTED','RETURNED','APPROVED','SUPERSEDED','CANCELLED','EDITED','TASKS_MATERIALIZED')),
    CHECK (actor_role IN ('AUTHOR','REVIEWER','APPROVER','SYSTEM'))
);
CREATE INDEX idx_blueprint_events
    ON blueprint_review_events(blueprint_id,event_at,id);

CREATE TABLE approved_blueprint_review_findings (
    id               TEXT PRIMARY KEY,
    blueprint_id     TEXT NOT NULL REFERENCES approved_blueprints(id) ON DELETE CASCADE,
    finding_type     TEXT NOT NULL,
    finding_code     TEXT NOT NULL,
    field_name       TEXT,
    input_value      TEXT,
    canonical_value  TEXT,
    detail           TEXT NOT NULL,
    quality          REAL,
    CHECK (finding_type IN ('REVIEW_REASON','NORMALIZATION','CONFLICT')),
    CHECK (quality IS NULL OR (quality>=0 AND quality<=1))
);
CREATE INDEX idx_blueprint_review_findings
    ON approved_blueprint_review_findings(blueprint_id,finding_type,finding_code);

CREATE TABLE profile_tasks (
    id                    TEXT PRIMARY KEY,
    profile_id            TEXT NOT NULL REFERENCES enterprise_profiles(id) ON DELETE CASCADE,
    profile_artifact_id   TEXT NOT NULL REFERENCES profile_artifacts(id) ON DELETE CASCADE,
    blueprint_id          TEXT NOT NULL REFERENCES approved_blueprints(id) ON DELETE RESTRICT,
    blueprint_action_id   TEXT NOT NULL REFERENCES approved_blueprint_actions(id) ON DELETE RESTRICT,
    source_semantic_key   TEXT NOT NULL,
    title                 TEXT NOT NULL,
    description           TEXT NOT NULL,
    status                TEXT NOT NULL DEFAULT 'TODO',
    priority              TEXT,
    assigned_to           TEXT,
    due_date              TEXT,
    created_by            TEXT NOT NULL,
    last_changed_by       TEXT NOT NULL,
    created_at            TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at            TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at          TEXT,
    closed_by             TEXT,
    last_change_note      TEXT,
    UNIQUE(blueprint_action_id),
    CHECK (status IN ('TODO','IN_PROGRESS','BLOCKED','DONE','CANCELLED')),
    CHECK (priority IS NULL OR priority IN ('PRI-CRITICAL','PRI-HIGH','PRI-MEDIUM','PRI-LOW'))
);
CREATE INDEX idx_profile_tasks_work_queue
    ON profile_tasks(profile_id,status,due_date,priority);
CREATE INDEX idx_profile_tasks_blueprint
    ON profile_tasks(blueprint_id,blueprint_action_id);

CREATE TABLE profile_task_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id         TEXT NOT NULL REFERENCES profile_tasks(id) ON DELETE CASCADE,
    event_type      TEXT NOT NULL,
    status_from     TEXT,
    status_to       TEXT,
    actor           TEXT NOT NULL,
    note            TEXT,
    event_at        TEXT NOT NULL DEFAULT (datetime('now')),
    CHECK (event_type IN ('CREATED','STARTED','BLOCKED','RESUMED','COMPLETED','CANCELLED','UPDATED'))
);
CREATE INDEX idx_profile_task_events ON profile_task_events(task_id,event_at,id);

-- Profile/artifact lineage and insert-state invariants.
CREATE TRIGGER trg_blueprint_validate_insert
BEFORE INSERT ON approved_blueprints
BEGIN
    SELECT CASE WHEN NEW.workflow_status<>'DRAFT'
      THEN RAISE(ABORT,'blueprint must be created as DRAFT') END;
    SELECT CASE WHEN NOT EXISTS (
        SELECT 1 FROM profile_artifacts pa
         WHERE pa.id=NEW.profile_artifact_id
           AND pa.profile_id=NEW.profile_id
           AND pa.artifact_id=NEW.artifact_id
    ) THEN RAISE(ABORT,'blueprint must match profile artifact and catalog artifact') END;
    SELECT CASE WHEN NEW.parent_blueprint_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM approved_blueprints p
         WHERE p.id=NEW.parent_blueprint_id
           AND p.profile_artifact_id=NEW.profile_artifact_id
           AND p.version<NEW.version
    ) THEN RAISE(ABORT,'parent blueprint must be an earlier version for the same profile artifact') END;
END;

CREATE TRIGGER trg_blueprint_identity_immutable
BEFORE UPDATE OF profile_id,artifact_id,profile_artifact_id,version,parent_blueprint_id,
                 source_blueprint_id,source_payload_hash,engine_version,blueprint_version,
                 rule_set_id,rule_set_version,rule_set_hash,action_plan_type,
                 generation_confidence,generation_requires_review,created_by,created_at
ON approved_blueprints
BEGIN
    SELECT RAISE(ABORT,'blueprint identity and generation provenance are immutable');
END;

CREATE TRIGGER trg_blueprint_state_machine
BEFORE UPDATE OF workflow_status ON approved_blueprints
WHEN OLD.workflow_status<>NEW.workflow_status
BEGIN
    SELECT CASE WHEN NOT (
        (OLD.workflow_status='DRAFT' AND NEW.workflow_status IN ('UNDER_REVIEW','CANCELLED')) OR
        (OLD.workflow_status='UNDER_REVIEW' AND NEW.workflow_status IN ('DRAFT','APPROVED','CANCELLED')) OR
        (OLD.workflow_status='APPROVED' AND NEW.workflow_status='SUPERSEDED')
    ) THEN RAISE(ABORT,'invalid blueprint workflow transition') END;
    SELECT CASE WHEN NEW.workflow_status='UNDER_REVIEW'
      AND (NEW.submitted_by IS NULL OR NEW.submitted_at IS NULL OR NEW.last_actor_role<>'AUTHOR')
      THEN RAISE(ABORT,'submission requires author and timestamp') END;
    SELECT CASE WHEN NEW.workflow_status='UNDER_REVIEW' AND (
        NOT EXISTS (SELECT 1 FROM approved_blueprint_actions a WHERE a.blueprint_id=NEW.id) OR
        NOT EXISTS (SELECT 1 FROM approved_blueprint_evidence e WHERE e.blueprint_id=NEW.id) OR
        EXISTS (SELECT 1 FROM approved_blueprint_actions a
                 WHERE a.blueprint_id=NEW.id AND NOT EXISTS (
                    SELECT 1 FROM approved_blueprint_action_rules r WHERE r.action_id=a.id)) OR
        EXISTS (SELECT 1 FROM approved_blueprint_evidence e
                 WHERE e.blueprint_id=NEW.id AND NOT EXISTS (
                    SELECT 1 FROM approved_blueprint_evidence_rules r WHERE r.evidence_id=e.id)) OR
        EXISTS (SELECT 1 FROM approved_blueprint_action_rules ar
                 JOIN approved_blueprint_actions a ON a.id=ar.action_id
                 WHERE a.blueprint_id=NEW.id AND NOT EXISTS (
                    SELECT 1 FROM approved_blueprint_rules r
                     WHERE r.blueprint_id=NEW.id AND r.rule_id=ar.rule_id
                       AND r.rule_version=ar.rule_version)) OR
        EXISTS (SELECT 1 FROM approved_blueprint_output_rules x
                 JOIN approved_blueprint_outputs o ON o.id=x.output_id
                 WHERE o.blueprint_id=NEW.id AND NOT EXISTS (
                    SELECT 1 FROM approved_blueprint_rules r
                     WHERE r.blueprint_id=NEW.id AND r.rule_id=x.rule_id
                       AND r.rule_version=x.rule_version)) OR
        EXISTS (SELECT 1 FROM approved_blueprint_evidence_rules er
                 JOIN approved_blueprint_evidence e ON e.id=er.evidence_id
                 WHERE e.blueprint_id=NEW.id AND NOT EXISTS (
                    SELECT 1 FROM approved_blueprint_rules r
                     WHERE r.blueprint_id=NEW.id AND r.rule_id=er.rule_id
                       AND r.rule_version=er.rule_version))
    ) THEN RAISE(ABORT,'submission requires actions, evidence, and normalized rule lineage') END;
    SELECT CASE WHEN NEW.workflow_status='DRAFT' AND NEW.last_actor_role<>'REVIEWER'
      THEN RAISE(ABORT,'return to draft requires reviewer role') END;
    SELECT CASE WHEN NEW.workflow_status='APPROVED'
      AND (NEW.approved_by IS NULL OR NEW.approved_at IS NULL OR NEW.last_actor_role<>'APPROVER')
      THEN RAISE(ABORT,'approval requires approver and timestamp') END;
    SELECT CASE WHEN NEW.workflow_status='APPROVED'
      AND NEW.generation_requires_review=1
      AND (NEW.review_resolution_note IS NULL OR trim(NEW.review_resolution_note)='')
      THEN RAISE(ABORT,'review resolution note is required for generated review flags') END;
    SELECT CASE WHEN NEW.workflow_status IN ('SUPERSEDED','CANCELLED')
      AND (NEW.closed_by IS NULL OR NEW.closed_at IS NULL)
      THEN RAISE(ABORT,'terminal blueprint state requires closer and timestamp') END;
END;

CREATE TRIGGER trg_blueprint_content_lock
BEFORE UPDATE OF title,change_summary ON approved_blueprints
WHEN OLD.workflow_status<>'DRAFT'
BEGIN SELECT RAISE(ABORT,'blueprint content is editable only in DRAFT'); END;

CREATE TRIGGER trg_blueprint_finding_insert_draft
BEFORE INSERT ON approved_blueprint_review_findings
WHEN NOT EXISTS (SELECT 1 FROM approved_blueprints b WHERE b.id=NEW.blueprint_id AND b.workflow_status='DRAFT')
BEGIN SELECT RAISE(ABORT,'blueprint review findings are editable only in DRAFT'); END;
CREATE TRIGGER trg_blueprint_finding_update_draft
BEFORE UPDATE ON approved_blueprint_review_findings
WHEN NOT EXISTS (SELECT 1 FROM approved_blueprints b WHERE b.id=OLD.blueprint_id AND b.workflow_status='DRAFT')
  OR NOT EXISTS (SELECT 1 FROM approved_blueprints b WHERE b.id=NEW.blueprint_id AND b.workflow_status='DRAFT')
BEGIN SELECT RAISE(ABORT,'blueprint review findings are editable only in DRAFT'); END;
CREATE TRIGGER trg_blueprint_finding_delete_draft
BEFORE DELETE ON approved_blueprint_review_findings
WHEN NOT EXISTS (SELECT 1 FROM approved_blueprints b WHERE b.id=OLD.blueprint_id AND b.workflow_status='DRAFT')
BEGIN SELECT RAISE(ABORT,'blueprint review findings are editable only in DRAFT'); END;

CREATE TRIGGER trg_blueprint_event_insert
AFTER INSERT ON approved_blueprints
BEGIN
    INSERT INTO blueprint_review_events(
        blueprint_id,event_type,status_to,actor,actor_role,note)
    VALUES(NEW.id,'CREATED','DRAFT',NEW.created_by,NEW.last_actor_role,NEW.change_summary);
END;

CREATE TRIGGER trg_blueprint_event_status
AFTER UPDATE OF workflow_status ON approved_blueprints
WHEN OLD.workflow_status<>NEW.workflow_status
BEGIN
    INSERT INTO blueprint_review_events(
        blueprint_id,event_type,status_from,status_to,actor,actor_role,note)
    VALUES(
        NEW.id,
        CASE NEW.workflow_status
          WHEN 'UNDER_REVIEW' THEN 'SUBMITTED'
          WHEN 'DRAFT' THEN 'RETURNED'
          WHEN 'APPROVED' THEN 'APPROVED'
          WHEN 'SUPERSEDED' THEN 'SUPERSEDED'
          ELSE 'CANCELLED'
        END,
        OLD.workflow_status,NEW.workflow_status,NEW.last_actor,NEW.last_actor_role,
        COALESCE(NEW.review_resolution_note,NEW.change_summary)
    );
END;

-- Snapshot children may be edited only while the parent is a draft.
CREATE TRIGGER trg_blueprint_action_insert_draft
BEFORE INSERT ON approved_blueprint_actions
WHEN NOT EXISTS (SELECT 1 FROM approved_blueprints b WHERE b.id=NEW.blueprint_id AND b.workflow_status='DRAFT')
BEGIN SELECT RAISE(ABORT,'blueprint actions are editable only in DRAFT'); END;
CREATE TRIGGER trg_blueprint_action_update_draft
BEFORE UPDATE ON approved_blueprint_actions
WHEN NOT EXISTS (SELECT 1 FROM approved_blueprints b WHERE b.id=OLD.blueprint_id AND b.workflow_status='DRAFT')
  OR NOT EXISTS (SELECT 1 FROM approved_blueprints b WHERE b.id=NEW.blueprint_id AND b.workflow_status='DRAFT')
BEGIN SELECT RAISE(ABORT,'blueprint actions are editable only in DRAFT'); END;
CREATE TRIGGER trg_blueprint_action_delete_draft
BEFORE DELETE ON approved_blueprint_actions
WHEN NOT EXISTS (SELECT 1 FROM approved_blueprints b WHERE b.id=OLD.blueprint_id AND b.workflow_status='DRAFT')
BEGIN SELECT RAISE(ABORT,'blueprint actions are editable only in DRAFT'); END;

CREATE TRIGGER trg_blueprint_evidence_insert_draft
BEFORE INSERT ON approved_blueprint_evidence
WHEN NOT EXISTS (SELECT 1 FROM approved_blueprints b WHERE b.id=NEW.blueprint_id AND b.workflow_status='DRAFT')
BEGIN SELECT RAISE(ABORT,'blueprint evidence is editable only in DRAFT'); END;
CREATE TRIGGER trg_blueprint_evidence_update_draft
BEFORE UPDATE ON approved_blueprint_evidence
WHEN NOT EXISTS (SELECT 1 FROM approved_blueprints b WHERE b.id=OLD.blueprint_id AND b.workflow_status='DRAFT')
  OR NOT EXISTS (SELECT 1 FROM approved_blueprints b WHERE b.id=NEW.blueprint_id AND b.workflow_status='DRAFT')
BEGIN SELECT RAISE(ABORT,'blueprint evidence is editable only in DRAFT'); END;

CREATE TRIGGER trg_blueprint_rule_insert_draft
BEFORE INSERT ON approved_blueprint_rules
WHEN NOT EXISTS (SELECT 1 FROM approved_blueprints b WHERE b.id=NEW.blueprint_id AND b.workflow_status='DRAFT')
BEGIN SELECT RAISE(ABORT,'blueprint rules are editable only in DRAFT'); END;
CREATE TRIGGER trg_blueprint_rule_update_draft
BEFORE UPDATE ON approved_blueprint_rules
WHEN NOT EXISTS (SELECT 1 FROM approved_blueprints b WHERE b.id=OLD.blueprint_id AND b.workflow_status='DRAFT')
  OR NOT EXISTS (SELECT 1 FROM approved_blueprints b WHERE b.id=NEW.blueprint_id AND b.workflow_status='DRAFT')
BEGIN SELECT RAISE(ABORT,'blueprint rules are editable only in DRAFT'); END;
CREATE TRIGGER trg_blueprint_rule_delete_draft
BEFORE DELETE ON approved_blueprint_rules
WHEN NOT EXISTS (SELECT 1 FROM approved_blueprints b WHERE b.id=OLD.blueprint_id AND b.workflow_status='DRAFT')
BEGIN SELECT RAISE(ABORT,'blueprint rules are editable only in DRAFT'); END;

CREATE TRIGGER trg_blueprint_output_insert_draft
BEFORE INSERT ON approved_blueprint_outputs
WHEN NOT EXISTS (SELECT 1 FROM approved_blueprints b WHERE b.id=NEW.blueprint_id AND b.workflow_status='DRAFT')
BEGIN SELECT RAISE(ABORT,'blueprint outputs are editable only in DRAFT'); END;
CREATE TRIGGER trg_blueprint_output_update_draft
BEFORE UPDATE ON approved_blueprint_outputs
WHEN NOT EXISTS (SELECT 1 FROM approved_blueprints b WHERE b.id=OLD.blueprint_id AND b.workflow_status='DRAFT')
  OR NOT EXISTS (SELECT 1 FROM approved_blueprints b WHERE b.id=NEW.blueprint_id AND b.workflow_status='DRAFT')
BEGIN SELECT RAISE(ABORT,'blueprint outputs are editable only in DRAFT'); END;
CREATE TRIGGER trg_blueprint_output_delete_draft
BEFORE DELETE ON approved_blueprint_outputs
WHEN NOT EXISTS (SELECT 1 FROM approved_blueprints b WHERE b.id=OLD.blueprint_id AND b.workflow_status='DRAFT')
BEGIN SELECT RAISE(ABORT,'blueprint outputs are editable only in DRAFT'); END;

CREATE TRIGGER trg_blueprint_action_rule_lock_insert
BEFORE INSERT ON approved_blueprint_action_rules
WHEN NOT EXISTS (
    SELECT 1 FROM approved_blueprint_actions a JOIN approved_blueprints b ON b.id=a.blueprint_id
     WHERE a.id=NEW.action_id AND b.workflow_status='DRAFT')
BEGIN SELECT RAISE(ABORT,'action rule sources are editable only in DRAFT'); END;
CREATE TRIGGER trg_blueprint_action_rule_lock_update
BEFORE UPDATE ON approved_blueprint_action_rules
WHEN NOT EXISTS (
    SELECT 1 FROM approved_blueprint_actions a JOIN approved_blueprints b ON b.id=a.blueprint_id
     WHERE a.id=OLD.action_id AND b.workflow_status='DRAFT')
  OR NOT EXISTS (
    SELECT 1 FROM approved_blueprint_actions a JOIN approved_blueprints b ON b.id=a.blueprint_id
     WHERE a.id=NEW.action_id AND b.workflow_status='DRAFT')
BEGIN SELECT RAISE(ABORT,'action rule sources are editable only in DRAFT'); END;
CREATE TRIGGER trg_blueprint_action_rule_lock_delete
BEFORE DELETE ON approved_blueprint_action_rules
WHEN NOT EXISTS (
    SELECT 1 FROM approved_blueprint_actions a JOIN approved_blueprints b ON b.id=a.blueprint_id
     WHERE a.id=OLD.action_id AND b.workflow_status='DRAFT')
BEGIN SELECT RAISE(ABORT,'action rule sources are editable only in DRAFT'); END;

CREATE TRIGGER trg_blueprint_output_rule_lock_insert
BEFORE INSERT ON approved_blueprint_output_rules
WHEN NOT EXISTS (
    SELECT 1 FROM approved_blueprint_outputs o JOIN approved_blueprints b ON b.id=o.blueprint_id
     WHERE o.id=NEW.output_id AND b.workflow_status='DRAFT')
BEGIN SELECT RAISE(ABORT,'output rule sources are editable only in DRAFT'); END;
CREATE TRIGGER trg_blueprint_output_rule_lock_update
BEFORE UPDATE ON approved_blueprint_output_rules
WHEN NOT EXISTS (
    SELECT 1 FROM approved_blueprint_outputs o JOIN approved_blueprints b ON b.id=o.blueprint_id
     WHERE o.id=OLD.output_id AND b.workflow_status='DRAFT')
  OR NOT EXISTS (
    SELECT 1 FROM approved_blueprint_outputs o JOIN approved_blueprints b ON b.id=o.blueprint_id
     WHERE o.id=NEW.output_id AND b.workflow_status='DRAFT')
BEGIN SELECT RAISE(ABORT,'output rule sources are editable only in DRAFT'); END;
CREATE TRIGGER trg_blueprint_output_rule_lock_delete
BEFORE DELETE ON approved_blueprint_output_rules
WHEN NOT EXISTS (
    SELECT 1 FROM approved_blueprint_outputs o JOIN approved_blueprints b ON b.id=o.blueprint_id
     WHERE o.id=OLD.output_id AND b.workflow_status='DRAFT')
BEGIN SELECT RAISE(ABORT,'output rule sources are editable only in DRAFT'); END;

CREATE TRIGGER trg_blueprint_evidence_rule_lock_insert
BEFORE INSERT ON approved_blueprint_evidence_rules
WHEN NOT EXISTS (
    SELECT 1 FROM approved_blueprint_evidence e JOIN approved_blueprints b ON b.id=e.blueprint_id
     WHERE e.id=NEW.evidence_id AND b.workflow_status='DRAFT')
BEGIN SELECT RAISE(ABORT,'evidence rule sources are editable only in DRAFT'); END;
CREATE TRIGGER trg_blueprint_evidence_rule_lock_update
BEFORE UPDATE ON approved_blueprint_evidence_rules
WHEN NOT EXISTS (
    SELECT 1 FROM approved_blueprint_evidence e JOIN approved_blueprints b ON b.id=e.blueprint_id
     WHERE e.id=OLD.evidence_id AND b.workflow_status='DRAFT')
  OR NOT EXISTS (
    SELECT 1 FROM approved_blueprint_evidence e JOIN approved_blueprints b ON b.id=e.blueprint_id
     WHERE e.id=NEW.evidence_id AND b.workflow_status='DRAFT')
BEGIN SELECT RAISE(ABORT,'evidence rule sources are editable only in DRAFT'); END;
CREATE TRIGGER trg_blueprint_evidence_rule_lock_delete
BEFORE DELETE ON approved_blueprint_evidence_rules
WHEN NOT EXISTS (
    SELECT 1 FROM approved_blueprint_evidence e JOIN approved_blueprints b ON b.id=e.blueprint_id
     WHERE e.id=OLD.evidence_id AND b.workflow_status='DRAFT')
BEGIN SELECT RAISE(ABORT,'evidence rule sources are editable only in DRAFT'); END;
CREATE TRIGGER trg_blueprint_evidence_delete_draft
BEFORE DELETE ON approved_blueprint_evidence
WHEN NOT EXISTS (SELECT 1 FROM approved_blueprints b WHERE b.id=OLD.blueprint_id AND b.workflow_status='DRAFT')
BEGIN SELECT RAISE(ABORT,'blueprint evidence is editable only in DRAFT'); END;

-- Every per-item rule source must exist in the same blueprint rule snapshot.
CREATE TRIGGER trg_blueprint_action_rule_validate
BEFORE INSERT ON approved_blueprint_action_rules
BEGIN
    SELECT CASE WHEN NOT EXISTS (
        SELECT 1 FROM approved_blueprint_actions a
        JOIN approved_blueprint_rules r ON r.blueprint_id=a.blueprint_id
         WHERE a.id=NEW.action_id AND r.rule_id=NEW.rule_id AND r.rule_version=NEW.rule_version
    ) THEN RAISE(ABORT,'action source rule must belong to the same blueprint') END;
END;
CREATE TRIGGER trg_blueprint_output_rule_validate
BEFORE INSERT ON approved_blueprint_output_rules
BEGIN
    SELECT CASE WHEN NOT EXISTS (
        SELECT 1 FROM approved_blueprint_outputs o
        JOIN approved_blueprint_rules r ON r.blueprint_id=o.blueprint_id
         WHERE o.id=NEW.output_id AND r.rule_id=NEW.rule_id AND r.rule_version=NEW.rule_version
    ) THEN RAISE(ABORT,'output source rule must belong to the same blueprint') END;
END;
CREATE TRIGGER trg_blueprint_evidence_rule_validate
BEFORE INSERT ON approved_blueprint_evidence_rules
BEGIN
    SELECT CASE WHEN NOT EXISTS (
        SELECT 1 FROM approved_blueprint_evidence e
        JOIN approved_blueprint_rules r ON r.blueprint_id=e.blueprint_id
         WHERE e.id=NEW.evidence_id AND r.rule_id=NEW.rule_id AND r.rule_version=NEW.rule_version
    ) THEN RAISE(ABORT,'evidence source rule must belong to the same blueprint') END;
END;

-- Task creation is profile-safe and approval-gated at the storage boundary.
CREATE TRIGGER trg_profile_task_validate_insert
BEFORE INSERT ON profile_tasks
BEGIN
    SELECT CASE WHEN NEW.status<>'TODO'
      THEN RAISE(ABORT,'materialized task must start as TODO') END;
    SELECT CASE WHEN NOT EXISTS (
        SELECT 1 FROM approved_blueprints b
        JOIN approved_blueprint_actions a ON a.blueprint_id=b.id
        JOIN profile_artifacts pa ON pa.id=b.profile_artifact_id
         WHERE b.id=NEW.blueprint_id
           AND a.id=NEW.blueprint_action_id
           AND a.taskable=1
           AND b.workflow_status='APPROVED'
           AND b.profile_id=NEW.profile_id
           AND b.profile_artifact_id=NEW.profile_artifact_id
           AND pa.profile_id=NEW.profile_id
    ) THEN RAISE(ABORT,'tasks require a taskable action from an approved matching-profile blueprint') END;
END;

CREATE TRIGGER trg_profile_task_state_machine
BEFORE UPDATE OF status ON profile_tasks
WHEN OLD.status<>NEW.status
BEGIN
    SELECT CASE WHEN OLD.status IN ('DONE','CANCELLED')
      THEN RAISE(ABORT,'terminal task status is immutable') END;
    SELECT CASE WHEN NOT (
        (OLD.status='TODO' AND NEW.status IN ('IN_PROGRESS','BLOCKED','DONE','CANCELLED')) OR
        (OLD.status='IN_PROGRESS' AND NEW.status IN ('BLOCKED','DONE','CANCELLED')) OR
        (OLD.status='BLOCKED' AND NEW.status IN ('TODO','IN_PROGRESS','CANCELLED'))
    ) THEN RAISE(ABORT,'invalid task status transition') END;
    SELECT CASE WHEN NEW.status IN ('DONE','CANCELLED')
      AND (NEW.closed_by IS NULL OR NEW.completed_at IS NULL)
      THEN RAISE(ABORT,'terminal task status requires closer and timestamp') END;
END;

CREATE TRIGGER trg_profile_task_event_insert
AFTER INSERT ON profile_tasks
BEGIN
    INSERT INTO profile_task_events(task_id,event_type,status_to,actor,note)
    VALUES(NEW.id,'CREATED','TODO',NEW.last_changed_by,NEW.last_change_note);
END;

CREATE TRIGGER trg_profile_task_event_status
AFTER UPDATE OF status ON profile_tasks
WHEN OLD.status<>NEW.status
BEGIN
    INSERT INTO profile_task_events(task_id,event_type,status_from,status_to,actor,note)
    VALUES(
        NEW.id,
        CASE NEW.status
          WHEN 'IN_PROGRESS' THEN CASE OLD.status WHEN 'BLOCKED' THEN 'RESUMED' ELSE 'STARTED' END
          WHEN 'BLOCKED' THEN 'BLOCKED'
          WHEN 'TODO' THEN 'RESUMED'
          WHEN 'DONE' THEN 'COMPLETED'
          ELSE 'CANCELLED'
        END,
        OLD.status,NEW.status,NEW.last_changed_by,NEW.last_change_note
    );
END;

CREATE TRIGGER trg_profile_task_touch
AFTER UPDATE OF status,priority,assigned_to,due_date,last_change_note ON profile_tasks
WHEN NEW.updated_at=OLD.updated_at
BEGIN
    UPDATE profile_tasks SET updated_at=datetime('now') WHERE id=NEW.id;
END;

CREATE VIEW v_profile_blueprints AS
SELECT b.*,
       a.title_en AS artifact_title_en,
       a.title_ar AS artifact_title_ar,
       (SELECT COUNT(*) FROM approved_blueprint_actions x WHERE x.blueprint_id=b.id) AS action_count,
       (SELECT COUNT(*) FROM approved_blueprint_evidence e WHERE e.blueprint_id=b.id) AS evidence_count,
       (SELECT COUNT(*) FROM profile_tasks t WHERE t.blueprint_id=b.id) AS task_count
  FROM approved_blueprints b
  JOIN security_artifacts a ON a.id=b.artifact_id;

CREATE VIEW v_profile_task_queue AS
SELECT t.*,b.version AS blueprint_version_number,b.action_plan_type,
       a.artifact_id,sa.title_en AS artifact_title_en,sa.primary_domain,sa.sub_domain
  FROM profile_tasks t
  JOIN approved_blueprints b ON b.id=t.blueprint_id
  JOIN profile_artifacts a ON a.id=t.profile_artifact_id
  JOIN security_artifacts sa ON sa.id=a.artifact_id;

CREATE VIEW v_blueprint_governance_issues AS
SELECT b.id AS blueprint_id,b.profile_id,b.artifact_id,b.profile_artifact_id,
       CASE
         WHEN pa.id IS NULL THEN 'MISSING_PROFILE_ARTIFACT'
         WHEN pa.profile_id<>b.profile_id OR pa.artifact_id<>b.artifact_id THEN 'PROFILE_ARTIFACT_MISMATCH'
         WHEN b.workflow_status='APPROVED' AND (b.approved_by IS NULL OR b.approved_at IS NULL) THEN 'APPROVED_WITHOUT_APPROVER'
         WHEN b.workflow_status='APPROVED' AND b.generation_requires_review=1
              AND (b.review_resolution_note IS NULL OR trim(b.review_resolution_note)='') THEN 'UNRESOLVED_GENERATION_REVIEW'
       END AS issue_code
  FROM approved_blueprints b
  LEFT JOIN profile_artifacts pa ON pa.id=b.profile_artifact_id
 WHERE pa.id IS NULL
    OR pa.profile_id<>b.profile_id
    OR pa.artifact_id<>b.artifact_id
    OR (b.workflow_status='APPROVED' AND (b.approved_by IS NULL OR b.approved_at IS NULL))
    OR (b.workflow_status='APPROVED' AND b.generation_requires_review=1
        AND (b.review_resolution_note IS NULL OR trim(b.review_resolution_note)=''));
''',
  ),
  EmbeddedMigration(
    version: '024',
    filename: '024_blueprint_pattern_enrichment.sql',
    sha256: '886239dd36884e83eb93c100218fdd2386946d8a3ad4f82d205147407c51a54e',
    sql:
        r'''-- ============================================================================
-- SecureGuide — Migration 024: Blueprint Draft Enrichment from Operational Patterns
-- ----------------------------------------------------------------------------
-- Lets a human author attach a non-authoritative operational pattern to a DRAFT
-- blueprint as an explicit, reversible, provenance-preserving enrichment. The
-- enrichment stores a frozen COPY of the pattern text after the author's edits
-- (never a live reference), together with the library version and sha256, the
-- source pattern identity, and the actor/time/reason of the selection.
--
-- A pattern never becomes a task directly. It only informs a DRAFT snapshot that
-- still travels the same governed path: draft -> review -> approval -> tasks.
-- Enrichments are editable only while the blueprint is DRAFT; once the blueprint
-- leaves DRAFT they are frozen and travel with the approved snapshot as lineage.
--
-- Recovery: restore the pre-024 backup. This additive migration does not alter
-- Master Catalog content or any 023 table. Existing data remains valid if 024
-- is absent.
-- ============================================================================

PRAGMA foreign_keys = ON;

INSERT OR IGNORE INTO schema_migrations(version,description)
VALUES ('024','Reversible, provenance-preserving operational-pattern enrichment of draft blueprints');

CREATE TABLE approved_blueprint_pattern_enrichments (
    id                        TEXT PRIMARY KEY,
    blueprint_id              TEXT NOT NULL REFERENCES approved_blueprints(id) ON DELETE CASCADE,
    source_pattern_id         TEXT NOT NULL,
    pattern_source_row        INTEGER NOT NULL,
    library_id                TEXT NOT NULL,
    library_version           TEXT NOT NULL,
    library_sha256            TEXT NOT NULL,
    recommended_artifact_type TEXT NOT NULL,
    primary_domain            TEXT NOT NULL,
    sub_domain                TEXT NOT NULL,
    pattern_priority          TEXT NOT NULL,
    copied_title_ar           TEXT NOT NULL,
    copied_text_ar            TEXT NOT NULL,
    safety_review_required    INTEGER NOT NULL DEFAULT 0,
    safety_acknowledged       INTEGER NOT NULL DEFAULT 0,
    safety_note_ar            TEXT,
    selected_by               TEXT NOT NULL,
    selection_reason          TEXT NOT NULL,
    selected_at               TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(blueprint_id,source_pattern_id),
    CHECK (pattern_source_row>0),
    CHECK (source_pattern_id GLOB 'OPP-[0-9][0-9][0-9]'),
    CHECK (length(library_sha256)=64 AND library_sha256 NOT GLOB '*[^0-9A-Fa-f]*'),
    CHECK (safety_review_required IN (0,1)),
    CHECK (safety_acknowledged IN (0,1)),
    CHECK (safety_review_required=0 OR safety_acknowledged=1),
    CHECK (safety_review_required=0 OR (safety_note_ar IS NOT NULL AND trim(safety_note_ar)<>'')),
    CHECK (trim(copied_title_ar)<>'' AND trim(copied_text_ar)<>''),
    CHECK (trim(selection_reason)<>''),
    CHECK (substr(sub_domain,1,5)=primary_domain)
);
CREATE INDEX idx_bp_enrichment_blueprint
    ON approved_blueprint_pattern_enrichments(blueprint_id,selected_at,id);
CREATE INDEX idx_bp_enrichment_pattern
    ON approved_blueprint_pattern_enrichments(source_pattern_id);

-- Append-only timeline of enrichment additions and reversals. enrichment_id is a
-- plain value, not a foreign key, so the ADDED/REMOVED audit survives the removal
-- of the enrichment row itself. Rows cascade only when the blueprint is deleted.
CREATE TABLE blueprint_pattern_enrichment_events (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    blueprint_id      TEXT NOT NULL REFERENCES approved_blueprints(id) ON DELETE CASCADE,
    enrichment_id     TEXT NOT NULL,
    source_pattern_id TEXT NOT NULL,
    event_type        TEXT NOT NULL,
    actor             TEXT NOT NULL,
    reason            TEXT,
    event_at          TEXT NOT NULL DEFAULT (datetime('now')),
    CHECK (event_type IN ('ADDED','REMOVED'))
);
CREATE INDEX idx_bp_enrichment_events
    ON blueprint_pattern_enrichment_events(blueprint_id,event_at,id);

-- Enrichments are mutable only while their blueprint is a draft.
CREATE TRIGGER trg_bp_enrichment_insert_draft
BEFORE INSERT ON approved_blueprint_pattern_enrichments
WHEN NOT EXISTS (SELECT 1 FROM approved_blueprints b WHERE b.id=NEW.blueprint_id AND b.workflow_status='DRAFT')
BEGIN SELECT RAISE(ABORT,'blueprint pattern enrichments are editable only in DRAFT'); END;

CREATE TRIGGER trg_bp_enrichment_update_draft
BEFORE UPDATE ON approved_blueprint_pattern_enrichments
WHEN NOT EXISTS (SELECT 1 FROM approved_blueprints b WHERE b.id=OLD.blueprint_id AND b.workflow_status='DRAFT')
  OR NOT EXISTS (SELECT 1 FROM approved_blueprints b WHERE b.id=NEW.blueprint_id AND b.workflow_status='DRAFT')
BEGIN SELECT RAISE(ABORT,'blueprint pattern enrichments are editable only in DRAFT'); END;

CREATE TRIGGER trg_bp_enrichment_delete_draft
BEFORE DELETE ON approved_blueprint_pattern_enrichments
WHEN NOT EXISTS (SELECT 1 FROM approved_blueprints b WHERE b.id=OLD.blueprint_id AND b.workflow_status='DRAFT')
BEGIN SELECT RAISE(ABORT,'blueprint pattern enrichments are editable only in DRAFT'); END;

CREATE VIEW v_blueprint_pattern_enrichments AS
SELECT e.*,
       b.profile_id,
       b.profile_artifact_id,
       b.artifact_id,
       b.workflow_status,
       b.version AS blueprint_version_number,
       sa.title_en AS artifact_title_en,
       sa.title_ar AS artifact_title_ar
  FROM approved_blueprint_pattern_enrichments e
  JOIN approved_blueprints b ON b.id=e.blueprint_id
  JOIN security_artifacts sa ON sa.id=b.artifact_id;

CREATE VIEW v_blueprint_enrichment_governance_issues AS
SELECT e.id AS enrichment_id,e.blueprint_id,e.source_pattern_id,
       CASE
         WHEN e.safety_review_required=1 AND e.safety_acknowledged=0 THEN 'UNACKNOWLEDGED_SAFETY_PATTERN'
         WHEN length(e.library_sha256)<>64 THEN 'MISSING_LIBRARY_PROVENANCE'
         WHEN substr(e.sub_domain,1,5)<>e.primary_domain THEN 'DOMAIN_LINEAGE_MISMATCH'
       END AS issue_code
  FROM approved_blueprint_pattern_enrichments e
 WHERE (e.safety_review_required=1 AND e.safety_acknowledged=0)
    OR length(e.library_sha256)<>64
    OR substr(e.sub_domain,1,5)<>e.primary_domain;
''',
  ),
  EmbeddedMigration(
    version: '025',
    filename: '025_view_overrides.sql',
    sha256: 'd4e1710e0fabfaa07a408eb1b67366fd10a2676e95dfa765c56f2d4fa1bc971d',
    sql:
        r'''-- ============================================================================
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
''',
  ),
  EmbeddedMigration(
    version: '026',
    filename: '026_performance_indexes.sql',
    sha256: 'bae59643f803ca7c3ed7013a30a325c85a1b6b41f30662f811f2d38f6714f083',
    sql:
        r'''-- ============================================================================
-- SecureGuide — Migration 026: Performance Indexes
-- ============================================================================

PRAGMA foreign_keys = ON;

INSERT OR IGNORE INTO schema_migrations (version, description)
VALUES ('026', 'Add strategic indexes for catalog search performance');

CREATE INDEX IF NOT EXISTS idx_artifacts_source ON security_artifacts(source);
''',
  ),
  EmbeddedMigration(
    version: '027',
    filename: '027_profile_archival.sql',
    sha256: '4ed4129436eb116321344017719f432ff38b0953c6d3449a7ae29ef4825bfa6c',
    sql:
        r'''-- SecureGuide migration 027: non-destructive enterprise-profile archival.
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
''',
  ),
  EmbeddedMigration(
    version: '028',
    filename: '028_locale_preference.sql',
    sha256: '7c59280e2758a2820b16e5842bd0ec249b906e1877fdb631b1f42654bd19bb5f',
    sql:
        r'''-- ============================================================================
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
''',
  ),
  EmbeddedMigration(
    version: '029',
    filename: '029_evidence_file_size.sql',
    sha256: 'bc1367f9ae8403fa15f0ca5171f5f81e695a3e7d1716557e3111af6e355fc138',
    sql:
        r'''-- ============================================================================
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
''',
  ),
  EmbeddedMigration(
    version: '030',
    filename: '030_localized_gap_read_model.sql',
    sha256: 'c8cbd22ba2510c422983f8d5f3ab99ac463654051d8c72c9ed0884666c164055',
    sql:
        r'''-- ============================================================================
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
''',
  ),
  EmbeddedMigration(
    version: '031',
    filename: '031_catalog_closure_foundation.sql',
    sha256: 'fc71e88c79109dfc93b6a7275c929180eb9e4a5a1d3147e4699a030d2c27a48d',
    sql:
        r'''-- ============================================================================
-- SecureGuide - Migration 031: Catalog Closure Foundation
-- ----------------------------------------------------------------------------
-- Adds durable source manifests, versioned source-rights decisions, exactly-one
-- raw dispositions, and normalized final raw-to-canonical lineage.
--
-- This migration is additive and contains no operational/profile state.
-- Recovery: restore the pre-migration working/installed database copy. Do not
-- drop closure facts after they are populated because they are release evidence.
-- ============================================================================

PRAGMA foreign_keys = ON;

INSERT OR IGNORE INTO schema_migrations (version, description)
VALUES ('031', 'Catalog closure: source manifests, rights, raw dispositions, and final lineage');

CREATE TABLE source_import_manifests (
    id                     TEXT PRIMARY KEY,
    source_catalog_id      TEXT NOT NULL REFERENCES source_catalogs(id) ON DELETE RESTRICT,
    source_version         TEXT NOT NULL,
    version_unknown_reason TEXT,
    source_file            TEXT NOT NULL,
    source_sha256          TEXT NOT NULL,
    manifest_sha256        TEXT NOT NULL,
    retrieval_uri          TEXT,
    retrieved_at           TEXT,
    importer_name          TEXT NOT NULL,
    importer_version       TEXT NOT NULL,
    raw_record_count       INTEGER NOT NULL,
    created_at             TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (source_catalog_id, source_version, source_file, source_sha256),
    CHECK (length(source_sha256)=64 AND lower(source_sha256) NOT GLOB '*[^0-9a-f]*'),
    CHECK (length(manifest_sha256)=64 AND lower(manifest_sha256) NOT GLOB '*[^0-9a-f]*'),
    CHECK (upper(source_version) NOT IN ('UNKNOWN','CURRENT') OR length(trim(version_unknown_reason))>0),
    CHECK (raw_record_count>=0)
);
CREATE INDEX idx_source_manifest_catalog
    ON source_import_manifests(source_catalog_id, source_version);

ALTER TABLE raw_artifacts ADD COLUMN source_manifest_id TEXT
    REFERENCES source_import_manifests(id) ON DELETE RESTRICT;
CREATE INDEX idx_raw_source_manifest ON raw_artifacts(source_manifest_id);

CREATE TABLE source_rights_versions (
    id                      TEXT PRIMARY KEY,
    source_catalog_id       TEXT NOT NULL REFERENCES source_catalogs(id) ON DELETE RESTRICT,
    source_version          TEXT NOT NULL,
    rights_version          TEXT NOT NULL,
    redistribution_status   TEXT NOT NULL DEFAULT 'UNKNOWN',
    ship_raw_text           INTEGER NOT NULL DEFAULT 0,
    license_identifier      TEXT,
    terms_url               TEXT,
    evidence_sha256         TEXT,
    evidence_retrieved_at   TEXT,
    attribution_text        TEXT,
    decision_reason         TEXT NOT NULL,
    decided_by              TEXT NOT NULL,
    decided_at              TEXT NOT NULL DEFAULT (datetime('now')),
    supersedes_id           TEXT REFERENCES source_rights_versions(id) ON DELETE RESTRICT,
    is_current              INTEGER NOT NULL DEFAULT 1,
    UNIQUE (source_catalog_id, source_version, rights_version),
    CHECK (redistribution_status IN ('ALLOWED','RESTRICTED','UNKNOWN')),
    CHECK (ship_raw_text IN (0,1)),
    CHECK (ship_raw_text=0 OR redistribution_status='ALLOWED'),
    CHECK (evidence_sha256 IS NULL OR
           (length(evidence_sha256)=64 AND lower(evidence_sha256) NOT GLOB '*[^0-9a-f]*')),
    CHECK (is_current IN (0,1))
);
CREATE UNIQUE INDEX idx_source_rights_current
    ON source_rights_versions(source_catalog_id, source_version)
    WHERE is_current=1;

CREATE TABLE raw_artifact_dispositions (
    raw_artifact_id         TEXT PRIMARY KEY REFERENCES raw_artifacts(id) ON DELETE RESTRICT,
    disposition             TEXT NOT NULL,
    rationale               TEXT NOT NULL,
    related_raw_artifact_id TEXT REFERENCES raw_artifacts(id) ON DELETE RESTRICT,
    decision_method         TEXT NOT NULL,
    decision_confidence     REAL,
    requires_human_review   INTEGER NOT NULL DEFAULT 1,
    decided_by              TEXT NOT NULL,
    decided_at              TEXT NOT NULL DEFAULT (datetime('now')),
    decision_batch_id       TEXT,
    CHECK (disposition IN (
        'SUPPORTS_CANONICAL','SPLIT','DUPLICATE','CROSSWALK_ONLY',
        'RELATION_ONLY','REJECTED','DEFERRED'
    )),
    CHECK (length(trim(rationale))>0),
    CHECK (disposition<>'DUPLICATE' OR related_raw_artifact_id IS NOT NULL),
    CHECK (decision_confidence IS NULL OR
           (decision_confidence>=0 AND decision_confidence<=1)),
    CHECK (requires_human_review IN (0,1)),
    CHECK (related_raw_artifact_id IS NULL OR related_raw_artifact_id<>raw_artifact_id)
);
CREATE INDEX idx_raw_disposition
    ON raw_artifact_dispositions(disposition, requires_human_review);

CREATE TABLE artifact_source_lineage (
    artifact_id      TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE RESTRICT,
    raw_artifact_id  TEXT NOT NULL REFERENCES raw_artifacts(id) ON DELETE RESTRICT,
    lineage_role     TEXT NOT NULL,
    mapping_strength TEXT NOT NULL DEFAULT 'DIRECT',
    rationale        TEXT,
    is_primary       INTEGER NOT NULL DEFAULT 0,
    created_at       TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (artifact_id, raw_artifact_id),
    CHECK (lineage_role IN ('SUPPORTS_CANONICAL','SPLIT')),
    CHECK (mapping_strength IN ('DIRECT','INDIRECT','PARTIAL','INFORMATIVE')),
    CHECK (mapping_strength='DIRECT' OR length(trim(rationale))>0),
    CHECK (is_primary IN (0,1))
);
CREATE INDEX idx_lineage_raw ON artifact_source_lineage(raw_artifact_id, artifact_id);
CREATE UNIQUE INDEX idx_lineage_primary
    ON artifact_source_lineage(artifact_id) WHERE is_primary=1;

-- Once final lineage exists, neither side may be physically removed. Canonical
-- deprecation remains a logical update and therefore does not trigger guards.
CREATE TRIGGER trg_preserve_raw_with_lineage
BEFORE DELETE ON raw_artifacts
WHEN EXISTS (
    SELECT 1 FROM artifact_source_lineage WHERE raw_artifact_id=OLD.id
)
BEGIN
    SELECT RAISE(ABORT, 'raw artifact has final lineage and cannot be deleted');
END;

CREATE TRIGGER trg_preserve_final_lineage
BEFORE DELETE ON artifact_source_lineage
BEGIN
    SELECT RAISE(ABORT, 'final source lineage cannot be deleted');
END;

CREATE VIEW v_catalog_closure AS
SELECT
    (SELECT COUNT(*) FROM raw_artifacts) AS raw_total,
    (SELECT COUNT(*) FROM raw_artifact_dispositions) AS raw_disposed,
    (SELECT COUNT(*) FROM security_artifacts WHERE is_active=1) AS active_canonicals,
    (SELECT COUNT(DISTINCT artifact_id) FROM artifact_source_lineage) AS canonicals_with_lineage,
    (SELECT COUNT(*) FROM raw_artifacts r
      WHERE NOT EXISTS (
          SELECT 1 FROM raw_artifact_dispositions d WHERE d.raw_artifact_id=r.id
      )) AS missing_dispositions,
    (SELECT COUNT(*) FROM security_artifacts a
      WHERE a.is_active=1 AND NOT EXISTS (
          SELECT 1 FROM artifact_source_lineage l WHERE l.artifact_id=a.id
      )) AS missing_canonical_lineage;
''',
  ),
  EmbeddedMigration(
    version: '032',
    filename: '032_catalog_workbook_audit.sql',
    sha256: '21cb5368fd761c31feaf48914dbb31fb21cdf1880cb6ee20769053ca6bc8cc70',
    sql:
        r'''-- SecureGuide migration 032: audited Excel catalog curation runs.
PRAGMA foreign_keys = ON;

INSERT OR IGNORE INTO schema_migrations(version, description)
VALUES('032', 'Audited and conflict-safe catalog workbook runs');

CREATE TABLE catalog_workbook_runs (
    id                       TEXT PRIMARY KEY,
    operation                TEXT NOT NULL,
    workbook_path            TEXT NOT NULL,
    baseline_db_sha256       TEXT NOT NULL,
    workbook_sha256          TEXT,
    status                   TEXT NOT NULL,
    actor                    TEXT NOT NULL,
    conflict_resolution_json TEXT,
    summary_json             TEXT,
    created_at               TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at             TEXT,
    CHECK(operation IN ('EXPORT','VALIDATE','PLAN','APPLY')),
    CHECK(status IN ('STARTED','VALID','INVALID','PLANNED','CONFLICT','APPLIED','FAILED')),
    CHECK(length(baseline_db_sha256)=64 AND lower(baseline_db_sha256) NOT GLOB '*[^0-9a-f]*'),
    CHECK(workbook_sha256 IS NULL OR
          (length(workbook_sha256)=64 AND lower(workbook_sha256) NOT GLOB '*[^0-9a-f]*'))
);
CREATE INDEX idx_workbook_runs_status ON catalog_workbook_runs(status, created_at);

CREATE TABLE catalog_workbook_row_audit (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id         TEXT NOT NULL REFERENCES catalog_workbook_runs(id) ON DELETE RESTRICT,
    sheet_name     TEXT NOT NULL,
    row_key        TEXT NOT NULL,
    action         TEXT NOT NULL,
    baseline_hash  TEXT,
    current_hash   TEXT,
    proposed_hash  TEXT,
    outcome        TEXT NOT NULL,
    resolution     TEXT,
    detail         TEXT,
    created_at     TEXT NOT NULL DEFAULT (datetime('now')),
    CHECK(action IN ('NO_CHANGE','UPSERT','DEPRECATE')),
    CHECK(outcome IN ('NO_CHANGE','VALID','INVALID','CONFLICT','APPLIED','FAILED')),
    CHECK(resolution IS NULL OR resolution IN ('USE_WORKBOOK','USE_DATABASE','MANUAL'))
);
CREATE INDEX idx_workbook_audit_run ON catalog_workbook_row_audit(run_id, sheet_name, row_key);
''',
  ),
  EmbeddedMigration(
    version: '033',
    filename: '033_catalog_upgrade_audit.sql',
    sha256: '3755ab865562f4be12f2d8979c694542a92d6a06993442aba83a5b8b236c7039',
    sql:
        r'''-- SecureGuide migration 033: audited catalog-content upgrades.
PRAGMA foreign_keys = ON;

INSERT OR IGNORE INTO schema_migrations(version, description)
VALUES('033', 'Transactional catalog-content upgrade audit');

CREATE TABLE catalog_upgrade_runs (
    id                         TEXT PRIMARY KEY,
    candidate_sha256           TEXT NOT NULL,
    installed_sha256_before    TEXT NOT NULL,
    installed_sha256_after     TEXT,
    operational_snapshot_before TEXT NOT NULL,
    operational_snapshot_after  TEXT,
    status                     TEXT NOT NULL,
    old_artifact_count         INTEGER NOT NULL,
    new_artifact_count         INTEGER,
    actor                      TEXT NOT NULL,
    error_detail               TEXT,
    started_at                 TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at               TEXT,
    CHECK(status IN ('STARTED','APPLIED','FAILED')),
    CHECK(length(candidate_sha256)=64),
    CHECK(length(installed_sha256_before)=64),
    CHECK(installed_sha256_after IS NULL OR length(installed_sha256_after)=64),
    CHECK(length(operational_snapshot_before)=64),
    CHECK(operational_snapshot_after IS NULL OR length(operational_snapshot_after)=64)
);
CREATE INDEX idx_catalog_upgrade_status ON catalog_upgrade_runs(status, started_at);
''',
  ),
  EmbeddedMigration(
    version: '034',
    filename: '034_neutral_catalog_identity.sql',
    sha256: 'aa7243324a6e3b508571004fad1299b62a6564fbec7f4fba2868e753a6d6fccd',
    sql:
        r'''-- ============================================================================
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
''',
  ),
  EmbeddedMigration(
    version: '035',
    filename: '035_semantic_reconciliation_closure.sql',
    sha256: 'bb8cde1b5958020c7ac2060e14a3762c3d78a834887bff26aa7938184a200928',
    sql:
        r'''-- ============================================================================
-- SecureGuide - Migration 035: Semantic reconciliation closure evidence
-- ----------------------------------------------------------------------------
-- Adds normalized, source-preserving evidence for non-lineage reconciliation
-- outcomes and individually classified deferred records. Existing raw rows,
-- final lineage, aliases, and profile/operational data remain untouched.
-- ============================================================================

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS raw_artifact_deferred_reasons (
    raw_artifact_id TEXT PRIMARY KEY
        REFERENCES raw_artifacts(id) ON DELETE RESTRICT,
    reason_code TEXT NOT NULL CHECK (reason_code IN (
        'INSUFFICIENT_AUTHORITATIVE_CONTEXT',
        'ATOMICITY_AMBIGUITY',
        'AUTHORITATIVE_CONFLICT',
        'UNRESOLVED_SEMANTIC_BOUNDARY',
        'MISSING_SOURCE_METADATA'
    )),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS raw_artifact_reconciliation_links (
    raw_artifact_id TEXT NOT NULL
        REFERENCES raw_artifacts(id) ON DELETE RESTRICT,
    link_index INTEGER NOT NULL CHECK (link_index >= 0),
    disposition TEXT NOT NULL CHECK (disposition IN (
        'DUPLICATE', 'CROSSWALK_ONLY', 'RELATION_ONLY'
    )),
    target_artifact_id TEXT REFERENCES security_artifacts(id) ON DELETE RESTRICT,
    target_raw_artifact_id TEXT REFERENCES raw_artifacts(id) ON DELETE RESTRICT,
    mapping_strength TEXT NOT NULL CHECK (mapping_strength IN (
        'DIRECT', 'INDIRECT', 'PARTIAL', 'INFORMATIVE'
    )),
    rationale TEXT NOT NULL CHECK (length(trim(rationale)) > 0),
    evidence_method TEXT NOT NULL CHECK (length(trim(evidence_method)) > 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (raw_artifact_id, link_index),
    CHECK (
        (target_artifact_id IS NOT NULL AND target_raw_artifact_id IS NULL)
        OR (target_artifact_id IS NULL AND target_raw_artifact_id IS NOT NULL)
    ),
    CHECK (mapping_strength = 'DIRECT' OR length(trim(rationale)) > 0)
);
CREATE INDEX IF NOT EXISTS idx_reconciliation_links_artifact
    ON raw_artifact_reconciliation_links(target_artifact_id, raw_artifact_id);
CREATE INDEX IF NOT EXISTS idx_reconciliation_links_raw_target
    ON raw_artifact_reconciliation_links(target_raw_artifact_id, raw_artifact_id);

INSERT OR IGNORE INTO schema_migrations(version, description)
VALUES ('035', 'Semantic reconciliation links and deferred reason evidence');
''',
  ),
];
// dart format on
