-- ============================================================================
-- SecureGuide — Migration 007: Content Enrichment
-- ----------------------------------------------------------------------------
-- Captures the rich app-facing content amani carries, WITHOUT touching the
-- canonical USACM/SDT model. Additive only (ADD COLUMN / CREATE IF NOT EXISTS).
-- Extension code columns are enforced by CHECK here; the paired bilingual lk_*
-- lists (with a usacm_map to the nearest canonical value) are added in the
-- reference-data step and kept in sync by validate_reference_data.py.
-- ============================================================================

PRAGMA foreign_keys = ON;

INSERT OR IGNORE INTO schema_migrations (version, description)
VALUES ('007', 'Content enrichment: scoring inputs + enterprise classification facets + actions/variants');

-- ---- Scoring inputs + AR content parity on security_artifacts ----
ALTER TABLE security_artifacts ADD COLUMN scoring_weight REAL CHECK (scoring_weight IS NULL OR scoring_weight >= 0);
ALTER TABLE security_artifacts ADD COLUMN risk_reduction INTEGER CHECK (risk_reduction IS NULL OR risk_reduction BETWEEN 2 AND 5);
ALTER TABLE security_artifacts ADD COLUMN effort_level TEXT CHECK (effort_level IS NULL OR effort_level IN ('low','medium','high'));
ALTER TABLE security_artifacts ADD COLUMN tier TEXT CHECK (tier IS NULL OR tier IN ('essential','advanced','very_advanced','full'));
ALTER TABLE security_artifacts ADD COLUMN evidence_required_ar TEXT;          -- AR of existing evidence_required
ALTER TABLE security_artifacts ADD COLUMN verification_method_note_ar TEXT;   -- AR of existing verification_method_note
CREATE INDEX IF NOT EXISTS idx_artifacts_scoring ON security_artifacts(tier, effort_level, risk_reduction);

-- ---- Ordered bilingual step lists (control actions, variant actions, verification steps) ----
CREATE TABLE IF NOT EXISTS artifact_actions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id  TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    variant_id   INTEGER REFERENCES artifact_variants(id) ON DELETE CASCADE,   -- NULL = base control
    kind         TEXT NOT NULL DEFAULT 'ACTION',
    seq          INTEGER NOT NULL,
    text_en      TEXT NOT NULL,
    text_ar      TEXT,
    UNIQUE (artifact_id, variant_id, kind, seq),
    CHECK (kind IN ('ACTION','VERIFICATION')),
    CHECK (seq >= 0)
);
CREATE INDEX IF NOT EXISTS idx_actions_artifact ON artifact_actions(artifact_id, kind, seq);

-- ---- Platform-specific variants (variants[]) ----
CREATE TABLE IF NOT EXISTS artifact_variants (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id  TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    platform     TEXT NOT NULL,                                                -- open-ended; lk_platform provides labels
    title_en     TEXT,
    title_ar     TEXT,
    sort_order   INTEGER NOT NULL DEFAULT 0,
    UNIQUE (artifact_id, platform)
);

-- ---- enterprise.security_objectives (8 CIA+) with strength ----
CREATE TABLE IF NOT EXISTS artifact_security_objectives (
    artifact_id    TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    objective_code TEXT NOT NULL,
    strength       TEXT NOT NULL,
    PRIMARY KEY (artifact_id, objective_code),
    CHECK (objective_code IN ('confidentiality','integrity','availability','authenticity','accountability','non_repudiation','privacy','safety')),
    CHECK (strength IN ('primary','supporting','none'))
);

-- ---- enterprise.csf_functions (6 NIST-CSF) with role ----
CREATE TABLE IF NOT EXISTS artifact_csf_functions (
    artifact_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    csf_code    TEXT NOT NULL,
    strength    TEXT NOT NULL,
    PRIMARY KEY (artifact_id, csf_code),
    CHECK (csf_code IN ('govern','identify','protect','detect','respond','recover')),
    CHECK (strength IN ('primary','supporting'))
);

-- ---- enterprise.control_purposes (10) → maps to control_function FUN-* via lk ----
CREATE TABLE IF NOT EXISTS artifact_control_purposes (
    artifact_id  TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    purpose_code TEXT NOT NULL,
    PRIMARY KEY (artifact_id, purpose_code),
    CHECK (purpose_code IN ('preventive','deterrent','detective','corrective','containment','recovery','compensating','directive','monitoring','assurance'))
);

-- ---- enterprise.implementation_types (7) → maps to control_nature NAT-* via lk ----
CREATE TABLE IF NOT EXISTS artifact_implementation_types (
    artifact_id    TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    impl_type_code TEXT NOT NULL,
    PRIMARY KEY (artifact_id, impl_type_code),
    CHECK (impl_type_code IN ('administrative','technical','operational','physical','human','legal_contractual','architectural'))
);

