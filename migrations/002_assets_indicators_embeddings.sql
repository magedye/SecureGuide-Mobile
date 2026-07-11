-- ============================================================================
-- SecureGuide v1.1 — Additive Migration 002
-- Modules: (A) Asset Intelligence  (B) Threat Indicators  (C) Semantic
--          Embeddings & Deduplication
-- ----------------------------------------------------------------------------
-- Additive over 001_initial_schema.sql. Run AFTER 001 on the same database.
-- Authorities: USACM v2.2.1 / SDT v2.2.1. Assets/Threats/Vulns remain modeled
-- as catalog artifacts (ART-AST/ART-THR/ART-VUL); the tables below add the
-- ENTERPRISE-SPECIFIC (operational) inventory + observed threat intelligence,
-- linked back to the catalog. Deduplication is human-in-the-loop and never
-- destructive (AGENTS.md Rule 12).
-- ============================================================================

PRAGMA foreign_keys = ON;

-- ============================================================================
-- MODULE A: ASSET INTELLIGENCE (operational, per enterprise_profile)
-- ============================================================================

-- Optional reference taxonomy for configurable asset types (UI Settings).
CREATE TABLE IF NOT EXISTS ref_asset_types (
    id TEXT PRIMARY KEY,
    name_en TEXT NOT NULL,
    name_ar TEXT,
    category TEXT,                        -- maps to USACM asset_type family
    description TEXT,
    CHECK (category IS NULL OR category IN ('HARDWARE','SOFTWARE','DATA','SERVICE','FACILITY','PERSONNEL','NETWORK','CLOUD_INSTANCE','DOCUMENT','INTELLECTUAL_PROPERTY'))
);

-- The actual assets owned by a specific organization/profile.
CREATE TABLE IF NOT EXISTS enterprise_assets (
    id TEXT PRIMARY KEY,
    profile_id TEXT NOT NULL REFERENCES enterprise_profiles(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    asset_type TEXT NOT NULL,
    asset_type_ref_id TEXT REFERENCES ref_asset_types(id) ON DELETE SET NULL,
    criticality TEXT NOT NULL DEFAULT 'MEDIUM',
    exposure TEXT,                        -- INTERNAL/EXTERNAL/DMZ/CLOUD…
    owner TEXT,
    location TEXT,
    environment TEXT,                     -- PRODUCTION/STAGING/DEV/OT…
    description TEXT,
    catalog_artifact_id TEXT REFERENCES security_artifacts(id) ON DELETE SET NULL,  -- optional ART-AST reference
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    CHECK (asset_type IN ('HARDWARE','SOFTWARE','DATA','SERVICE','FACILITY','PERSONNEL','NETWORK','CLOUD_INSTANCE','DOCUMENT','INTELLECTUAL_PROPERTY')),
    CHECK (criticality IN ('CRITICAL','HIGH','MEDIUM','LOW'))
);
CREATE INDEX IF NOT EXISTS idx_assets_profile ON enterprise_assets(profile_id);
CREATE INDEX IF NOT EXISTS idx_assets_type ON enterprise_assets(asset_type, criticality);

-- Asset -> protecting control (ART-CTR/ART-CFG catalog artifact).
CREATE TABLE IF NOT EXISTS asset_controls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id TEXT NOT NULL REFERENCES enterprise_assets(id) ON DELETE CASCADE,
    artifact_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    coverage_status TEXT NOT NULL DEFAULT 'PLANNED',
    notes TEXT,
    UNIQUE (asset_id, artifact_id),
    CHECK (coverage_status IN ('COVERED','PARTIAL','PLANNED','GAP'))
);

-- Asset -> vulnerability (ART-VUL catalog artifact or raw CVE).
CREATE TABLE IF NOT EXISTS asset_vulnerabilities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id TEXT NOT NULL REFERENCES enterprise_assets(id) ON DELETE CASCADE,
    artifact_id TEXT REFERENCES security_artifacts(id) ON DELETE SET NULL,
    cve_id TEXT,
    cvss_score REAL,
    status TEXT NOT NULL DEFAULT 'OPEN',
    notes TEXT,
    CHECK (cvss_score IS NULL OR (cvss_score >= 0 AND cvss_score <= 10)),
    CHECK (status IN ('OPEN','MITIGATED','ACCEPTED','FALSE_POSITIVE','RESOLVED'))
);
CREATE INDEX IF NOT EXISTS idx_asset_vulns_asset ON asset_vulnerabilities(asset_id);

-- Asset -> threat (ART-THR catalog artifact).
CREATE TABLE IF NOT EXISTS asset_threats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id TEXT NOT NULL REFERENCES enterprise_assets(id) ON DELETE CASCADE,
    artifact_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    relevance TEXT NOT NULL DEFAULT 'MEDIUM',
    notes TEXT,
    UNIQUE (asset_id, artifact_id),
    CHECK (relevance IN ('CRITICAL','HIGH','MEDIUM','LOW'))
);

-- ============================================================================
-- MODULE B: THREAT INDICATORS (observed intelligence — IoCs / IoAs / TTPs)
-- ============================================================================

