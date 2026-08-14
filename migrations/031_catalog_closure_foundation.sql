-- ============================================================================
-- SecureGuide - Migration 031: Catalog Closure Foundation
-- ----------------------------------------------------------------------------
-- Adds durable source manifests, versioned source-rights decisions, exactly-one
-- raw dispositions, and normalized final raw-to-canonical lineage.
--
-- This migration is additive and contains no operational/profile state.
-- Recovery: restore the pre-migration working/installed database copy. Do not
-- drop closure facts after they are populated because they are release evidence.
-- ============================================================================

PRAGMA foreign_keys = ON;

INSERT OR IGNORE INTO schema_migrations (version, description)
VALUES ('031', 'Catalog closure: source manifests, rights, raw dispositions, and final lineage');

CREATE TABLE source_import_manifests (
    id                     TEXT PRIMARY KEY,
    source_catalog_id      TEXT NOT NULL REFERENCES source_catalogs(id) ON DELETE RESTRICT,
    source_version         TEXT NOT NULL,
    version_unknown_reason TEXT,
    source_file            TEXT NOT NULL,
    source_sha256          TEXT NOT NULL,
    manifest_sha256        TEXT NOT NULL,
    retrieval_uri          TEXT,
    retrieved_at           TEXT,
    importer_name          TEXT NOT NULL,
    importer_version       TEXT NOT NULL,
    raw_record_count       INTEGER NOT NULL,
    created_at             TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (source_catalog_id, source_version, source_file, source_sha256),
    CHECK (length(source_sha256)=64 AND lower(source_sha256) NOT GLOB '*[^0-9a-f]*'),
    CHECK (length(manifest_sha256)=64 AND lower(manifest_sha256) NOT GLOB '*[^0-9a-f]*'),
    CHECK (upper(source_version) NOT IN ('UNKNOWN','CURRENT') OR length(trim(version_unknown_reason))>0),
    CHECK (raw_record_count>=0)
);
CREATE INDEX idx_source_manifest_catalog
    ON source_import_manifests(source_catalog_id, source_version);

ALTER TABLE raw_artifacts ADD COLUMN source_manifest_id TEXT
    REFERENCES source_import_manifests(id) ON DELETE RESTRICT;
CREATE INDEX idx_raw_source_manifest ON raw_artifacts(source_manifest_id);

CREATE TABLE source_rights_versions (
    id                      TEXT PRIMARY KEY,
    source_catalog_id       TEXT NOT NULL REFERENCES source_catalogs(id) ON DELETE RESTRICT,
    source_version          TEXT NOT NULL,
    rights_version          TEXT NOT NULL,
    redistribution_status   TEXT NOT NULL DEFAULT 'UNKNOWN',
    ship_raw_text           INTEGER NOT NULL DEFAULT 0,
    license_identifier      TEXT,
    terms_url               TEXT,
    evidence_sha256         TEXT,
    evidence_retrieved_at   TEXT,
    attribution_text        TEXT,
    decision_reason         TEXT NOT NULL,
    decided_by              TEXT NOT NULL,
    decided_at              TEXT NOT NULL DEFAULT (datetime('now')),
    supersedes_id           TEXT REFERENCES source_rights_versions(id) ON DELETE RESTRICT,
    is_current              INTEGER NOT NULL DEFAULT 1,
    UNIQUE (source_catalog_id, source_version, rights_version),
    CHECK (redistribution_status IN ('ALLOWED','RESTRICTED','UNKNOWN')),
    CHECK (ship_raw_text IN (0,1)),
    CHECK (ship_raw_text=0 OR redistribution_status='ALLOWED'),
    CHECK (evidence_sha256 IS NULL OR
           (length(evidence_sha256)=64 AND lower(evidence_sha256) NOT GLOB '*[^0-9a-f]*')),
    CHECK (is_current IN (0,1))
);
CREATE UNIQUE INDEX idx_source_rights_current
    ON source_rights_versions(source_catalog_id, source_version)
    WHERE is_current=1;

