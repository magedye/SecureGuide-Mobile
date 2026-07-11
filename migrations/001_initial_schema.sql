-- ============================================================================
-- SecureGuide v1.0 — Comprehensive Normative Schema (SQLite)
-- ----------------------------------------------------------------------------
-- Authorities : USACM v2.2.1 (§8 Normative SQLite Data Model) + SDT v2.2.1
-- Content      : authored per docs/AUTHORING_POLICY.md (bilingual AR/EN)
-- Separation   : Master Catalog (reference) vs Enterprise Profile (operational)
-- Scope        : Intake + Master Catalog + 10 reference child tables +
--                Templates + Operational Profile layer.
--                Assets/Risks/Threats/Vulnerabilities are modeled as
--                artifact types (ART-AST / ART-RSK / ART-THR / ART-VUL)
--                related through artifact_relationships — no separate tables.
-- Note         : Operational status columns on security_artifacts are
--                REFERENCE DEFAULTS ONLY (AGENTS.md Rule 1). The authoritative
--                per-organization state lives in profile_artifacts.
-- ============================================================================

PRAGMA foreign_keys = ON;

-- ============================================================================
-- LAYER 1: INTAKE (source registry)
-- ============================================================================
CREATE TABLE source_catalogs (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    source_type TEXT,
    version TEXT,
    source_url TEXT,
    issuing_authority TEXT,
    publication_date TEXT,
    imported_at TEXT NOT NULL DEFAULT (datetime('now')),
    CHECK (source_type IS NULL OR source_type IN ('FRAMEWORK','STANDARD','THREAT_INTEL','GUIDELINE','POLICY_TEMPLATE','REGULATION','DOCUMENT','SYSTEM','TOOL'))
);

