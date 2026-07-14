-- ============================================================================
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
