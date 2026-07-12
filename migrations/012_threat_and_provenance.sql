-- ============================================================================
-- SecureGuide — Migration 012: Threat dimension + normalized provenance
-- ----------------------------------------------------------------------------
-- SADP v1.0 §2.4/§2.5/§3.1. Introduces the Threat classification (THR-*) as a
-- normalized dimension (the mandated replacement for free-form tags), plus the
-- typed tables that hold what previously rode on tags (platforms, amani
-- provenance, amani asset refs) and the UI-visibility config. Additive only;
-- lk_threat / amani_threat_alias values are seeded in migration 013.
-- ============================================================================

PRAGMA foreign_keys = ON;

INSERT OR IGNORE INTO schema_migrations (version, description)
VALUES ('012', 'Threat dimension (THR-*) + artifact_threats/platforms + amani provenance + UI visibility (SADP 2.4/2.5/3.1)');

-- ---- Threat classification list (values in 013) ----
CREATE TABLE IF NOT EXISTS lk_threat (
    code       TEXT PRIMARY KEY,
    name_en    TEXT,
    name_ar    TEXT,
    category   TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0
);

-- ---- Normalized threats per artifact (SADP §3.1 — never a JSON array) ----
CREATE TABLE IF NOT EXISTS artifact_threats (
    artifact_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    threat_code TEXT NOT NULL REFERENCES lk_threat(code),
    PRIMARY KEY (artifact_id, threat_code)
);
CREATE INDEX IF NOT EXISTS idx_artifact_threats ON artifact_threats(threat_code);

-- ---- Normalized platform applicability (replaces platform tags) ----
CREATE TABLE IF NOT EXISTS artifact_platforms (
    artifact_id   TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    platform_code TEXT NOT NULL REFERENCES lk_platform(code),
    PRIMARY KEY (artifact_id, platform_code)
);

-- ---- Reversible amani lineage (replaces amani_domain/amani_sub/amani_id tags) ----
CREATE TABLE IF NOT EXISTS catalog_amani_provenance (
    artifact_id  TEXT PRIMARY KEY REFERENCES security_artifacts(id) ON DELETE CASCADE,
    amani_id     TEXT NOT NULL,
    amani_domain TEXT NOT NULL REFERENCES amani_domain_alias(amani_key),
    amani_sub    TEXT
);
CREATE INDEX IF NOT EXISTS idx_amani_prov_amaniid ON catalog_amani_provenance(amani_id);

-- ---- Normalized amani asset refs (replaces Data tags) ----
CREATE TABLE IF NOT EXISTS catalog_amani_assets (
    artifact_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    asset_ref   TEXT NOT NULL,
    PRIMARY KEY (artifact_id, asset_ref)
);

-- ---- amani threat vocabulary -> THR-* (seeded in 013; fail-loud on unmapped) ----
CREATE TABLE IF NOT EXISTS amani_threat_alias (
    amani_key    TEXT PRIMARY KEY,
    threat_code  TEXT NOT NULL REFERENCES lk_threat(code),
    needs_review INTEGER NOT NULL DEFAULT 0,
    CHECK (needs_review IN (0,1))
);

-- ---- UI visibility config (SADP §2.5 — show/hide without a schema change) ----
CREATE TABLE IF NOT EXISTS classification_visibility (
    dimension  TEXT PRIMARY KEY,
    is_visible INTEGER NOT NULL DEFAULT 1,
    sort_order INTEGER NOT NULL DEFAULT 0,
    CHECK (is_visible IN (0,1))
);
INSERT OR IGNORE INTO classification_visibility (dimension, is_visible, sort_order) VALUES
 ('primary_domain',1,0),('sub_domain',1,1),('artifact_type',1,2),('abstraction_level',1,3),
 ('obligation_source',1,4),('obligation_level',1,5),('exception_status',1,6),('granularity_level',1,7),
 ('control_nature',1,8),('control_function',1,9),('testability',1,10),('implementation_status',1,11),
 ('verification_status',1,12),('effectiveness',1,13),('priority',1,14),('relationship_type',1,15),
 ('requirement_type',1,16),('mapping_strength',1,17),('review_frequency',1,18),('threat',1,19),('platform',1,20);

-- ---- Staging additions so authored threats/platforms flow through promote.py ----
ALTER TABLE staging_artifacts ADD COLUMN proposed_threats_json TEXT;
ALTER TABLE staging_artifacts ADD COLUMN proposed_platforms_json TEXT;