-- ============================================================================
-- LAYER 2: MASTER CATALOG (reference data only)
-- Full USACM v2.2.1 record + drafting-policy bilingual content fields.
-- ============================================================================
CREATE TABLE security_artifacts (
    id TEXT PRIMARY KEY,
    source_catalog_id TEXT REFERENCES source_catalogs(id) ON DELETE SET NULL,
    source_artifact_id TEXT,
    temp_id TEXT,

    type TEXT NOT NULL,

    -- ---- Bilingual identity / narrative (USACM) ----
    title_en TEXT NOT NULL,
    title_ar TEXT,
    description_en TEXT,
    description_ar TEXT,

    -- ---- Drafting-policy structured content (docs/AUTHORING_POLICY.md) ----
    canonical_statement TEXT,
    definition_short_en TEXT,
    definition_short_ar TEXT,
    definition_full_en TEXT,
    definition_full_ar TEXT,
    objective_en TEXT,
    objective_ar TEXT,
    applicability_note TEXT,
    implementation_guidance TEXT,
    verification_method_note TEXT,
    evidence_required TEXT,
    common_misinterpretations TEXT,
    source_quote TEXT,

    -- ---- Classification (USACM + SDT) ----
    primary_domain TEXT NOT NULL,
    sub_domain TEXT NOT NULL,
    abstraction_level TEXT NOT NULL,
    source TEXT NOT NULL,                 -- obligation source (SRC-*)
    source_type TEXT NOT NULL,
    source_location TEXT,
    obligation_level TEXT NOT NULL,
    requirement_type TEXT,
    granularity_level TEXT NOT NULL,
    control_nature TEXT,
    control_function TEXT,
    testability TEXT,
    scope TEXT,
    owner_role TEXT,

    -- ---- Reference priority (default) ----
    priority TEXT NOT NULL DEFAULT 'PRI-MEDIUM',
    priority_weight INTEGER NOT NULL DEFAULT 4,

    -- ---- Reference-default operational state (real state -> profile_artifacts) ----
    implementation_status TEXT NOT NULL DEFAULT 'STS-NOT-APPLIED',
    verification_status TEXT NOT NULL DEFAULT 'VER-NOT-VERIFIED',
    effectiveness TEXT NOT NULL DEFAULT 'EFF-UNKNOWN',
    exception_status TEXT NOT NULL DEFAULT 'EXC-NONE',
    exception_approval_date TEXT,
    exception_expiry_date TEXT,

    -- ---- Lifecycle / review / publication ----
    review_frequency TEXT,
    last_review_date TEXT,
    next_review_date TEXT,
    publication_status TEXT NOT NULL DEFAULT 'DRAFT',
    publication_date TEXT,
    effective_date TEXT,

    -- ---- Asset-specific (ART-AST) ----
    asset_type TEXT,
    asset_criticality TEXT,

    -- ---- Maturity / cost / effort planning ----
    required_maturity_level TEXT,
    cost_category TEXT,
    cost_estimate_currency TEXT,
    cost_estimate REAL,
    cost_estimate_min REAL,
    cost_estimate_max REAL,
    effort_estimate INTEGER,

    -- ---- AI classification accountability ----
    classification_confidence REAL,
    classification_rationale TEXT,
    ai_review_status TEXT NOT NULL DEFAULT 'AIR-HUMAN-REVIEW',
    requires_human_review INTEGER NOT NULL DEFAULT 1,
    rejected_alternatives TEXT,           -- JSON/text of rejected classifications

    -- ---- Import lineage ----
    import_status TEXT,
    import_source TEXT,
    import_date TEXT,
    import_version TEXT,
    source_document TEXT NOT NULL,
    source_section TEXT,
    extraction_date TEXT,

    -- ---- Record housekeeping ----
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    version INTEGER NOT NULL DEFAULT 1,
    is_custom INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,

    -- ---- Controlled-value constraints (USACM v2.2.1) ----
    CHECK (type IN ('ART-REQ','ART-OBJ','ART-PRI','ART-POL','ART-STD','ART-CTR','ART-CTE','ART-PRO','ART-PRC','ART-PRG','ART-PLN','ART-TSK','ART-CFG','ART-RUL','ART-EVD','ART-MET','ART-EXC','ART-RSK','ART-AST','ART-THR','ART-VUL','ART-OWN')),
    CHECK (primary_domain IN ('SD-01','SD-02','SD-03','SD-04','SD-05','SD-06','SD-07','SD-08')),
    CHECK (sub_domain IN ('SD-01.01','SD-01.02','SD-01.03','SD-01.04','SD-01.05','SD-02.01','SD-02.02','SD-02.03','SD-02.04','SD-02.05','SD-03.01','SD-03.02','SD-03.03','SD-03.04','SD-03.05','SD-04.01','SD-04.02','SD-04.03','SD-04.04','SD-04.05','SD-05.01','SD-05.02','SD-05.03','SD-05.04','SD-05.05','SD-06.01','SD-06.02','SD-06.03','SD-06.04','SD-06.05','SD-07.01','SD-07.02','SD-07.03','SD-07.04','SD-07.05','SD-08.01','SD-08.02','SD-08.03','SD-08.04','SD-08.05')),
    CHECK (substr(sub_domain,1,5) = primary_domain),
    CHECK (abstraction_level IN ('ABS-GOV','ABS-RIS','ABS-POL','ABS-CTR','ABS-PRO','ABS-TEC','ABS-EVM')),
    CHECK (source IN ('SRC-REG','SRC-LEG','SRC-CON','SRC-STD','SRC-INT','SRC-BST','SRC-RSK')),
    CHECK (source_type IN ('DOCUMENT','SYSTEM','TOOL','INTERVIEW','OBSERVATION','STANDARD','REGULATION')),
    CHECK (obligation_level IN ('OBL-MND','OBL-CON','OBL-REC','OBL-OPT')),
    CHECK (type <> 'ART-REQ' OR (requirement_type IS NOT NULL AND requirement_type IN ('RQT-GOV','RQT-REG','RQT-LEG','RQT-CON','RQT-STD','RQT-INT','RQT-RSK'))),
    CHECK (type = 'ART-REQ' OR requirement_type IS NULL),
    CHECK (granularity_level IN ('GRN-HIGH','GRN-MEDIUM','GRN-DETAILED','GRN-EXECUTABLE','GRN-TECHNICAL','GRN-EVIDENTIARY','GRN-METRIC')),
    CHECK (type NOT IN ('ART-CTR','ART-CTE') OR (control_nature IS NOT NULL AND control_function IS NOT NULL AND testability IS NOT NULL AND control_nature IN ('NAT-ORG','NAT-HUM','NAT-PHY','NAT-TEC') AND control_function IN ('FUN-PRE','FUN-DET','FUN-COR','FUN-REC','FUN-DRR','FUN-COM') AND testability IN ('TST-AUTO','TST-MAN','TST-DOC','TST-INT','TST-NA'))),
    CHECK (control_nature IS NULL OR control_nature IN ('NAT-ORG','NAT-HUM','NAT-PHY','NAT-TEC')),
    CHECK (control_function IS NULL OR control_function IN ('FUN-PRE','FUN-DET','FUN-COR','FUN-REC','FUN-DRR','FUN-COM')),
    CHECK (testability IS NULL OR testability IN ('TST-AUTO','TST-MAN','TST-DOC','TST-INT','TST-NA')),
    CHECK (priority IN ('PRI-CRITICAL','PRI-HIGH','PRI-MEDIUM','PRI-LOW')),
    CHECK ((priority = 'PRI-CRITICAL' AND priority_weight = 10) OR (priority = 'PRI-HIGH' AND priority_weight = 7) OR (priority = 'PRI-MEDIUM' AND priority_weight = 4) OR (priority = 'PRI-LOW' AND priority_weight = 1)),
    CHECK (implementation_status IN ('STS-NOT-APPLIED','STS-PARTIAL','STS-FULL','STS-PLANNED','STS-NEEDS-IMPROVEMENT')),
    CHECK (verification_status IN ('VER-NOT-VERIFIED','VER-PASS','VER-FAIL')),
    CHECK (effectiveness IN ('EFF-LOW','EFF-MEDIUM','EFF-HIGH','EFF-UNKNOWN')),
    CHECK (exception_status IN ('EXC-NONE','EXC-NOT-APPLICABLE','EXC-RISK-ACCEPTED','EXC-DEFERRED','EXC-UNAVAILABLE')),
    CHECK (type <> 'ART-EXC' OR (exception_approval_date IS NOT NULL AND exception_expiry_date IS NOT NULL)),
    CHECK (review_frequency IS NULL OR review_frequency IN ('DAILY','WEEKLY','MONTHLY','QUARTERLY','SEMI-ANNUAL','ANNUAL','BIENNIAL','AD-HOC','CONTINUOUS')),
    CHECK (review_frequency IS NULL OR review_frequency = 'AD-HOC' OR next_review_date IS NOT NULL),
    CHECK (publication_status IN ('DRAFT','UNDER_REVIEW','APPROVED','PUBLISHED','DEPRECATED','WITHDRAWN')),
    CHECK (type NOT IN ('ART-POL','ART-STD','ART-PRC') OR publication_status <> 'PUBLISHED' OR effective_date IS NOT NULL),
    CHECK (type <> 'ART-AST' OR (asset_type IS NOT NULL AND asset_criticality IS NOT NULL AND asset_type IN ('HARDWARE','SOFTWARE','DATA','SERVICE','FACILITY','PERSONNEL','NETWORK','CLOUD_INSTANCE','DOCUMENT','INTELLECTUAL_PROPERTY') AND asset_criticality IN ('CRITICAL','HIGH','MEDIUM','LOW'))),
    CHECK (asset_type IS NULL OR asset_type IN ('HARDWARE','SOFTWARE','DATA','SERVICE','FACILITY','PERSONNEL','NETWORK','CLOUD_INSTANCE','DOCUMENT','INTELLECTUAL_PROPERTY')),
    CHECK (asset_criticality IS NULL OR asset_criticality IN ('CRITICAL','HIGH','MEDIUM','LOW')),
    CHECK (required_maturity_level IS NULL OR required_maturity_level IN ('INITIAL','REPEATABLE','DEFINED','MANAGED','OPTIMIZED')),
    CHECK (cost_category IS NULL OR cost_category IN ('LOW','MEDIUM','HIGH','VERY_HIGH')),
    CHECK (cost_estimate_currency IS NULL OR cost_estimate_currency GLOB '[A-Z][A-Z][A-Z]'),
    CHECK (cost_estimate IS NULL OR cost_estimate >= 0),
    CHECK (cost_estimate_min IS NULL OR cost_estimate_min >= 0),
    CHECK (cost_estimate_max IS NULL OR cost_estimate_max >= 0),
    CHECK (cost_estimate_min IS NULL OR cost_estimate_max IS NULL OR cost_estimate_max >= cost_estimate_min),
    CHECK (effort_estimate IS NULL OR effort_estimate >= 0),
    CHECK (classification_confidence IS NULL OR (classification_confidence >= 0 AND classification_confidence <= 1)),
    CHECK (classification_confidence IS NULL OR classification_rationale IS NOT NULL),
    CHECK (classification_confidence IS NULL OR classification_confidence > 0.70 OR (requires_human_review = 1 AND ai_review_status = 'AIR-HUMAN-REVIEW')),
    CHECK (ai_review_status IN ('AIR-AUTO-ACCEPTED','AIR-HUMAN-REVIEW','AIR-HUMAN-APPROVED','AIR-HUMAN-REJECTED')),
    CHECK (requires_human_review IN (0,1)),
    CHECK (import_status IS NULL OR import_status IN ('NEW','IMPORTED','UPDATED','MERGED','CONFLICT','REJECTED')),
    CHECK (is_custom IN (0,1)),
    CHECK (is_active IN (0,1))
);

