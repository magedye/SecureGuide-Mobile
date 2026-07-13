-- ============================================================================
-- SecureGuide — Migration 016: SADP backfill for pre-SADP catalog rows
-- ----------------------------------------------------------------------------
-- Artifacts promoted before the SADP work (catalog-v0.1) predate the threat
-- dimension and the review_frequency baseline, so they would violate SADP §2.2
-- (a NULL classification) and §3.1 (no threat). Backfill them: review_frequency
-- -> AD-HOC baseline, and one THR-NA row for any artifact with no threats.
-- Additive & idempotent; a NO-OP on a fresh DB (security_artifacts empty at
-- migration time — promote.py fills these for new promotions).
-- ============================================================================

INSERT OR IGNORE INTO schema_migrations (version, description)
VALUES ('016', 'SADP backfill: review_frequency=AD-HOC + THR-NA for pre-SADP catalog rows');

UPDATE security_artifacts SET review_frequency = 'AD-HOC' WHERE review_frequency IS NULL;

INSERT OR IGNORE INTO artifact_threats (artifact_id, threat_code)
  SELECT id, 'THR-NA' FROM security_artifacts
  WHERE id NOT IN (SELECT artifact_id FROM artifact_threats);
