import sqlite3
import os
import sys

schema_path = os.path.join(os.path.dirname(__file__), '..', 'migrations', '001_initial_schema.sql')
schema_path = os.path.abspath(schema_path)

conn = sqlite3.connect(':memory:')
conn.execute("PRAGMA foreign_keys = ON;")
with open(schema_path, 'r', encoding='utf-8') as f:
    conn.executescript(f.read())
cur = conn.cursor()

failures = []


def ok(desc, fn):
    try:
        fn()
    except Exception as e:
        failures.append(f"[should PASS] {desc}: {e}")


def fail(desc, fn):
    try:
        fn()
        failures.append(f"[should FAIL but passed] {desc}")
    except sqlite3.IntegrityError:
        pass
    except Exception as e:
        failures.append(f"[wrong error type] {desc}: {e}")


print("1. Integrity check...")
if cur.execute("PRAGMA integrity_check;").fetchone()[0] != 'ok':
    print("Integrity check FAILED")
    sys.exit(1)

expected_tables = {
    'source_catalogs', 'raw_artifacts', 'security_artifacts', 'artifact_tags',
    'artifact_relationships', 'framework_mappings', 'artifact_applicability_scope',
    'artifact_self_assessments', 'technical_dependencies', 'verification_tools',
    'stakeholders', 'remediation_actions', 'external_references',
    'templates', 'template_items', 'enterprise_profiles', 'profile_artifacts',
    'profile_assessments', 'profile_evidence', 'profile_exceptions'
}
have = {r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")}
missing = expected_tables - have
if missing:
    print("MISSING TABLES:", missing)
    sys.exit(1)
print(f"   {len(have)} tables created, all {len(expected_tables)} expected present.")

FULL_CTR = ("INSERT INTO security_artifacts (id, source_catalog_id, type, title_en, "
            "primary_domain, sub_domain, abstraction_level, source, source_type, "
            "obligation_level, granularity_level, control_nature, control_function, "
            "testability, source_document) VALUES "
            "(?, 'cat-1', 'ART-CTR', 'Test Control', 'SD-03', 'SD-03.02', 'ABS-CTR', "
            "'SRC-STD', 'STANDARD', 'OBL-MND', 'GRN-MEDIUM', 'NAT-TEC', 'FUN-PRE', "
            "'TST-AUTO', 'CIS v8')")

print("2. Valid inserts across all layers...")
ok("source_catalog", lambda: cur.execute("INSERT INTO source_catalogs (id, name, source_type) VALUES ('cat-1','CIS','FRAMEWORK')"))
ok("raw_artifact", lambda: cur.execute("INSERT INTO raw_artifacts (id, source_catalog_id, raw_json) VALUES ('raw-1','cat-1','{}')"))
ok("valid ART-CTR", lambda: cur.execute(FULL_CTR, ('art-1',)))
ok("valid ART-REQ w/ requirement_type", lambda: cur.execute(
    "INSERT INTO security_artifacts (id, type, title_en, primary_domain, sub_domain, "
    "abstraction_level, source, source_type, obligation_level, granularity_level, "
    "requirement_type, source_document) VALUES ('art-2','ART-REQ','R','SD-01','SD-01.01',"
    "'ABS-GOV','SRC-REG','REGULATION','OBL-MND','GRN-HIGH','RQT-REG','NCA ECC')"))
ok("tag", lambda: cur.execute("INSERT INTO artifact_tags VALUES ('art-1','Framework','CIS')"))
ok("mapping DIRECT no rationale", lambda: cur.execute("INSERT INTO framework_mappings (artifact_id, framework, version, reference, mapping_strength) VALUES ('art-1','CIS','8','1.1','DIRECT')"))
ok("relationship REL-SAT", lambda: cur.execute("INSERT INTO artifact_relationships (source_id, target_id, relation_type) VALUES ('art-1','art-2','REL-SAT')"))
ok("REL-CNF with resolution", lambda: cur.execute("INSERT INTO artifact_relationships (source_id, target_id, relation_type, resolution_status, resolution_note) VALUES ('art-2','art-1','REL-CNF','PENDING','conflict noted')"))
ok("template", lambda: cur.execute("INSERT INTO templates (id, name) VALUES ('tpl-1','Essentials')"))
ok("template_item", lambda: cur.execute("INSERT INTO template_items (id, template_id, artifact_id, inclusion_status) VALUES ('ti-1','tpl-1','art-1','MANDATORY')"))
ok("profile", lambda: cur.execute("INSERT INTO enterprise_profiles (id, name, target_maturity_level) VALUES ('prof-1','My Org','DEFINED')"))
ok("profile_artifact", lambda: cur.execute("INSERT INTO profile_artifacts (id, profile_id, artifact_id, template_item_id, implementation_status) VALUES ('pa-1','prof-1','art-1','ti-1','STS-FULL')"))
ok("assessment", lambda: cur.execute("INSERT INTO profile_assessments (id, profile_artifact_id, assessor_name, score, effectiveness) VALUES ('as-1','pa-1','Auditor',85,'EFF-HIGH')"))
ok("evidence", lambda: cur.execute("INSERT INTO profile_evidence (id, profile_artifact_id, evidence_type, description) VALUES ('ev-1','pa-1','LOG','syslog export')"))
ok("exception", lambda: cur.execute("INSERT INTO profile_exceptions (id, profile_artifact_id, exception_status, justification) VALUES ('ex-1','pa-1','EXC-RISK-ACCEPTED','legacy system')"))

print("3. Constraint enforcement (must reject)...")
fail("invalid type", lambda: cur.execute("INSERT INTO security_artifacts (id, type, title_en, primary_domain, sub_domain, abstraction_level, source, source_type, obligation_level, granularity_level, source_document) VALUES ('x1','ART-XXX','t','SD-01','SD-01.01','ABS-GOV','SRC-REG','STANDARD','OBL-MND','GRN-HIGH','d')"))
fail("sub_domain not in primary_domain", lambda: cur.execute("INSERT INTO security_artifacts (id, type, title_en, primary_domain, sub_domain, abstraction_level, source, source_type, obligation_level, granularity_level, source_document) VALUES ('x2','ART-OBJ','t','SD-01','SD-03.02','ABS-GOV','SRC-REG','STANDARD','OBL-MND','GRN-HIGH','d')"))
fail("ART-REQ without requirement_type", lambda: cur.execute("INSERT INTO security_artifacts (id, type, title_en, primary_domain, sub_domain, abstraction_level, source, source_type, obligation_level, granularity_level, source_document) VALUES ('x3','ART-REQ','t','SD-01','SD-01.01','ABS-GOV','SRC-REG','STANDARD','OBL-MND','GRN-HIGH','d')"))
fail("ART-CTR without control fields", lambda: cur.execute("INSERT INTO security_artifacts (id, type, title_en, primary_domain, sub_domain, abstraction_level, source, source_type, obligation_level, granularity_level, source_document) VALUES ('x4','ART-CTR','t','SD-01','SD-01.01','ABS-CTR','SRC-STD','STANDARD','OBL-MND','GRN-MEDIUM','d')"))
fail("priority/weight mismatch", lambda: cur.execute("INSERT INTO security_artifacts (id, type, title_en, primary_domain, sub_domain, abstraction_level, source, source_type, obligation_level, granularity_level, control_nature, control_function, testability, source_document, priority, priority_weight) VALUES ('x5','ART-CTR','t','SD-03','SD-03.02','ABS-CTR','SRC-STD','STANDARD','OBL-MND','GRN-MEDIUM','NAT-TEC','FUN-PRE','TST-AUTO','d','PRI-LOW',7)"))
fail("low confidence without human review", lambda: cur.execute("INSERT INTO security_artifacts (id, type, title_en, primary_domain, sub_domain, abstraction_level, source, source_type, obligation_level, granularity_level, requirement_type, source_document, classification_confidence, classification_rationale, requires_human_review, ai_review_status) VALUES ('x6','ART-REQ','t','SD-01','SD-01.01','ABS-GOV','SRC-REG','REGULATION','OBL-MND','GRN-HIGH','RQT-REG','d',0.5,'weak',0,'AIR-AUTO-ACCEPTED')"))
fail("invalid ai_review_status (old value)", lambda: cur.execute("INSERT INTO security_artifacts (id, type, title_en, primary_domain, sub_domain, abstraction_level, source, source_type, obligation_level, granularity_level, requirement_type, source_document, ai_review_status) VALUES ('x7','ART-REQ','t','SD-01','SD-01.01','ABS-GOV','SRC-REG','REGULATION','OBL-MND','GRN-HIGH','RQT-REG','d','AIR-AUTO-PUBLISHED')"))
fail("invalid tag_type", lambda: cur.execute("INSERT INTO artifact_tags VALUES ('art-1','BadType','v')"))
fail("REL-CNF without resolution", lambda: cur.execute("INSERT INTO artifact_relationships (source_id, target_id, relation_type) VALUES ('art-1','art-2','REL-CNF')"))
fail("non-DIRECT mapping without rationale", lambda: cur.execute("INSERT INTO framework_mappings (artifact_id, framework, version, reference, mapping_strength) VALUES ('art-1','NIST','2.0','GV.OC','PARTIAL')"))
fail("template_item bad inclusion_status", lambda: cur.execute("INSERT INTO template_items (id, template_id, artifact_id, inclusion_status) VALUES ('ti-9','tpl-1','art-2','MUST')"))
fail("profile_artifact invalid impl status", lambda: cur.execute("INSERT INTO profile_artifacts (id, profile_id, artifact_id, implementation_status) VALUES ('pa-9','prof-1','art-2','IMP-FULL')"))
fail("duplicate profile_artifact (UNIQUE)", lambda: cur.execute("INSERT INTO profile_artifacts (id, profile_id, artifact_id) VALUES ('pa-dup','prof-1','art-1')"))

conn.commit()

print()
if failures:
    print("VALIDATION FAILED:")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("All validation checks PASSED — schema is sound.")
