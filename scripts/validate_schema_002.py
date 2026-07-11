import sqlite3
import os
import struct
import sys

base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'migrations'))
conn = sqlite3.connect(':memory:')
conn.execute("PRAGMA foreign_keys = ON;")
for fn in ('001_initial_schema.sql', '002_assets_indicators_embeddings.sql'):
    with open(os.path.join(base, fn), 'r', encoding='utf-8') as f:
        conn.executescript(f.read())
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


print("1. Integrity + table presence...")
assert cur.execute("PRAGMA integrity_check;").fetchone()[0] == 'ok'
new_tables = {'ref_asset_types', 'enterprise_assets', 'asset_controls', 'asset_vulnerabilities',
              'asset_threats', 'threat_intelligence_sources', 'detection_tools', 'threat_indicators',
              'indicator_vulnerabilities', 'indicator_controls', 'indicator_tools',
              'indicator_recommended_actions', 'artifact_embeddings', 'equivalence_groups',
              'equivalence_group_members', 'duplicate_candidates'}
have = {r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")}
missing = new_tables - have
assert not missing, f"missing tables: {missing}"
print(f"   all {len(new_tables)} new tables present (total {len(have & (new_tables | have))}).")

# seed prerequisites from 001
cur.execute("INSERT INTO source_catalogs (id,name,source_type) VALUES ('cat','CIS','FRAMEWORK')")
cur.execute("INSERT INTO enterprise_profiles (id,name) VALUES ('prof','Org')")
for aid in ('ctrl', 'vuln', 'thr', 'ast', 'dup1', 'dup2'):
    cur.execute("INSERT INTO security_artifacts (id,type,title_en,primary_domain,sub_domain,abstraction_level,source,source_type,obligation_level,granularity_level,control_nature,control_function,testability,source_document) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (aid, 'ART-CTR', aid, 'SD-06', 'SD-06.02', 'ABS-CTR', 'SRC-STD', 'STANDARD', 'OBL-MND', 'GRN-MEDIUM', 'NAT-TEC', 'FUN-DET', 'TST-AUTO', 'doc'))

print("2. Valid inserts across new modules...")
ok("ref_asset_type", lambda: cur.execute("INSERT INTO ref_asset_types (id,name_en,category) VALUES ('rat','Server','HARDWARE')"))
ok("enterprise_asset", lambda: cur.execute("INSERT INTO enterprise_assets (id,profile_id,name,asset_type,criticality) VALUES ('as1','prof','DB Server','HARDWARE','CRITICAL')"))
ok("asset_control", lambda: cur.execute("INSERT INTO asset_controls (asset_id,artifact_id,coverage_status) VALUES ('as1','ctrl','COVERED')"))
ok("asset_vuln", lambda: cur.execute("INSERT INTO asset_vulnerabilities (asset_id,artifact_id,cve_id,cvss_score,status) VALUES ('as1','vuln','CVE-2024-1',9.8,'OPEN')"))
ok("asset_threat", lambda: cur.execute("INSERT INTO asset_threats (asset_id,artifact_id,relevance) VALUES ('as1','thr','HIGH')"))
ok("ti_source", lambda: cur.execute("INSERT INTO threat_intelligence_sources (id,name,reliability) VALUES ('src','MISP','HIGH')"))
ok("detection_tool", lambda: cur.execute("INSERT INTO detection_tools (id,name,tool_type) VALUES ('dt','Splunk','SIEM')"))
ok("threat_indicator", lambda: cur.execute("INSERT INTO threat_indicators (id,profile_id,title,indicator_class,ioc_type,ioc_value,severity_level,confidence_score,status,primary_domain,sub_domain,mitre_tactic,mitre_technique_id,source_id) "
                                           "VALUES ('ind','prof','Phishing wave','IOC','DOMAIN','evil.example','HIGH',0.9,'ACTIVE','SD-06','SD-06.02','Initial Access','T1566','src')"))
ok("indicator_vuln", lambda: cur.execute("INSERT INTO indicator_vulnerabilities (indicator_id,artifact_id,cvss_score) VALUES ('ind','vuln',9.8)"))
ok("indicator_control", lambda: cur.execute("INSERT INTO indicator_controls (indicator_id,artifact_id,control_role,coverage_pct,status) VALUES ('ind','ctrl','DETECTIVE',80,'PARTIAL')"))
ok("indicator_tool", lambda: cur.execute("INSERT INTO indicator_tools (indicator_id,detection_tool_id,coverage_pct) VALUES ('ind','dt',75)"))
ok("indicator_action", lambda: cur.execute("INSERT INTO indicator_recommended_actions (indicator_id,action,priority,status) VALUES ('ind','Block domain','PRI-HIGH','PENDING')"))

emb = struct.pack('<4f', 0.1, 0.2, 0.3, 0.4)  # dim=4 -> 16 bytes
ok("artifact_embedding (dim*4 bytes)", lambda: cur.execute("INSERT INTO artifact_embeddings (artifact_id,model_name,dim,embedding) VALUES ('ctrl','multilingual-e5-small',4,?)", (emb,)))
ok("equivalence_group", lambda: cur.execute("INSERT INTO equivalence_groups (id,label,canonical_artifact_id,concept_domain) VALUES ('eg','Asset Inventory','dup1','SD-06')"))
ok("eq member", lambda: cur.execute("INSERT INTO equivalence_group_members (group_id,artifact_id,member_role,similarity) VALUES ('eg','dup1','CANONICAL',1.0)"))
ok("dup candidate (a<b order)", lambda: cur.execute("INSERT INTO duplicate_candidates (artifact_id_a,artifact_id_b,similarity,detection_method,status) VALUES ('dup1','dup2',0.93,'EMBEDDING','PENDING')"))

print("3. Constraint enforcement (must reject)...")
bad("asset bad criticality", lambda: cur.execute("INSERT INTO enterprise_assets (id,profile_id,name,asset_type,criticality) VALUES ('asX','prof','x','HARDWARE','SEVERE')"))
bad("cvss out of range", lambda: cur.execute("INSERT INTO asset_vulnerabilities (asset_id,cvss_score) VALUES ('as1',11)"))
bad("indicator bad class", lambda: cur.execute("INSERT INTO threat_indicators (id,title,indicator_class) VALUES ('iX','t','SIGNATURE')"))
bad("indicator sub not in domain", lambda: cur.execute("INSERT INTO threat_indicators (id,title,primary_domain,sub_domain) VALUES ('iY','t','SD-03','SD-06.02')"))
bad("confidence >1", lambda: cur.execute("INSERT INTO threat_indicators (id,title,confidence_score) VALUES ('iZ','t',1.5)"))
bad("coverage_pct >100", lambda: cur.execute("INSERT INTO indicator_controls (indicator_id,artifact_id,control_role,coverage_pct) VALUES ('ind','vuln','DETECTIVE',150)"))
bad("embedding wrong byte length", lambda: cur.execute("INSERT INTO artifact_embeddings (artifact_id,model_name,dim,embedding) VALUES ('vuln','m',4,?)", (struct.pack('<3f', 1, 2, 3),)))
bad("dup a==b", lambda: cur.execute("INSERT INTO duplicate_candidates (artifact_id_a,artifact_id_b) VALUES ('ctrl','ctrl')"))
bad("dup wrong order (a>b)", lambda: cur.execute("INSERT INTO duplicate_candidates (artifact_id_a,artifact_id_b) VALUES ('dup2','dup1')"))
bad("dup bad status", lambda: cur.execute("INSERT INTO duplicate_candidates (artifact_id_a,artifact_id_b,status) VALUES ('ctrl','vuln','MERGED')"))
bad("detection_tool bad type", lambda: cur.execute("INSERT INTO detection_tools (id,name,tool_type) VALUES ('dX','x','ANTIVIRUS')"))

# FK cascade sanity: deleting a profile removes its assets
cur.execute("DELETE FROM enterprise_profiles WHERE id='prof'")
remaining = cur.execute("SELECT count(*) FROM enterprise_assets WHERE profile_id='prof'").fetchone()[0]
if remaining != 0:
    failures.append("[cascade] enterprise_assets not deleted with profile")

conn.commit()
print()
if failures:
    print("VALIDATION FAILED:")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("All 002 validation checks PASSED - assets/indicators/embeddings schema is sound.")