CREATE INDEX idx_artifacts_type ON security_artifacts(type);
CREATE INDEX idx_artifacts_domain ON security_artifacts(primary_domain, sub_domain);
CREATE INDEX idx_artifacts_priority ON security_artifacts(priority, priority_weight);
CREATE INDEX idx_artifacts_review ON security_artifacts(next_review_date, review_frequency);
CREATE INDEX idx_artifacts_publication ON security_artifacts(publication_status, effective_date);
CREATE INDEX idx_artifacts_maturity ON security_artifacts(required_maturity_level);
CREATE INDEX idx_artifacts_ai_review ON security_artifacts(ai_review_status, requires_human_review);
CREATE INDEX idx_artifacts_import ON security_artifacts(import_status, import_source);
CREATE INDEX idx_artifacts_active ON security_artifacts(is_active, is_custom);

-- ---- Reference child tables (normalized repeatable collections) ----
CREATE TABLE artifact_tags (
    artifact_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    tag_type TEXT NOT NULL,
    tag_value TEXT NOT NULL,
    PRIMARY KEY (artifact_id, tag_type, tag_value),
    CHECK (tag_type IN ('Technology','Framework','Concept','Context','Threat','Data','Party'))
);
CREATE INDEX idx_tags_value ON artifact_tags(tag_type, tag_value);

