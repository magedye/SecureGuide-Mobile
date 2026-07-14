-- ============================================================================
-- SecureGuide — Migration 018: Classification Fallback Governance
-- ----------------------------------------------------------------------------
-- Makes the SADP fallback vocabulary explicit without weakening the normative
-- USACM/SDT catalog constraints.  Lookup membership alone is not permission to
-- publish a value: UNKNOWN/MULTI are review signals, type/domain/sub-domain
-- never have fallbacks, and type-conditional N/A is represented structurally.
-- ============================================================================

PRAGMA foreign_keys = ON;

INSERT OR IGNORE INTO schema_migrations (version, description)
VALUES ('018', 'Explicit fallback disposition and fail-closed publication governance');

CREATE TABLE IF NOT EXISTS classification_fallback_policy (
    dimension            TEXT PRIMARY KEY,
    lookup_table         TEXT NOT NULL,
    fallback_mode        TEXT NOT NULL,
    not_applicable_code  TEXT,
    unknown_code         TEXT,
    multi_code           TEXT,
    na_disposition       TEXT NOT NULL,
    unknown_disposition  TEXT NOT NULL,
    multi_disposition    TEXT NOT NULL,
    rationale            TEXT NOT NULL,
    CHECK (fallback_mode IN ('NONE','TRIPLE')),
    CHECK (na_disposition IN ('FORBIDDEN','PUBLISHABLE','STRUCTURAL_NULL','REVIEW_ONLY','NORMALIZE_VALUES')),
    CHECK (unknown_disposition IN ('FORBIDDEN','PUBLISHABLE','STRUCTURAL_NULL','REVIEW_ONLY','NORMALIZE_VALUES')),
    CHECK (multi_disposition IN ('FORBIDDEN','PUBLISHABLE','STRUCTURAL_NULL','REVIEW_ONLY','NORMALIZE_VALUES')),
    CHECK (
        (fallback_mode = 'NONE'
         AND not_applicable_code IS NULL AND unknown_code IS NULL AND multi_code IS NULL
         AND na_disposition = 'FORBIDDEN'
         AND unknown_disposition = 'FORBIDDEN'
         AND multi_disposition = 'FORBIDDEN')
        OR
        (fallback_mode = 'TRIPLE'
         AND not_applicable_code IS NOT NULL AND unknown_code IS NOT NULL AND multi_code IS NOT NULL)
    )
);

-- Identity and lifecycle dimensions use their native controlled values only.
INSERT OR REPLACE INTO classification_fallback_policy VALUES
 ('artifact_type','lk_artifact_type','NONE',NULL,NULL,NULL,'FORBIDDEN','FORBIDDEN','FORBIDDEN','An artifact must have one real USACM type.'),
 ('primary_domain','lk_sdt_domain','NONE',NULL,NULL,NULL,'FORBIDDEN','FORBIDDEN','FORBIDDEN','Every artifact must have one real SDT primary domain.'),
 ('sub_domain','lk_sdt_subdomain','NONE',NULL,NULL,NULL,'FORBIDDEN','FORBIDDEN','FORBIDDEN','Every artifact must have one real SDT sub-domain belonging to its primary domain.'),
 ('implementation_status','lk_implementation_status','NONE',NULL,NULL,NULL,'FORBIDDEN','FORBIDDEN','FORBIDDEN','Use native STS-* operational states.'),
 ('verification_status','lk_verification_status','NONE',NULL,NULL,NULL,'FORBIDDEN','FORBIDDEN','FORBIDDEN','Use VER-NOT-VERIFIED rather than a generic fallback.'),
 ('relationship_type','lk_relationship_type','NONE',NULL,NULL,NULL,'FORBIDDEN','FORBIDDEN','FORBIDDEN','A relationship row must state one real REL-* meaning.'),
 ('ai_review_status','lk_ai_review_status','NONE',NULL,NULL,NULL,'FORBIDDEN','FORBIDDEN','FORBIDDEN','Use the native AI review workflow values.'),
 ('publication_status','lk_publication_status','NONE',NULL,NULL,NULL,'FORBIDDEN','FORBIDDEN','FORBIDDEN','Use the native publication lifecycle values.'),
 ('source_type','lk_source_type','NONE',NULL,NULL,NULL,'FORBIDDEN','FORBIDDEN','FORBIDDEN','Use a real controlled source type.'),
 ('asset_type','lk_asset_type','NONE',NULL,NULL,NULL,'FORBIDDEN','FORBIDDEN','FORBIDDEN','ART-AST requires one real asset type; other types use structural NULL.'),
 ('maturity_level','lk_maturity_level','NONE',NULL,NULL,NULL,'FORBIDDEN','FORBIDDEN','FORBIDDEN','Use a native maturity value or an optional NULL where the schema permits it.'),
 ('cost_category','lk_cost_category','NONE',NULL,NULL,NULL,'FORBIDDEN','FORBIDDEN','FORBIDDEN','Use a native cost category or an optional NULL.'),
 ('import_status','lk_import_status','NONE',NULL,NULL,NULL,'FORBIDDEN','FORBIDDEN','FORBIDDEN','Use the native import workflow values.'),
 ('tag_type','lk_tag_type','NONE',NULL,NULL,NULL,'FORBIDDEN','FORBIDDEN','FORBIDDEN','Tags use the seven approved normalized tag types.'),

