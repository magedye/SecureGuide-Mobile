-- ============================================================================
-- SecureGuide — Migration 015: Platform vocabulary extension (SADP §2.6 record)
-- ----------------------------------------------------------------------------
-- artifact_platforms (migration 012) normalizes platform applicability that used
-- to ride on tags. amani's catalog references five platform identifiers absent
-- from lk_platform; add them so platforms round-trip losslessly. Additive.
-- Recorded in docs/SADP_CONFORMANCE.md §6 (change control).
-- ============================================================================

INSERT OR IGNORE INTO schema_migrations (version, description)
VALUES ('015', 'Extend lk_platform with active_directory/desktop/laptop/mobile/windows_server (SADP 2.6)');

INSERT OR IGNORE INTO lk_platform (code, name_en, name_ar, sort_order) VALUES
 ('desktop', 'Desktop', 'حاسب مكتبي', 20),
 ('laptop', 'Laptop', 'حاسب محمول', 21),
 ('mobile', 'Mobile', 'محمول', 22),
 ('windows_server', 'Windows Server', 'خادم ويندوز', 23),
 ('active_directory', 'Active Directory', 'الدليل النشط', 24);