CREATE TABLE artifact_relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    target_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE RESTRICT,
    relation_type TEXT NOT NULL,
    description TEXT,
    resolution_status TEXT,
    resolution_note TEXT,
    resolution_date TEXT,
    resolved_by TEXT,
    owner_role TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (source_id, target_id, relation_type),
    CHECK (relation_type IN ('REL-DER','REL-SAT','REL-SUP','REL-SPL','REL-IMP','REL-VER','REL-MEA','REL-MIT','REL-AFF','REL-EXC','REL-DEP','REL-CNF')),
    CHECK (resolution_status IS NULL OR resolution_status IN ('PENDING','RESOLVED','ACCEPTED','REJECTED')),
    CHECK (relation_type <> 'REL-CNF' OR (resolution_status IS NOT NULL AND resolution_note IS NOT NULL))
);
CREATE INDEX idx_rel_source ON artifact_relationships(source_id);
CREATE INDEX idx_rel_target ON artifact_relationships(target_id);

CREATE TABLE framework_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    framework TEXT NOT NULL,
    version TEXT NOT NULL,
    reference TEXT NOT NULL,
    category TEXT,
    mapping_strength TEXT NOT NULL DEFAULT 'DIRECT',
    rationale TEXT,
    UNIQUE (artifact_id, framework, version, reference),
    CHECK (mapping_strength IN ('DIRECT','INDIRECT','PARTIAL','INFORMATIVE')),
    CHECK (mapping_strength = 'DIRECT' OR (rationale IS NOT NULL AND length(trim(rationale)) > 0))
);
CREATE INDEX idx_mapping_ref ON framework_mappings(framework, version, reference);