-- ---- enterprise.maturity_requirements (per tier, bilingual) ----
CREATE TABLE IF NOT EXISTS artifact_maturity_requirements (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id     TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    tier_code       TEXT NOT NULL,
    objective_en    TEXT,  objective_ar    TEXT,
    scope_en        TEXT,  scope_ar        TEXT,
    verification_en TEXT,  verification_ar TEXT,
    UNIQUE (artifact_id, tier_code),
    CHECK (tier_code IN ('essential','advanced','very_advanced','full'))
);

-- ---- enterprise.verification_guidance.evidence_types[] (reuses profile_evidence set) ----
CREATE TABLE IF NOT EXISTS artifact_verification_evidence_types (
    artifact_id   TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    evidence_type TEXT NOT NULL,
    PRIMARY KEY (artifact_id, evidence_type),
    CHECK (evidence_type IN ('DOCUMENT','SCREENSHOT','LOG','REPORT','CONFIG','ATTESTATION','LINK','OTHER'))
);

-- ============================================================================
-- Scoring configuration + amani domain alias (seeded by build_scoring_reference.py)
-- ============================================================================
CREATE TABLE IF NOT EXISTS scoring_policy (
    id                       TEXT PRIMARY KEY,
    critical_cap             INTEGER NOT NULL,
    dependency_clamp_ceiling REAL NOT NULL,
    accepted_risk_lifts_cap  INTEGER NOT NULL DEFAULT 0,
    note                     TEXT,
    CHECK (accepted_risk_lifts_cap IN (0,1)),
    CHECK (critical_cap BETWEEN 0 AND 100),
    CHECK (dependency_clamp_ceiling >= 0 AND dependency_clamp_ceiling <= 1)
);

CREATE TABLE IF NOT EXISTS scoring_bands (
    policy_id  TEXT NOT NULL REFERENCES scoring_policy(id) ON DELETE CASCADE,
    band_code  TEXT NOT NULL,
    min_score  INTEGER NOT NULL,
    label_en   TEXT NOT NULL,
    label_ar   TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (policy_id, band_code),
    CHECK (min_score BETWEEN 0 AND 100)
);

-- amani domain key → SDT primary/sub (reviewable; importer & generator read this both ways)
CREATE TABLE IF NOT EXISTS amani_domain_alias (
    amani_key    TEXT PRIMARY KEY,
    sdt_primary  TEXT NOT NULL,
    sdt_sub      TEXT,
    confidence   REAL,
    needs_review INTEGER NOT NULL DEFAULT 0,
    note         TEXT,
    CHECK (needs_review IN (0,1)),
    CHECK (sdt_primary GLOB 'SD-0[1-8]'),
    CHECK (sdt_sub IS NULL OR (sdt_sub GLOB 'SD-0[1-8].0[1-5]' AND substr(sdt_sub,1,5) = sdt_primary))
);

-- ============================================================================
-- Staging-side additions so authored rich content flows through promote.py
-- ============================================================================
ALTER TABLE staging_artifacts ADD COLUMN title_ar TEXT;
ALTER TABLE staging_artifacts ADD COLUMN definition_short_ar TEXT;
ALTER TABLE staging_artifacts ADD COLUMN definition_full_ar TEXT;
ALTER TABLE staging_artifacts ADD COLUMN objective_ar TEXT;
ALTER TABLE staging_artifacts ADD COLUMN evidence_ar TEXT;
ALTER TABLE staging_artifacts ADD COLUMN verification_method_note_ar TEXT;
ALTER TABLE staging_artifacts ADD COLUMN proposed_scoring_weight REAL;
ALTER TABLE staging_artifacts ADD COLUMN proposed_risk_reduction INTEGER;
ALTER TABLE staging_artifacts ADD COLUMN proposed_effort_level TEXT;
ALTER TABLE staging_artifacts ADD COLUMN proposed_tier TEXT;
ALTER TABLE staging_artifacts ADD COLUMN proposed_actions_json TEXT;
ALTER TABLE staging_artifacts ADD COLUMN proposed_variants_json TEXT;
ALTER TABLE staging_artifacts ADD COLUMN proposed_security_objectives_json TEXT;
ALTER TABLE staging_artifacts ADD COLUMN proposed_csf_functions_json TEXT;
ALTER TABLE staging_artifacts ADD COLUMN proposed_control_purposes_json TEXT;
ALTER TABLE staging_artifacts ADD COLUMN proposed_implementation_types_json TEXT;
ALTER TABLE staging_artifacts ADD COLUMN proposed_maturity_requirements_json TEXT;
ALTER TABLE staging_artifacts ADD COLUMN proposed_verification_json TEXT;
