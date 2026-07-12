import sqlite3
import os
import sys
import io

base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'migrations'))
conn = sqlite3.connect(':memory:')
conn.execute("PRAGMA foreign_keys = ON;")
for fn in ('001_initial_schema.sql', '002_assets_indicators_embeddings.sql',
           '003_reference_data.sql', '004_curation_layer.sql', '005_views.sql',
           '006_promotion_workflow.sql', '007_content_enrichment.sql', '008_app_entities.sql'):
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


print("1. tables present...")
assert cur.execute("PRAGMA integrity_check;").fetchone()[0] == 'ok'
need = {'glossary_terms', 'incident_playbooks', 'incident_playbook_steps', 'incident_playbook_controls',
        'incident_playbook_contacts', 'breach_checks', 'security_tool_categories', 'security_tools',
        'catalog_personas', 'catalog_persona_priority_overrides', 'catalog_persona_packs'}
have = {r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")}
assert not (need - have), f"missing: {need - have}"
assert 'category' in {r[1] for r in cur.execute("PRAGMA table_info(templates)")}
print(f"   {len(need)} app-entity tables present + templates.category.")

# prerequisites
cur.execute("INSERT INTO source_catalogs (id,name) VALUES ('c','C')")
cur.execute("INSERT INTO security_artifacts (id,type,title_en,primary_domain,sub_domain,abstraction_level,source,source_type,obligation_level,granularity_level,requirement_type,source_document) "
            "VALUES ('a1','ART-REQ','t','SD-02','SD-02.01','ABS-GOV','SRC-STD','STANDARD','OBL-MND','GRN-HIGH','RQT-STD','doc')")
cur.execute("INSERT INTO templates (id,name,category) VALUES ('TPL-PACK-1','Essentials Pack','PACK')")

print("2. valid inserts...")
ok("glossary", lambda: cur.execute("INSERT INTO glossary_terms (id,term_en,term_ar,sdt_domain) VALUES ('g1','MFA','مصادقة','SD-03')"))
ok("playbook", lambda: cur.execute("INSERT INTO incident_playbooks (id,title_en,severity) VALUES ('pb1','Account Compromise','HIGH')"))
ok("playbook step", lambda: cur.execute("INSERT INTO incident_playbook_steps (playbook_id,seq,text_en) VALUES ('pb1',0,'reset password')"))
ok("playbook control", lambda: cur.execute("INSERT INTO incident_playbook_controls (playbook_id,artifact_id,is_primary) VALUES ('pb1','a1',1)"))
ok("playbook contact", lambda: cur.execute("INSERT INTO incident_playbook_contacts (playbook_id,role_en,contact_detail) VALUES ('pb1','SOC','soc@x')"))
ok("breach check", lambda: cur.execute("INSERT INTO breach_checks (id,check_en,severity) VALUES ('bc1','Check email breach','MEDIUM')"))
ok("tool category", lambda: cur.execute("INSERT INTO security_tool_categories (id,name_en) VALUES ('cat1','Password Managers')"))
ok("security tool", lambda: cur.execute("INSERT INTO security_tools (id,category_id,name_en) VALUES ('t1','cat1','Bitwarden')"))
ok("persona", lambda: cur.execute("INSERT INTO catalog_personas (id,name_en,is_baseline) VALUES ('individual','Individual',1)"))
ok("persona override", lambda: cur.execute("INSERT INTO catalog_persona_priority_overrides VALUES ('individual','a1','PRI-HIGH')"))
ok("persona pack", lambda: cur.execute("INSERT INTO catalog_persona_packs VALUES ('individual','TPL-PACK-1')"))

print("3. constraints reject bad values...")
bad("bad sdt_domain hint", lambda: cur.execute("INSERT INTO glossary_terms (id,term_en,sdt_domain) VALUES ('g2','x','SD-99')"))
bad("bad playbook severity", lambda: cur.execute("INSERT INTO incident_playbooks (id,title_en,severity) VALUES ('pb2','x','URGENT')"))
bad("bad breach severity", lambda: cur.execute("INSERT INTO breach_checks (id,check_en,severity) VALUES ('bc2','x','MEGA')"))
bad("tool missing category (FK)", lambda: cur.execute("INSERT INTO security_tools (id,category_id,name_en) VALUES ('t2','nope','X')"))
bad("bad is_baseline", lambda: cur.execute("INSERT INTO catalog_personas (id,name_en,is_baseline) VALUES ('p2','X',2)"))
bad("bad priority_override", lambda: cur.execute("INSERT INTO catalog_persona_priority_overrides VALUES ('individual','a1','HIGH')"))
bad("persona pack bad template (FK)", lambda: cur.execute("INSERT INTO catalog_persona_packs VALUES ('individual','TPL-NOPE')"))

# FK RESTRICT: cannot delete a tool category referenced by a security tool
bad("delete referenced tool category (RESTRICT)", lambda: cur.execute("DELETE FROM security_tool_categories WHERE id='cat1'"))
# FK RESTRICT: cannot delete an artifact referenced by a persona priority override
bad("delete referenced artifact (RESTRICT)", lambda: cur.execute("DELETE FROM security_artifacts WHERE id='a1'"))

conn.commit()
print()
if fails:
    print("FAILED:")
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("All 008 schema checks PASSED.")