CREATE TABLE artifact_applicability_scope (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    scope_type TEXT NOT NULL,
    scope_value TEXT NOT NULL,
    UNIQUE (artifact_id, scope_type, scope_value),
    CHECK (scope_type IN ('ORGANIZATION_SIZE','INDUSTRY','GEOGRAPHIC_REGION','BUSINESS_UNIT','ENTITY_TYPE','REGULATORY_SCOPE','REGULATORY_JURISDICTION','EXCLUSION'))
);
CREATE INDEX idx_scope ON artifact_applicability_scope(scope_type, scope_value);

CREATE TABLE artifact_self_assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'NOT_ASSESSED',
    score INTEGER,
    assessment_date TEXT,
    assessed_by TEXT,
    comments TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    CHECK (status IN ('NOT_ASSESSED','IN_PROGRESS','COMPLETED','NEEDS_REVIEW')),
    CHECK (score IS NULL OR (score >= 0 AND score <= 100))
);
CREATE INDEX idx_self_assessment ON artifact_self_assessments(status, score);

CREATE TABLE technical_dependencies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    dependency_type TEXT NOT NULL,
    dependency_name TEXT NOT NULL,
    dependency_status TEXT NOT NULL,
    CHECK (dependency_type IN ('SYSTEM','PLATFORM','VENDOR','SKILL','BUDGET')),
    CHECK (dependency_status IN ('AVAILABLE','NOT_AVAILABLE','PARTIAL','PLANNED'))
);

CREATE TABLE verification_tools (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    tool_name TEXT NOT NULL,
    tool_type TEXT NOT NULL,
    verification_method TEXT NOT NULL,
    CHECK (tool_type IN ('SIEM','EDR','IAM','VULNERABILITY','CSPM','MANUAL')),
    CHECK (verification_method IN ('API','LOG','REPORT','INTERVIEW','OBSERVATION'))
);

CREATE TABLE stakeholders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    responsibility TEXT NOT NULL,
    CHECK (responsibility IN ('OWNER','REVIEWER','APPROVER','CONSULTED','INFORMED'))
);

CREATE TABLE remediation_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    action TEXT NOT NULL,
    priority TEXT NOT NULL,
    effort_estimate INTEGER,
    responsible_role TEXT NOT NULL,
    CHECK (priority IN ('PRI-CRITICAL','PRI-HIGH','PRI-MEDIUM','PRI-LOW')),
    CHECK (effort_estimate IS NULL OR effort_estimate >= 0)
);

CREATE TABLE external_references (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT,
    description TEXT,
    CHECK (type IN ('ARTICLE','BLOG','TOOL','VIDEO','STUDY','BENCHMARK'))
);

-- ============================================================================
-- LAYER 1 (cont.): RAW PRESERVATION
-- Stores the original Raw_Catalogs envelope item verbatim + indexed drafts.
-- Placed after security_artifacts so promoted_artifact_id can reference it.
-- ============================================================================
CREATE TABLE raw_artifacts (
    id TEXT PRIMARY KEY,
    source_catalog_id TEXT NOT NULL REFERENCES source_catalogs(id) ON DELETE CASCADE,
    external_raw_id TEXT,                  -- raw_artifact_id from the source dump
    source_document TEXT,
    source_type TEXT,
    source_section TEXT,
    source_version TEXT,
    source_url TEXT,
    title_draft TEXT,
    description_draft TEXT,
    raw_text_en TEXT,
    raw_text_ar TEXT,
    original_heading TEXT,
    context_paragraph TEXT,               -- polymorphic (JSON or prose), stored as-is
    keywords_json TEXT,                   -- extracted_elements.keywords[]
    entities_mentioned_json TEXT,         -- rich variant
    usacm_type_assigned TEXT,             -- pre-classification hints (rich variant)
    sdt_domain_assigned TEXT,
    sdt_subdomain_assigned TEXT,
    requires_classification INTEGER NOT NULL DEFAULT 1,
    needs_human_review INTEGER NOT NULL DEFAULT 0,
    is_ambiguous INTEGER NOT NULL DEFAULT 0,
    ambiguity_reason TEXT,
    raw_json TEXT NOT NULL,               -- full original envelope item
    source_file TEXT,                     -- originating Raw_Catalogs filename
    content_hash TEXT,                    -- sha256 of the raw item (idempotency / change detection)
    imported_at TEXT NOT NULL DEFAULT (datetime('now')),
    promoted_artifact_id TEXT REFERENCES security_artifacts(id) ON DELETE SET NULL,
    CHECK (requires_classification IN (0,1)),
    CHECK (needs_human_review IN (0,1)),
    CHECK (is_ambiguous IN (0,1))
);
CREATE INDEX idx_raw_source ON raw_artifacts(source_catalog_id);
CREATE INDEX idx_raw_promoted ON raw_artifacts(promoted_artifact_id);
CREATE INDEX idx_raw_hash ON raw_artifacts(content_hash);