CREATE TABLE IF NOT EXISTS threat_intelligence_sources (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    source_type TEXT,                     -- OSINT/COMMERCIAL/GOV/INTERNAL…
    url TEXT,
    reliability TEXT,                     -- Admiralty A–F / HIGH-LOW
    description TEXT,
    CHECK (reliability IS NULL OR reliability IN ('HIGH','MEDIUM','LOW','UNKNOWN'))
);

CREATE TABLE IF NOT EXISTS detection_tools (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    tool_type TEXT NOT NULL,
    vendor TEXT,
    capabilities TEXT,
    description TEXT,
    CHECK (tool_type IN ('SIEM','EDR','XDR','NDR','SOAR','IAM','VULNERABILITY','CSPM','FIREWALL','WAF','MANUAL','OTHER'))
);

CREATE TABLE IF NOT EXISTS threat_indicators (
    id TEXT PRIMARY KEY,
    profile_id TEXT REFERENCES enterprise_profiles(id) ON DELETE CASCADE,   -- NULL = global feed
    catalog_artifact_id TEXT REFERENCES security_artifacts(id) ON DELETE SET NULL,  -- optional ART-THR
    source_id TEXT REFERENCES threat_intelligence_sources(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    indicator_class TEXT NOT NULL DEFAULT 'IOC',
    ioc_type TEXT,
    ioc_value TEXT,
    severity_level TEXT NOT NULL DEFAULT 'MEDIUM',
    confidence_score REAL,                -- 0.0–1.0
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    primary_domain TEXT,
    sub_domain TEXT,
    mitre_tactic TEXT,
    mitre_technique_id TEXT,
    threat_family TEXT,
    first_observed TEXT,
    last_observed TEXT,
    observation_count INTEGER NOT NULL DEFAULT 0,
    description TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    CHECK (indicator_class IN ('IOC','IOA','ANOMALY','WEAK_SIGNAL','THREAT_INTEL','DETECTION_USE_CASE','HUNTING_HYPOTHESIS')),
    CHECK (ioc_type IS NULL OR ioc_type IN ('IP','DOMAIN','URL','HASH','EMAIL','FILE','REGISTRY','USER_AGENT','OTHER')),
    CHECK (severity_level IN ('CRITICAL','HIGH','MEDIUM','LOW','INFO')),
    CHECK (status IN ('ACTIVE','INACTIVE','INVESTIGATING','MITIGATED','EXPIRED')),
    CHECK (confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)),
    CHECK (primary_domain IS NULL OR primary_domain IN ('SD-01','SD-02','SD-03','SD-04','SD-05','SD-06','SD-07','SD-08')),
    CHECK (sub_domain IS NULL OR (sub_domain GLOB 'SD-0[1-8].0[1-5]' AND (primary_domain IS NULL OR substr(sub_domain,1,5) = primary_domain))),
    CHECK (observation_count >= 0)
);
CREATE INDEX IF NOT EXISTS idx_indicators_profile ON threat_indicators(profile_id);
CREATE INDEX IF NOT EXISTS idx_indicators_status ON threat_indicators(status, severity_level);
CREATE INDEX IF NOT EXISTS idx_indicators_mitre ON threat_indicators(mitre_tactic, mitre_technique_id);
CREATE INDEX IF NOT EXISTS idx_indicators_ioc ON threat_indicators(ioc_type, ioc_value);

-- Indicator -> related vulnerability.
CREATE TABLE IF NOT EXISTS indicator_vulnerabilities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    indicator_id TEXT NOT NULL REFERENCES threat_indicators(id) ON DELETE CASCADE,
    artifact_id TEXT REFERENCES security_artifacts(id) ON DELETE SET NULL,  -- ART-VUL
    cve_id TEXT,
    cvss_score REAL,
    notes TEXT,
    CHECK (cvss_score IS NULL OR (cvss_score >= 0 AND cvss_score <= 10))
);
CREATE INDEX IF NOT EXISTS idx_ind_vulns ON indicator_vulnerabilities(indicator_id);

-- Indicator -> mitigating / detecting control (ART-CTR).
CREATE TABLE IF NOT EXISTS indicator_controls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    indicator_id TEXT NOT NULL REFERENCES threat_indicators(id) ON DELETE CASCADE,
    artifact_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    control_role TEXT NOT NULL DEFAULT 'DETECTIVE',
    coverage_pct INTEGER,
    status TEXT,
    UNIQUE (indicator_id, artifact_id, control_role),
    CHECK (control_role IN ('DETECTIVE','PREVENTIVE','CORRECTIVE','COMPENSATING')),
    CHECK (coverage_pct IS NULL OR (coverage_pct >= 0 AND coverage_pct <= 100)),
    CHECK (status IS NULL OR status IN ('COVERED','PARTIAL','PLANNED','GAP'))
);
CREATE INDEX IF NOT EXISTS idx_ind_controls ON indicator_controls(indicator_id);

