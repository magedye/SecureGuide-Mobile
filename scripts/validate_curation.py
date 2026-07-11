# -*- coding: utf-8 -*-
"""Apply the full migration stack (001..005) and validate the curation layer:
integrity, table/view presence, staging + consolidation constraints, and that
every view is selectable."""
import io
import os
import sqlite3
import sys

MIG = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'migrations'))
FILES = ['001_initial_schema.sql', '002_assets_indicators_embeddings.sql',
         '003_reference_data.sql', '004_curation_layer.sql', '005_views.sql']

conn = sqlite3.connect(':memory:')
conn.execute("PRAGMA foreign_keys = ON;")
for fn in FILES:
    conn.executescript(io.open(os.path.join(MIG, fn), encoding='utf-8').read())
cur = conn.cursor()
failures = []


def ok(desc, fn):
    try:
        fn()
    except Exception as e:
        failures.append(f"[should PASS] {desc}: {e}")


def bad(desc, fn):
    try:
        fn()
        failures.append(f"[should FAIL but passed] {desc}")
    except sqlite3.IntegrityError:
        pass
    except Exception as e:
        failures.append(f"[wrong error] {desc}: {e}")


print("1. Integrity + object presence...")
assert cur.execute("PRAGMA integrity_check;").fetchone()[0] == 'ok'
tables = {r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")}
views = {r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='view'")}
need_t = {'schema_migrations', 'curation_batches', 'staging_artifacts',
          'consolidation_decisions', 'consolidation_members', 'curation_lessons'}
need_v = {'v_review_queue', 'v_duplicate_candidates', 'v_catalog_curation',
          'v_artifact_detail', 'v_profile_dashboard', 'v_gap_analysis'}
assert not (need_t - tables), f"missing tables: {need_t - tables}"
assert not (need_v - views), f"missing views: {need_v - views}"
mig = cur.execute("SELECT count(*) FROM schema_migrations").fetchone()[0]
print(f"   {len(tables)} tables, {len(views)} views, {mig} migrations recorded.")

print("2. Curation-layer valid inserts...")
ok("batch", lambda: cur.execute("INSERT INTO curation_batches (id, name, status) VALUES ('b1','CIS batch','OPEN')"))
cur.execute("INSERT INTO source_catalogs (id,name,source_type) VALUES ('cat','CIS','FRAMEWORK')")
cur.execute("INSERT INTO raw_artifacts (id,source_catalog_id,raw_json) VALUES ('raw','cat','{}')")
ok("staging draft (unclassified)", lambda: cur.execute(
    "INSERT INTO staging_artifacts (id, batch_id, raw_artifact_id, title_en, curation_status) "
    "VALUES ('st1','b1','raw','Enterprise Asset Inventory','DRAFT')"))
ok("staging classified + belongs-to", lambda: cur.execute(
    "INSERT INTO staging_artifacts (id, title_en, proposed_type, proposed_abstraction_level, "
    "proposed_primary_domain, proposed_sub_domain, classification_confidence, classification_rationale, "
    "curation_status, quality_score, merge_action) VALUES "
    "('st2','Privileged Access Review','ART-CTR','ABS-CTR','SD-03','SD-03.04',0.88,'IAM review','CLASSIFIED',72,'CANONICALIZE')"))
# promoted catalog artifacts for consolidation
for aid in ('a1', 'a2'):
    cur.execute("INSERT INTO security_artifacts (id,type,title_en,primary_domain,sub_domain,abstraction_level,source,source_type,obligation_level,granularity_level,requirement_type,source_document) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (aid, 'ART-REQ', aid, 'SD-02', 'SD-02.01', 'ABS-GOV', 'SRC-STD', 'STANDARD', 'OBL-MND', 'GRN-HIGH', 'RQT-STD', 'doc'))
ok("consolidation decision", lambda: cur.execute("INSERT INTO consolidation_decisions (id, decision, canonical_artifact_id, rationale) VALUES ('cd1','CANONICALIZE','a1','same asset-inventory concept from CIS/NIST/NCA')"))
ok("decision member canonical", lambda: cur.execute("INSERT INTO consolidation_members (decision_id, artifact_id, role) VALUES ('cd1','a1','CANONICAL')"))
ok("decision member source", lambda: cur.execute("INSERT INTO consolidation_members (decision_id, artifact_id, role) VALUES ('cd1','a2','SOURCE')"))
ok("lesson", lambda: cur.execute("INSERT INTO curation_lessons (lesson_type, pattern, example, action) VALUES ('TIE_BREAKER','Cloud IAM -> SD-03 not SD-04','Azure AD roles','reinforce tie-breaker')"))

print("3. Curation-layer constraint enforcement (must reject)...")
bad("bad curation_status", lambda: cur.execute("INSERT INTO staging_artifacts (id, curation_status) VALUES ('x1','PUBLISHED')"))
bad("bad merge_action", lambda: cur.execute("INSERT INTO staging_artifacts (id, merge_action) VALUES ('x2','MERGE_ALL')"))
bad("staging sub not in domain", lambda: cur.execute("INSERT INTO staging_artifacts (id, proposed_primary_domain, proposed_sub_domain) VALUES ('x3','SD-03','SD-06.02')"))
bad("staging bad proposed_type", lambda: cur.execute("INSERT INTO staging_artifacts (id, proposed_type) VALUES ('x4','ART-XXX')"))
bad("quality_score > 100", lambda: cur.execute("INSERT INTO staging_artifacts (id, quality_score) VALUES ('x5',150)"))
bad("bad consolidation decision", lambda: cur.execute("INSERT INTO consolidation_decisions (id, decision) VALUES ('x6','MERGE')"))
bad("bad member role", lambda: cur.execute("INSERT INTO consolidation_members (decision_id, artifact_id, role) VALUES ('cd1','a1','BOSS')"))
bad("bad batch status", lambda: cur.execute("INSERT INTO curation_batches (id, status) VALUES ('x7','DONE')"))
bad("bad lesson_type", lambda: cur.execute("INSERT INTO curation_lessons (lesson_type, pattern) VALUES ('RANDOM','x')"))

print("4. All views are selectable...")
for v in sorted(need_v):
    ok(f"select {v}", lambda v=v: cur.execute(f"SELECT * FROM {v} LIMIT 5").fetchall())

# seed a profile so dashboard/gap views have data, then re-query
cur.execute("INSERT INTO enterprise_profiles (id,name) VALUES ('p','Org')")
cur.execute("INSERT INTO profile_artifacts (id,profile_id,artifact_id,implementation_status) VALUES ('pa','p','a1','STS-PARTIAL')")
ok("v_profile_dashboard has row", lambda: (cur.execute("SELECT total_items FROM v_profile_dashboard WHERE profile_id='p'").fetchone()[0] == 1) or (_ for _ in ()).throw(AssertionError('no row')))
ok("v_gap_analysis flags partial", lambda: (cur.execute("SELECT count(*) FROM v_gap_analysis WHERE profile_id='p'").fetchone()[0] == 1) or (_ for _ in ()).throw(AssertionError('gap not flagged')))
ok("v_review_queue includes staging", lambda: cur.execute("SELECT count(*) FROM v_review_queue").fetchone())

conn.commit()
print()
if failures:
    print("VALIDATION FAILED:")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("All curation-layer checks PASSED - staging, consolidation, and views are sound.")
