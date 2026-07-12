-- ============================================================================
-- SecureGuide — Migration 010: Complete amani_domain_alias sub-domain coverage
-- ----------------------------------------------------------------------------
-- Migration 009 seeded amani_domain_alias but left 5 broad domains without a
-- concrete SDT sub-domain (sdt_sub NULL). A promoted control REQUIRES a valid
-- sub_domain, and Phase 5's round-trip generator needs a complete domain bridge,
-- so we fill each with a documented best-fit sub-domain (still needs_review=1 —
-- a curator refines per control). Additive, idempotent (only fills NULLs); the
-- generator source-of-truth (build_reference_ext.AMANI_DOMAIN_ALIAS) matches.
-- ============================================================================

INSERT OR IGNORE INTO schema_migrations (version, description)
VALUES ('010', 'Fill best-fit SDT sub-domain for the 5 amani aliases left NULL by 009');

UPDATE amani_domain_alias SET sdt_sub = 'SD-01.01'
  WHERE amani_key = 'GRC' AND sdt_sub IS NULL AND sdt_primary = 'SD-01';
UPDATE amani_domain_alias SET sdt_sub = 'SD-02.04'
  WHERE amani_key = 'financial_transactions' AND sdt_sub IS NULL AND sdt_primary = 'SD-02';
UPDATE amani_domain_alias SET sdt_sub = 'SD-04.03'
  WHERE amani_key = 'IPS' AND sdt_sub IS NULL AND sdt_primary = 'SD-04';
UPDATE amani_domain_alias SET sdt_sub = 'SD-05.01'
  WHERE amani_key = 'applications_browsing' AND sdt_sub IS NULL AND sdt_primary = 'SD-05';
UPDATE amani_domain_alias SET sdt_sub = 'SD-06.01'
  WHERE amani_key = 'DMR' AND sdt_sub IS NULL AND sdt_primary = 'SD-06';