-- Triple-bearing dimensions.  REVIEW_ONLY values may exist in lookup/UI review
-- vocabulary but are never valid in APPROVED/PUBLISHED catalog records.
 ('abstraction_level','lk_abstraction_level','TRIPLE','ABS-NA','ABS-UNKNOWN','ABS-MULTI','REVIEW_ONLY','REVIEW_ONLY','REVIEW_ONLY','The normalized catalog requires one real abstraction level.'),
 ('obligation_source','lk_obligation_source','TRIPLE','SRC-NA','SRC-UNKNOWN','SRC-MULTI','REVIEW_ONLY','REVIEW_ONLY','REVIEW_ONLY','The normalized catalog requires one real obligation source.'),
 ('obligation_level','lk_obligation_level','TRIPLE','OBL-NA','OBL-UNKNOWN','OBL-MULTI','REVIEW_ONLY','REVIEW_ONLY','REVIEW_ONLY','The normalized catalog requires one real obligation level.'),
 ('granularity_level','lk_granularity_level','TRIPLE','GRN-NA','GRN-UNKNOWN','GRN-MULTI','REVIEW_ONLY','REVIEW_ONLY','REVIEW_ONLY','The normalized catalog requires one real granularity level.'),
 ('priority','lk_priority','TRIPLE','PRI-NA','PRI-UNKNOWN','PRI-MULTI','REVIEW_ONLY','REVIEW_ONLY','REVIEW_ONLY','The catalog baseline priority must be a real PRI-* value.'),
 ('control_nature','lk_control_nature','TRIPLE','NAT-NA','NAT-UNKNOWN','NAT-MULTI','STRUCTURAL_NULL','REVIEW_ONLY','REVIEW_ONLY','Non-controls use NULL; ART-CTR/ART-CTE require one real nature.'),
 ('control_function','lk_control_function','TRIPLE','FUN-NA','FUN-UNKNOWN','FUN-MULTI','STRUCTURAL_NULL','REVIEW_ONLY','REVIEW_ONLY','Non-controls use NULL; ART-CTR/ART-CTE require one real function.'),
 ('requirement_type','lk_requirement_type','TRIPLE','RQT-NA','RQT-UNKNOWN','RQT-MULTI','STRUCTURAL_NULL','REVIEW_ONLY','REVIEW_ONLY','Non-requirements use NULL; ART-REQ requires one real requirement type.'),
 ('testability','lk_testability','TRIPLE','TST-NA','TST-UNKNOWN','TST-MULTI','PUBLISHABLE','REVIEW_ONLY','REVIEW_ONLY','TST-NA is a native USACM value; uncertainty still requires review.'),
 ('effectiveness','lk_effectiveness','TRIPLE','EFF-NA','EFF-UNKNOWN','EFF-MULTI','REVIEW_ONLY','PUBLISHABLE','REVIEW_ONLY','EFF-UNKNOWN is the native reference baseline, not an unresolved classification.'),
 ('exception_status','lk_exception_status','TRIPLE','EXC-NOT-APPLICABLE','EXC-UNKNOWN','EXC-MULTI','PUBLISHABLE','REVIEW_ONLY','REVIEW_ONLY','EXC-NOT-APPLICABLE is a native profile exception; uncertainty is not publishable.'),
 ('threat','lk_threat','TRIPLE','THR-NA','THR-UNKNOWN','THR-MULTI','PUBLISHABLE','REVIEW_ONLY','NORMALIZE_VALUES','Multiple threats are stored as multiple artifact_threats rows, never as THR-MULTI in an approved artifact.'),
 ('review_frequency','lk_review_frequency','TRIPLE','NA','UNKNOWN','MULTI','REVIEW_ONLY','REVIEW_ONLY','REVIEW_ONLY','Use a real cadence; the catalog baseline is AD-HOC.'),
 ('mapping_strength','lk_mapping_strength','TRIPLE','NA','UNKNOWN','MULTI','REVIEW_ONLY','REVIEW_ONLY','NORMALIZE_VALUES','Each mapping row has one real strength; multiple mappings use multiple rows.');

CREATE VIEW IF NOT EXISTS v_nonpublishable_fallback_codes AS
SELECT dimension, not_applicable_code AS code, na_disposition AS disposition
  FROM classification_fallback_policy WHERE fallback_mode='TRIPLE' AND na_disposition <> 'PUBLISHABLE'
UNION ALL
SELECT dimension, unknown_code, unknown_disposition
  FROM classification_fallback_policy WHERE fallback_mode='TRIPLE' AND unknown_disposition <> 'PUBLISHABLE'
UNION ALL
SELECT dimension, multi_code, multi_disposition
  FROM classification_fallback_policy WHERE fallback_mode='TRIPLE' AND multi_disposition <> 'PUBLISHABLE';