-- Indicator -> detection tool coverage.
CREATE TABLE IF NOT EXISTS indicator_tools (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    indicator_id TEXT NOT NULL REFERENCES threat_indicators(id) ON DELETE CASCADE,
    detection_tool_id TEXT NOT NULL REFERENCES detection_tools(id) ON DELETE CASCADE,
    coverage_pct INTEGER,
    UNIQUE (indicator_id, detection_tool_id),
    CHECK (coverage_pct IS NULL OR (coverage_pct >= 0 AND coverage_pct <= 100))
);

-- Indicator -> recommended response actions.
CREATE TABLE IF NOT EXISTS indicator_recommended_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    indicator_id TEXT NOT NULL REFERENCES threat_indicators(id) ON DELETE CASCADE,
    action TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'PRI-MEDIUM',
    effort_estimate INTEGER,
    responsible_role TEXT,
    status TEXT NOT NULL DEFAULT 'PENDING',
    CHECK (priority IN ('PRI-CRITICAL','PRI-HIGH','PRI-MEDIUM','PRI-LOW')),
    CHECK (effort_estimate IS NULL OR effort_estimate >= 0),
    CHECK (status IN ('PENDING','IN_PROGRESS','DONE','DISMISSED'))
);
CREATE INDEX IF NOT EXISTS idx_ind_actions ON indicator_recommended_actions(indicator_id, status);

-- ============================================================================
-- MODULE C: SEMANTIC EMBEDDINGS & DEDUPLICATION
-- Store meaning-vectors for catalog artifacts to enable semantic search,
-- crosswalk suggestion, and (human-reviewed) near-duplicate detection.
-- ============================================================================

-- One row per (artifact, embedding model). Re-embed by inserting a new model row.
CREATE TABLE IF NOT EXISTS artifact_embeddings (
    artifact_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    model_name TEXT NOT NULL,             -- e.g. 'multilingual-e5-small'
    model_version TEXT NOT NULL DEFAULT '1',
    dim INTEGER NOT NULL,                 -- e.g. 384
    embedding BLOB NOT NULL,              -- float32[dim], little-endian
    source_text_hash TEXT,               -- hash of text embedded (staleness check)
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (artifact_id, model_name, model_version),
    CHECK (dim > 0),
    CHECK (length(embedding) = dim * 4)   -- 4 bytes per float32
);
CREATE INDEX IF NOT EXISTS idx_embeddings_model ON artifact_embeddings(model_name, model_version);

-- Concept clusters: artifacts across frameworks that mean the same thing
-- (the "canonical_concept" / equivalence-group idea). Never a physical merge.
CREATE TABLE IF NOT EXISTS equivalence_groups (
    id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    canonical_artifact_id TEXT REFERENCES security_artifacts(id) ON DELETE SET NULL,
    concept_domain TEXT,                  -- optional SDT primary_domain hint
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    CHECK (concept_domain IS NULL OR concept_domain IN ('SD-01','SD-02','SD-03','SD-04','SD-05','SD-06','SD-07','SD-08'))
);

CREATE TABLE IF NOT EXISTS equivalence_group_members (
    group_id TEXT NOT NULL REFERENCES equivalence_groups(id) ON DELETE CASCADE,
    artifact_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    member_role TEXT NOT NULL DEFAULT 'MEMBER',
    similarity REAL,                      -- cosine to canonical, 0.0–1.0
    added_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (group_id, artifact_id),
    CHECK (member_role IN ('CANONICAL','MEMBER')),
    CHECK (similarity IS NULL OR (similarity >= -1 AND similarity <= 1))
);
CREATE INDEX IF NOT EXISTS idx_eqgroup_artifact ON equivalence_group_members(artifact_id);

-- Pairwise near-duplicate candidates surfaced by embeddings (or exact/fuzzy),
-- pending human review. Resolution NEVER deletes source records (AGENTS Rule 12).
CREATE TABLE IF NOT EXISTS duplicate_candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id_a TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    artifact_id_b TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    similarity REAL,
    detection_method TEXT NOT NULL DEFAULT 'EMBEDDING',
    status TEXT NOT NULL DEFAULT 'PENDING',
    resolution TEXT,
    equivalence_group_id TEXT REFERENCES equivalence_groups(id) ON DELETE SET NULL,
    reviewed_by TEXT,
    reviewed_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (artifact_id_a, artifact_id_b, detection_method),
    CHECK (artifact_id_a <> artifact_id_b),
    CHECK (artifact_id_a < artifact_id_b),          -- canonical ordering, no mirror dupes
    CHECK (similarity IS NULL OR (similarity >= -1 AND similarity <= 1)),
    CHECK (detection_method IN ('EMBEDDING','EXACT_MATCH','FUZZY','MANUAL')),
    CHECK (status IN ('PENDING','CONFIRMED','REJECTED')),
    CHECK (resolution IS NULL OR resolution IN ('KEEP_BOTH','EQUIVALENCE_GROUP','DEPRECATE_ONE'))
);
CREATE INDEX IF NOT EXISTS idx_dupe_status ON duplicate_candidates(status, similarity);