CREATE TABLE raw_artifact_dispositions (
    raw_artifact_id         TEXT PRIMARY KEY REFERENCES raw_artifacts(id) ON DELETE RESTRICT,
    disposition             TEXT NOT NULL,
    rationale               TEXT NOT NULL,
    related_raw_artifact_id TEXT REFERENCES raw_artifacts(id) ON DELETE RESTRICT,
    decision_method         TEXT NOT NULL,
    decision_confidence     REAL,
    requires_human_review   INTEGER NOT NULL DEFAULT 1,
    decided_by              TEXT NOT NULL,
    decided_at              TEXT NOT NULL DEFAULT (datetime('now')),
    decision_batch_id       TEXT,
    CHECK (disposition IN (
        'SUPPORTS_CANONICAL','SPLIT','DUPLICATE','CROSSWALK_ONLY',
        'RELATION_ONLY','REJECTED','DEFERRED'
    )),
    CHECK (length(trim(rationale))>0),
    CHECK (disposition<>'DUPLICATE' OR related_raw_artifact_id IS NOT NULL),
    CHECK (decision_confidence IS NULL OR
           (decision_confidence>=0 AND decision_confidence<=1)),
    CHECK (requires_human_review IN (0,1)),
    CHECK (related_raw_artifact_id IS NULL OR related_raw_artifact_id<>raw_artifact_id)
);
CREATE INDEX idx_raw_disposition
    ON raw_artifact_dispositions(disposition, requires_human_review);

CREATE TABLE artifact_source_lineage (
    artifact_id      TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE RESTRICT,
    raw_artifact_id  TEXT NOT NULL REFERENCES raw_artifacts(id) ON DELETE RESTRICT,
    lineage_role     TEXT NOT NULL,
    mapping_strength TEXT NOT NULL DEFAULT 'DIRECT',
    rationale        TEXT,
    is_primary       INTEGER NOT NULL DEFAULT 0,
    created_at       TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (artifact_id, raw_artifact_id),
    CHECK (lineage_role IN ('SUPPORTS_CANONICAL','SPLIT')),
    CHECK (mapping_strength IN ('DIRECT','INDIRECT','PARTIAL','INFORMATIVE')),
    CHECK (mapping_strength='DIRECT' OR length(trim(rationale))>0),
    CHECK (is_primary IN (0,1))
);
CREATE INDEX idx_lineage_raw ON artifact_source_lineage(raw_artifact_id, artifact_id);
CREATE UNIQUE INDEX idx_lineage_primary
    ON artifact_source_lineage(artifact_id) WHERE is_primary=1;

-- Once final lineage exists, neither side may be physically removed. Canonical
-- deprecation remains a logical update and therefore does not trigger guards.
CREATE TRIGGER trg_preserve_raw_with_lineage
BEFORE DELETE ON raw_artifacts
WHEN EXISTS (
    SELECT 1 FROM artifact_source_lineage WHERE raw_artifact_id=OLD.id
)
BEGIN
    SELECT RAISE(ABORT, 'raw artifact has final lineage and cannot be deleted');
END;

CREATE TRIGGER trg_preserve_final_lineage
BEFORE DELETE ON artifact_source_lineage
BEGIN
    SELECT RAISE(ABORT, 'final source lineage cannot be deleted');
END;

CREATE VIEW v_catalog_closure AS
SELECT
    (SELECT COUNT(*) FROM raw_artifacts) AS raw_total,
    (SELECT COUNT(*) FROM raw_artifact_dispositions) AS raw_disposed,
    (SELECT COUNT(*) FROM security_artifacts WHERE is_active=1) AS active_canonicals,
    (SELECT COUNT(DISTINCT artifact_id) FROM artifact_source_lineage) AS canonicals_with_lineage,
    (SELECT COUNT(*) FROM raw_artifacts r
      WHERE NOT EXISTS (
          SELECT 1 FROM raw_artifact_dispositions d WHERE d.raw_artifact_id=r.id
      )) AS missing_dispositions,
    (SELECT COUNT(*) FROM security_artifacts a
      WHERE a.is_active=1 AND NOT EXISTS (
          SELECT 1 FROM artifact_source_lineage l WHERE l.artifact_id=a.id
      )) AS missing_canonical_lineage;
