-- ============================================================================
-- SecureGuide — Migration 005: Curation & Product Views (read-only)
-- ----------------------------------------------------------------------------
-- Read models for curation and the profile product surface (brief §6).
-- Views compute from state; they never duplicate storage. Run after 001-004.
-- ============================================================================

INSERT OR IGNORE INTO schema_migrations (version, description)
VALUES ('005', 'Curation & product read-only views');

-- 1) Human review queue: low-confidence / flagged staging + catalog items.
DROP VIEW IF EXISTS v_review_queue;
CREATE VIEW v_review_queue AS
    SELECT 'STAGING' AS source, s.id AS item_id, s.title_en AS title,
           s.proposed_primary_domain AS primary_domain,
           s.classification_confidence AS confidence,
           s.curation_status AS status, s.reviewer AS reviewer
    FROM staging_artifacts s
    WHERE s.curation_status IN ('NEEDS_REVIEW','DEDUP_REVIEW')
       OR s.requires_human_review = 1
    UNION ALL
    SELECT 'CATALOG' AS source, a.id, a.title_en, a.primary_domain,
           a.classification_confidence, a.ai_review_status, NULL
    FROM security_artifacts a
    WHERE a.requires_human_review = 1
       OR a.ai_review_status = 'AIR-HUMAN-REVIEW';

-- 2) Pending near-duplicate candidates with both titles, strongest first.
DROP VIEW IF EXISTS v_duplicate_candidates;
CREATE VIEW v_duplicate_candidates AS
    SELECT d.id, d.artifact_id_a, aa.title_en AS title_a,
           d.artifact_id_b, ab.title_en AS title_b,
           d.similarity, d.detection_method, d.status
    FROM duplicate_candidates d
    JOIN security_artifacts aa ON aa.id = d.artifact_id_a
    JOIN security_artifacts ab ON ab.id = d.artifact_id_b
    WHERE d.status = 'PENDING'
    ORDER BY d.similarity DESC;

-- 3) Curation progress: counts by status and domain over the staging set.
DROP VIEW IF EXISTS v_catalog_curation;
CREATE VIEW v_catalog_curation AS
    SELECT curation_status,
           proposed_primary_domain AS primary_domain,
           COUNT(*) AS items,
           AVG(classification_confidence) AS avg_confidence,
           AVG(quality_score) AS avg_quality
    FROM staging_artifacts
    GROUP BY curation_status, proposed_primary_domain;

-- 4) Artifact detail: catalog row + aggregated tags + mapping/relationship counts.
DROP VIEW IF EXISTS v_artifact_detail;
CREATE VIEW v_artifact_detail AS
    SELECT a.id, a.type, a.title_en, a.definition_short_en,
           a.primary_domain, a.sub_domain, a.abstraction_level,
           a.obligation_level, a.priority, a.publication_status,
           a.classification_confidence, a.ai_review_status, a.is_active,
           (SELECT GROUP_CONCAT(t.tag_type || ':' || t.tag_value, '; ')
              FROM artifact_tags t WHERE t.artifact_id = a.id) AS tags,
           (SELECT COUNT(*) FROM framework_mappings m WHERE m.artifact_id = a.id) AS mapping_count,
           (SELECT COUNT(*) FROM artifact_relationships r
              WHERE r.source_id = a.id OR r.target_id = a.id) AS relationship_count
    FROM security_artifacts a;

-- 5) Profile dashboard: operational rollup per enterprise profile.
DROP VIEW IF EXISTS v_profile_dashboard;
CREATE VIEW v_profile_dashboard AS
    SELECT p.id AS profile_id, p.name,
           COUNT(pa.id) AS total_items,
           SUM(CASE WHEN pa.implementation_status = 'STS-FULL' THEN 1 ELSE 0 END) AS implemented_full,
           SUM(CASE WHEN pa.implementation_status = 'STS-PARTIAL' THEN 1 ELSE 0 END) AS implemented_partial,
           SUM(CASE WHEN pa.implementation_status = 'STS-NOT-APPLIED' THEN 1 ELSE 0 END) AS not_applied,
           SUM(CASE WHEN pa.verification_status = 'VER-PASS' THEN 1 ELSE 0 END) AS verified_pass,
           SUM(CASE WHEN pa.exception_status <> 'EXC-NONE' THEN 1 ELSE 0 END) AS with_exception
    FROM enterprise_profiles p
    LEFT JOIN profile_artifacts pa ON pa.profile_id = p.id
    GROUP BY p.id, p.name;

-- 6) Gap analysis: profile items not fully implemented and not excepted.
DROP VIEW IF EXISTS v_gap_analysis;
CREATE VIEW v_gap_analysis AS
    SELECT pa.profile_id, pa.artifact_id, a.title_en,
           a.primary_domain, a.sub_domain, a.priority,
           pa.implementation_status, pa.verification_status,
           pa.effectiveness, pa.exception_status, pa.due_date
    FROM profile_artifacts pa
    JOIN security_artifacts a ON a.id = pa.artifact_id
    WHERE pa.implementation_status <> 'STS-FULL'
      AND pa.exception_status = 'EXC-NONE';
