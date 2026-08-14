import sqlite3
import os
import sys
import io

base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'migrations'))
conn = sqlite3.connect(':memory:')
conn.execute("PRAGMA foreign_keys = ON;")
for fn in ('001_initial_schema.sql', '002_assets_indicators_embeddings.sql',
           '003_reference_data.sql', '004_curation_layer.sql', '005_views.sql',
           '006_promotion_workflow.sql', '007_content_enrichment.sql'):
    conn.executescript(io.open(os.path.join(base, fn), encoding='utf-8').read())
cur = conn.cursor()
fails = []


def ok(d, fn):
    try:
        fn()
    except Exception as e:
        fails.append(f"[should PASS] {d}: {e}")


def bad(d, fn):
    try:
        fn()
        fails.append(f"[should FAIL] {d}")
    except sqlite3.IntegrityError:
        pass
    except Exception as e:
        fails.append(f"[wrong error] {d}: {e}")


print("1. tables/columns present...")
assert cur.execute("PRAGMA integrity_check;").fetchone()[0] == 'ok'
need = {'artifact_actions', 'artifact_variants', 'artifact_security_objectives', 'artifact_csf_functions',
        'artifact_control_purposes', 'artifact_implementation_types', 'artifact_maturity_requirements',
        'artifact_verification_evidence_types', 'scoring_policy', 'scoring_bands', 'amani_domain_alias'}
have = {r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")}
assert not (need - have), f"missing: {need - have}"
sa = {r[1] for r in cur.execute("PRAGMA table_info(security_artifacts)")}
assert {'scoring_weight', 'risk_reduction', 'effort_level', 'tier', 'evidence_required_ar', 'verification_method_note_ar'} <= sa
st = {r[1] for r in cur.execute("PRAGMA table_info(staging_artifacts)")}
assert {'title_ar', 'proposed_scoring_weight', 'proposed_actions_json', 'proposed_verification_json'} <= st
print(f"   {len(need)} new tables + columns present.")

# seed catalog artifacts
cur.execute("INSERT INTO source_catalogs (id,name) VALUES ('c','C')")
cur.execute("INSERT INTO security_artifacts (id,type,title_en,primary_domain,sub_domain,abstraction_level,source,source_type,obligation_level,granularity_level,control_nature,control_function,testability,source_document,scoring_weight,risk_reduction,effort_level,tier) "
            "VALUES ('a1','ART-CTR','t','SD-02','SD-02.01','ABS-CTR','SRC-STD','STANDARD','OBL-MND','GRN-MEDIUM','NAT-TEC','FUN-PRE','TST-AUTO','doc',6.9,5,'low','essential')")

print("2. valid inserts...")
ok("variant", lambda: cur.execute("INSERT INTO artifact_variants (id,artifact_id,platform,title_en) VALUES (1,'a1','windows','win title')"))
ok("action base", lambda: cur.execute("INSERT INTO artifact_actions (artifact_id,kind,seq,text_en,text_ar) VALUES ('a1','ACTION',0,'step 1','خطوة 1')"))
ok("action verification", lambda: cur.execute("INSERT INTO artifact_actions (artifact_id,kind,seq,text_en) VALUES ('a1','VERIFICATION',0,'verify')"))
ok("action variant", lambda: cur.execute("INSERT INTO artifact_actions (artifact_id,variant_id,kind,seq,text_en) VALUES ('a1',1,'ACTION',0,'win step')"))
ok("cia objective", lambda: cur.execute("INSERT INTO artifact_security_objectives VALUES ('a1','confidentiality','primary')"))
ok("csf function", lambda: cur.execute("INSERT INTO artifact_csf_functions VALUES ('a1','protect','primary')"))
ok("purpose", lambda: cur.execute("INSERT INTO artifact_control_purposes VALUES ('a1','preventive')"))
ok("impl type", lambda: cur.execute("INSERT INTO artifact_implementation_types VALUES ('a1','technical')"))
ok("maturity req", lambda: cur.execute("INSERT INTO artifact_maturity_requirements (artifact_id,tier_code,objective_en) VALUES ('a1','advanced','obj')"))
ok("evidence type", lambda: cur.execute("INSERT INTO artifact_verification_evidence_types VALUES ('a1','LOG')"))
ok("scoring_policy", lambda: cur.execute("INSERT INTO scoring_policy (id,critical_cap,dependency_clamp_ceiling) VALUES ('default',60,0.5)"))
ok("scoring_band", lambda: cur.execute("INSERT INTO scoring_bands VALUES ('default','fair',61,'Fair','مقبول',1)"))
ok("domain alias", lambda: cur.execute("INSERT INTO amani_domain_alias (amani_key,sdt_primary,sdt_sub) VALUES ('identity_accounts','SD-03','SD-03.02')"))

print("3. constraints reject bad values...")
bad("bad objective_code", lambda: cur.execute("INSERT INTO artifact_security_objectives VALUES ('a1','confidence','primary')"))
bad("bad strength", lambda: cur.execute("INSERT INTO artifact_security_objectives VALUES ('a1','integrity','strong')"))
bad("csf 'none' rejected", lambda: cur.execute("INSERT INTO artifact_csf_functions VALUES ('a1','detect','none')"))
bad("bad purpose", lambda: cur.execute("INSERT INTO artifact_control_purposes VALUES ('a1','magical')"))
bad("bad impl type", lambda: cur.execute("INSERT INTO artifact_implementation_types VALUES ('a1','wizardry')"))
bad("bad action kind", lambda: cur.execute("INSERT INTO artifact_actions (artifact_id,kind,seq,text_en) VALUES ('a1','STEP',5,'x')"))
bad("bad maturity tier", lambda: cur.execute("INSERT INTO artifact_maturity_requirements (artifact_id,tier_code) VALUES ('a1','expert')"))
bad("bad evidence type", lambda: cur.execute("INSERT INTO artifact_verification_evidence_types VALUES ('a1','TELEPATHY')"))
bad("scoring cap out of range", lambda: cur.execute("INSERT INTO scoring_policy (id,critical_cap,dependency_clamp_ceiling) VALUES ('x',150,0.5)"))
bad("clamp out of range", lambda: cur.execute("INSERT INTO scoring_policy (id,critical_cap,dependency_clamp_ceiling) VALUES ('y',60,2.0)"))
bad("alias sub not in primary", lambda: cur.execute("INSERT INTO amani_domain_alias (amani_key,sdt_primary,sdt_sub) VALUES ('k','SD-03','SD-06.02')"))
bad("bad tier on artifact", lambda: cur.execute("INSERT INTO security_artifacts (id,type,title_en,primary_domain,sub_domain,abstraction_level,source,source_type,obligation_level,granularity_level,requirement_type,source_document,tier) VALUES ('a2','ART-REQ','t','SD-02','SD-02.01','ABS-GOV','SRC-STD','STANDARD','OBL-MND','GRN-HIGH','RQT-STD','d','ultra')"))
bad("risk_reduction out of range", lambda: cur.execute("INSERT INTO security_artifacts (id,type,title_en,primary_domain,sub_domain,abstraction_level,source,source_type,obligation_level,granularity_level,requirement_type,source_document,risk_reduction) VALUES ('a3','ART-REQ','t','SD-02','SD-02.01','ABS-GOV','SRC-STD','STANDARD','OBL-MND','GRN-HIGH','RQT-STD','d',9)"))

conn.commit()
print()
if fails:
    print("FAILED:")
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("All 007 schema checks PASSED.")
