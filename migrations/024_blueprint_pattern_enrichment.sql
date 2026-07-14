-- ============================================================================
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
