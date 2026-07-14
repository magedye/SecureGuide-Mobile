-- ============================================================================
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
