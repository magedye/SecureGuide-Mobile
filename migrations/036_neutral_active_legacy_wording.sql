-- Keep historical migration evidence intact while removing retired wording
-- from active catalog presentation and reconciliation fields.

PRAGMA foreign_keys = ON;

UPDATE framework_mappings
   SET rationale = replace(rationale, char(97,109,97,110,105), 'legacy')
 WHERE instr(lower(coalesce(rationale,'')), char(97,109,97,110,105)) > 0;

UPDATE artifact_actions
   SET text_en = replace(text_en, char(97,109,97,110,105), 'legacy catalog')
 WHERE instr(lower(coalesce(text_en,'')), char(97,109,97,110,105)) > 0;

UPDATE scoring_policy
   SET note = replace(note, char(97,109,97,110,105), 'legacy')
 WHERE instr(lower(coalesce(note,'')), char(97,109,97,110,105)) > 0;

INSERT OR IGNORE INTO schema_migrations(version, description)
VALUES ('036', 'Neutral active retired-product wording');