-- ============================================================================
-- LAYER 3: TEMPLATES (selections/rules over Master Catalog artifacts)
-- ============================================================================
CREATE TABLE templates (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    version TEXT NOT NULL DEFAULT '1.0',
    scope_note TEXT,                      -- who this template fits (sector/size)
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE template_items (
    id TEXT PRIMARY KEY,
    template_id TEXT NOT NULL REFERENCES templates(id) ON DELETE CASCADE,
    artifact_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE RESTRICT,
    inclusion_status TEXT NOT NULL DEFAULT 'RECOMMENDED',
    inclusion_reason TEXT,
    applicability_condition TEXT,
    priority_override TEXT,
    review_frequency_override TEXT,
    UNIQUE (template_id, artifact_id),
    CHECK (inclusion_status IN ('MANDATORY','RECOMMENDED','OPTIONAL','CONDITIONAL')),
    CHECK (priority_override IS NULL OR priority_override IN ('PRI-CRITICAL','PRI-HIGH','PRI-MEDIUM','PRI-LOW')),
    CHECK (review_frequency_override IS NULL OR review_frequency_override IN ('DAILY','WEEKLY','MONTHLY','QUARTERLY','SEMI-ANNUAL','ANNUAL','BIENNIAL','AD-HOC','CONTINUOUS'))
);
CREATE INDEX idx_template_items_template ON template_items(template_id);
CREATE INDEX idx_template_items_artifact ON template_items(artifact_id);

-- ============================================================================
-- LAYER 4: OPERATIONAL STATE (Enterprise Profiles)
-- The authoritative per-organization state. Never stored in security_artifacts.
-- ============================================================================
CREATE TABLE enterprise_profiles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    profile_kind TEXT,                    -- organization/branch/system/cloud/audit/project...
    organization_size TEXT,
    industry TEXT,
    country TEXT,
    target_maturity_level TEXT,
    source_template_id TEXT REFERENCES templates(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    CHECK (target_maturity_level IS NULL OR target_maturity_level IN ('INITIAL','REPEATABLE','DEFINED','MANAGED','OPTIMIZED'))
);

CREATE TABLE profile_artifacts (
    id TEXT PRIMARY KEY,
    profile_id TEXT NOT NULL REFERENCES enterprise_profiles(id) ON DELETE CASCADE,
    artifact_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE RESTRICT,
    template_item_id TEXT REFERENCES template_items(id) ON DELETE SET NULL,

    inclusion_status TEXT,                -- carried from template if applicable
    priority_override TEXT,

    -- The four independent operational states (never merged) — AGENTS.md Rule 8
    implementation_status TEXT NOT NULL DEFAULT 'STS-NOT-APPLIED',
    verification_status TEXT NOT NULL DEFAULT 'VER-NOT-VERIFIED',
    effectiveness TEXT NOT NULL DEFAULT 'EFF-UNKNOWN',
    exception_status TEXT NOT NULL DEFAULT 'EXC-NONE',

    current_maturity_level TEXT,
    assigned_owner TEXT,
    due_date TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),

    UNIQUE (profile_id, artifact_id),
    CHECK (inclusion_status IS NULL OR inclusion_status IN ('MANDATORY','RECOMMENDED','OPTIONAL','CONDITIONAL')),
    CHECK (priority_override IS NULL OR priority_override IN ('PRI-CRITICAL','PRI-HIGH','PRI-MEDIUM','PRI-LOW')),
    CHECK (implementation_status IN ('STS-NOT-APPLIED','STS-PARTIAL','STS-FULL','STS-PLANNED','STS-NEEDS-IMPROVEMENT')),
    CHECK (verification_status IN ('VER-NOT-VERIFIED','VER-PASS','VER-FAIL')),
    CHECK (effectiveness IN ('EFF-LOW','EFF-MEDIUM','EFF-HIGH','EFF-UNKNOWN')),
    CHECK (exception_status IN ('EXC-NONE','EXC-NOT-APPLICABLE','EXC-RISK-ACCEPTED','EXC-DEFERRED','EXC-UNAVAILABLE')),
    CHECK (current_maturity_level IS NULL OR current_maturity_level IN ('INITIAL','REPEATABLE','DEFINED','MANAGED','OPTIMIZED'))
);
CREATE INDEX idx_prof_art_profile ON profile_artifacts(profile_id);
CREATE INDEX idx_prof_art_artifact ON profile_artifacts(artifact_id);
CREATE INDEX idx_prof_art_status ON profile_artifacts(implementation_status, verification_status, effectiveness, exception_status);

