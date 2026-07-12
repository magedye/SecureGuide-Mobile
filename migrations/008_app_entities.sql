-- ============================================================================
-- SecureGuide — Migration 008: App Entities
-- ----------------------------------------------------------------------------
-- Standalone app-content entities amani ships (glossary, incident playbooks,
-- breach checks, security tools, catalog personas). These are app content, not
-- USACM artifacts, so they are their own tables; where they reference a control
-- they FK to security_artifacts(id). Security "packs" reuse templates/template_items.
-- Additive only. Apply after 007.
-- ============================================================================

PRAGMA foreign_keys = ON;

INSERT OR IGNORE INTO schema_migrations (version, description)
VALUES ('008', 'App entities: glossary, playbooks, breach checks, tools, catalog personas');

-- ---- Glossary ----
CREATE TABLE IF NOT EXISTS glossary_terms (
    id             TEXT PRIMARY KEY,
    term_en        TEXT NOT NULL,
    term_ar        TEXT,
    definition_en  TEXT,
    definition_ar  TEXT,
    sdt_domain     TEXT,                    -- optional classification hint (SD-01..08)
    sort_order     INTEGER NOT NULL DEFAULT 0,
    CHECK (sdt_domain IS NULL OR sdt_domain GLOB 'SD-0[1-8]')
);

-- ---- Incident playbooks ----
CREATE TABLE IF NOT EXISTS incident_playbooks (
    id             TEXT PRIMARY KEY,
    title_en       TEXT NOT NULL,
    title_ar       TEXT,
    description_en  TEXT,
    description_ar  TEXT,
    severity       TEXT,
    sort_order     INTEGER NOT NULL DEFAULT 0,
    CHECK (severity IS NULL OR severity IN ('CRITICAL','HIGH','MEDIUM','LOW'))
);

CREATE TABLE IF NOT EXISTS incident_playbook_steps (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    playbook_id TEXT NOT NULL REFERENCES incident_playbooks(id) ON DELETE CASCADE,
    seq         INTEGER NOT NULL,
    text_en     TEXT NOT NULL,
    text_ar     TEXT,
    UNIQUE (playbook_id, seq),
    CHECK (seq >= 0)
);

CREATE TABLE IF NOT EXISTS incident_playbook_controls (
    playbook_id TEXT NOT NULL REFERENCES incident_playbooks(id) ON DELETE CASCADE,
    artifact_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE RESTRICT,
    is_primary  INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (playbook_id, artifact_id),
    CHECK (is_primary IN (0,1))
);

CREATE TABLE IF NOT EXISTS incident_playbook_contacts (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    playbook_id    TEXT NOT NULL REFERENCES incident_playbooks(id) ON DELETE CASCADE,
    role_en        TEXT,
    role_ar        TEXT,
    contact_detail TEXT,
    sort_order     INTEGER NOT NULL DEFAULT 0
);

-- ---- Breach checks ----
CREATE TABLE IF NOT EXISTS breach_checks (
    id            TEXT PRIMARY KEY,
    title_en      TEXT,
    title_ar      TEXT,
    check_en      TEXT NOT NULL,
    check_ar      TEXT,
    platform_en   TEXT,
    platform_ar   TEXT,
    safe_result_en TEXT,
    safe_result_ar TEXT,
    source_ref    TEXT,
    severity      TEXT,
    sort_order    INTEGER NOT NULL DEFAULT 0,
    CHECK (severity IS NULL OR severity IN ('CRITICAL','HIGH','MEDIUM','LOW'))
);

-- ---- Security tools ----
CREATE TABLE IF NOT EXISTS security_tool_categories (
    id         TEXT PRIMARY KEY,
    name_en    TEXT NOT NULL,
    name_ar    TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS security_tools (
    id             TEXT PRIMARY KEY,
    category_id    TEXT NOT NULL REFERENCES security_tool_categories(id) ON DELETE RESTRICT,
    name_en        TEXT NOT NULL,
    name_ar        TEXT,
    description_en  TEXT,
    description_ar  TEXT,
    source_ref     TEXT,
    url            TEXT,
    sort_order     INTEGER NOT NULL DEFAULT 0
);

-- ---- Catalog personas (reference personas; distinct from operational enterprise_profiles) ----
CREATE TABLE IF NOT EXISTS catalog_personas (
    id             TEXT PRIMARY KEY,
    name_en        TEXT NOT NULL,
    name_ar        TEXT,
    description_en  TEXT,
    description_ar  TEXT,
    is_baseline    INTEGER NOT NULL DEFAULT 0,
    sort_order     INTEGER NOT NULL DEFAULT 0,
    CHECK (is_baseline IN (0,1))
);

CREATE TABLE IF NOT EXISTS catalog_persona_priority_overrides (
    persona_id        TEXT NOT NULL REFERENCES catalog_personas(id) ON DELETE CASCADE,
    artifact_id       TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE RESTRICT,
    priority_override TEXT NOT NULL,
    PRIMARY KEY (persona_id, artifact_id),
    CHECK (priority_override IN ('PRI-CRITICAL','PRI-HIGH','PRI-MEDIUM','PRI-LOW'))
);

CREATE TABLE IF NOT EXISTS catalog_persona_packs (
    persona_id  TEXT NOT NULL REFERENCES catalog_personas(id) ON DELETE CASCADE,
    template_id TEXT NOT NULL REFERENCES templates(id) ON DELETE CASCADE,
    PRIMARY KEY (persona_id, template_id)
);

-- Optional: tag a template as a marketable "pack" (amani security_packs = templates)
ALTER TABLE templates ADD COLUMN category TEXT;