CREATE TABLE profile_assessments (
    id TEXT PRIMARY KEY,
    profile_artifact_id TEXT NOT NULL REFERENCES profile_artifacts(id) ON DELETE CASCADE,
    assessment_date TEXT NOT NULL DEFAULT (datetime('now')),
    assessor_name TEXT NOT NULL,
    score REAL,
    implementation_status TEXT,           -- snapshot at assessment time
    verification_status TEXT,
    effectiveness TEXT,
    exception_status TEXT,
    comments TEXT,
    CHECK (score IS NULL OR (score >= 0 AND score <= 100)),
    CHECK (implementation_status IS NULL OR implementation_status IN ('STS-NOT-APPLIED','STS-PARTIAL','STS-FULL','STS-PLANNED','STS-NEEDS-IMPROVEMENT')),
    CHECK (verification_status IS NULL OR verification_status IN ('VER-NOT-VERIFIED','VER-PASS','VER-FAIL')),
    CHECK (effectiveness IS NULL OR effectiveness IN ('EFF-LOW','EFF-MEDIUM','EFF-HIGH','EFF-UNKNOWN')),
    CHECK (exception_status IS NULL OR exception_status IN ('EXC-NONE','EXC-NOT-APPLICABLE','EXC-RISK-ACCEPTED','EXC-DEFERRED','EXC-UNAVAILABLE'))
);
CREATE INDEX idx_prof_assess_pa ON profile_assessments(profile_artifact_id, assessment_date);

CREATE TABLE profile_evidence (
    id TEXT PRIMARY KEY,
    profile_artifact_id TEXT NOT NULL REFERENCES profile_artifacts(id) ON DELETE CASCADE,
    assessment_id TEXT REFERENCES profile_assessments(id) ON DELETE SET NULL,
    evidence_type TEXT NOT NULL,
    evidence_url TEXT,
    description TEXT,
    collected_at TEXT NOT NULL DEFAULT (datetime('now')),
    CHECK (evidence_type IN ('DOCUMENT','SCREENSHOT','LOG','REPORT','CONFIG','ATTESTATION','LINK','OTHER'))
);
CREATE INDEX idx_prof_evidence_pa ON profile_evidence(profile_artifact_id);

CREATE TABLE profile_exceptions (
    id TEXT PRIMARY KEY,
    profile_artifact_id TEXT NOT NULL REFERENCES profile_artifacts(id) ON DELETE CASCADE,
    exception_status TEXT NOT NULL,
    justification TEXT NOT NULL,
    approved_by TEXT,
    approval_date TEXT,
    expiry_date TEXT,
    risk_accepted_by TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    CHECK (exception_status IN ('EXC-NOT-APPLICABLE','EXC-RISK-ACCEPTED','EXC-DEFERRED','EXC-UNAVAILABLE'))
);
CREATE INDEX idx_prof_exc_pa ON profile_exceptions(profile_artifact_id);
