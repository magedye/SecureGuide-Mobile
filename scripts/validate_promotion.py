# -*- coding: utf-8 -*-
"""20 acceptance tests for the promotion workflow (promote.py). Rebuilds a fresh
DB, runs the full chain, and asserts safety, idempotency, staleness rejection,
rollback, all-or-nothing, and that rejected/needs-review items never promote."""
import io
import json
import os
import subprocess
import sqlite3
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB = os.path.join(ROOT, 'promotion_test.db')
PLANDIR = os.path.join(ROOT, 'consolidation', 'promotion')
PY = sys.executable
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import _promote_common as C
fails = []


def run(*a):
    return subprocess.run([PY] + list(a), cwd=ROOT, capture_output=True)


def check(n, c):
    print(("PASS" if c else "FAIL"), "-", n)
    if not c:
        fails.append(n)


def cnt(conn, t, where=''):
    return conn.execute(f"SELECT COUNT(*) FROM {t} {where}").fetchone()[0]


def base_row(**kw):
    r = {k: None for k in ('title_en', 'definition_short_en', 'definition_full_en', 'objective_en',
        'canonical_statement', 'proposed_type', 'proposed_abstraction_level', 'proposed_primary_domain',
        'proposed_sub_domain', 'proposed_obligation_level', 'proposed_requirement_type', 'proposed_control_nature',
        'proposed_control_function', 'proposed_testability', 'proposed_asset_type', 'proposed_asset_criticality',
        'proposed_mappings_json', 'merge_action', 'ready_for_promotion', 'final_review_status', 'curation_status',
        'requires_human_review', 'classification_confidence', 'promotion_blockers')}
    r.update(ready_for_promotion=1, final_review_status='APPROVED', curation_status='APPROVED',
             requires_human_review=0, classification_confidence=0.9, title_en='T', definition_short_en='def',
             proposed_type='ART-REQ', proposed_abstraction_level='ABS-CTR', proposed_primary_domain='SD-02',
             proposed_sub_domain='SD-02.01', proposed_obligation_level='OBL-MND', proposed_requirement_type='RQT-STD',
             proposed_mappings_json=json.dumps([{'raw_id': 'x', 'source_document': 'CIS', 'mapping_strength': 'DIRECT'}]))
    r.update(kw)
    return r


# ---- build fresh DB through final_review ----
if os.path.exists(DB):
    os.remove(DB)
run('scripts/ingest_raw.py', '--db', DB)
run('scripts/pilot_asset_inventory.py', '--db', DB, '--apply')
run('scripts/final_review.py', '--db', DB)
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA foreign_keys=ON")
valid = C.load_valid(conn)
raw0 = cnt(conn, 'raw_artifacts')
stg0 = cnt(conn, 'staging_artifacts')

# inject a threat on AI-06 to exercise the THR-* normalization (SADP §2.4/§3.1).
# threats ARE in the hash fields, so recompute the content_hash to keep the plan fresh.
conn.execute("UPDATE staging_artifacts SET proposed_threats_json=? WHERE id='STG-CANON-AI-06'",
             (json.dumps([{'threat_code': 'THR-PHISHING'}]),))
_r = conn.execute("SELECT * FROM staging_artifacts WHERE id='STG-CANON-AI-06'").fetchone()
conn.execute("UPDATE staging_artifacts SET content_hash=? WHERE id='STG-CANON-AI-06'", (C.content_hash(_r),))
conn.commit()

print("# unit-level rejection tests (1-6)")
check("1. reject unapproved item", C.promotion_blockers(base_row(final_review_status='DEFERRED', ready_for_promotion=0), valid))
check("2. reject item with declared blockers", C.promotion_blockers(base_row(promotion_blockers=json.dumps(['open question'])), valid))
check("3. reject item missing type field (ART-REQ w/o requirement_type)", C.promotion_blockers(base_row(proposed_requirement_type=None), valid))
check("4. reject invalid SDT sub_domain", C.promotion_blockers(base_row(proposed_sub_domain='SD-09.09'), valid))
check("5. reject invalid USACM type", C.promotion_blockers(base_row(proposed_type='ART-XXX'), valid))
check("6. reject incomplete lineage", C.promotion_blockers(base_row(proposed_mappings_json=json.dumps([])), valid))
check("6b. reject free-form tags (SADP §2.4)",
      any('2.4' in b or 'tags' in b for b in C.promotion_blockers(base_row(proposed_tags_json=json.dumps([{'tag_type': 'Framework', 'tag_value': 'CIS'}])), valid)))
check("6c. reject invalid threat_code", C.promotion_blockers(base_row(proposed_threats_json=json.dumps(['THR-BOGUS'])), valid))
check("bonus: valid row has no blockers", not C.promotion_blockers(base_row(), valid))

print("# plan/apply/idempotency (7-11)")
before = cnt(conn, 'security_artifacts')
run('scripts/promote.py', 'plan', '--db', DB, '--batch', 'T1')
check("7. plan writes nothing to catalog", cnt(conn, 'security_artifacts') == before == 0)
r1 = run('scripts/promote.py', 'apply', '--db', DB, '--plan', os.path.join(PLANDIR, 'plan-T1.json'))
check("8. apply promotes 4 approved items", cnt(conn, 'security_artifacts') == 4)
check("9. mappings normalized", cnt(conn, 'framework_mappings') >= 4)
check("10. threats normalized (THR-PHISHING on AI-06)", cnt(conn, "artifact_threats", "WHERE threat_code='THR-PHISHING'") == 1)
check("10b. every promoted artifact has >=1 threat (THR-NA fallback)",
      cnt(conn, 'security_artifacts', "WHERE id NOT IN (SELECT artifact_id FROM artifact_threats)") == 0)
check("10c. no tags written (SADP §2.4)", cnt(conn, 'artifact_tags') == 0)
run('scripts/promote.py', 'apply', '--db', DB, '--plan', os.path.join(PLANDIR, 'plan-T1.json'))
check("11. idempotent re-apply (still 4)", cnt(conn, 'security_artifacts') == 4)

print("# rejected / needs-review never promoted (17-18)")
check("17. rejected AI-03 not promoted", cnt(conn, 'security_artifacts', "WHERE id LIKE '%AI-03%'") == 0)
check("18. no requires_human_review item promoted",
      cnt(conn, "staging_artifacts", "WHERE requires_human_review=1 AND promoted_artifact_id IS NOT NULL") == 0)
check("integrity ok after apply", conn.execute("PRAGMA integrity_check").fetchone()[0] == 'ok')  # part of 20

print("# invariants during apply (14-15)")
check("14. raw unchanged after apply", cnt(conn, 'raw_artifacts') == raw0)
check("15. staging preserved after apply", cnt(conn, 'staging_artifacts') == stg0)

print("# stale-plan rejection (12)")
row = conn.execute("SELECT title_en, content_hash FROM staging_artifacts WHERE id='STG-CANON-AI-02'").fetchone()
orig_title, orig_hash = row['title_en'], row['content_hash']
run('scripts/promote.py', 'rollback', '--db', DB, '--batch', 'T1')  # clear so a fresh plan/apply is meaningful
run('scripts/promote.py', 'plan', '--db', DB, '--batch', 'T2')
conn.execute("UPDATE staging_artifacts SET title_en='MUTATED' WHERE id='STG-CANON-AI-02'"); conn.commit()
r2 = run('scripts/promote.py', 'apply', '--db', DB, '--plan', os.path.join(PLANDIR, 'plan-T2.json'))
check("12. stale plan rejected", b'STALE' in r2.stdout and cnt(conn, 'security_artifacts') == 0)
conn.execute("UPDATE staging_artifacts SET title_en=?, content_hash=? WHERE id='STG-CANON-AI-02'", (orig_title, orig_hash))
conn.commit()

print("# rollback (13) + reverted state")
run('scripts/promote.py', 'plan', '--db', DB, '--batch', 'T3')
run('scripts/promote.py', 'apply', '--db', DB, '--plan', os.path.join(PLANDIR, 'plan-T3.json'))
applied3 = cnt(conn, 'security_artifacts')
run('scripts/promote.py', 'rollback', '--db', DB, '--batch', 'T3')
check("13. rollback reverts catalog", applied3 == 4 and cnt(conn, 'security_artifacts') == 0)
check("rollback removes child mappings", cnt(conn, 'framework_mappings') == 0)
check("rollback resets staging.promoted_artifact_id", cnt(conn, 'staging_artifacts', "WHERE promoted_artifact_id IS NOT NULL") == 0)
check("14b. raw still unchanged after rollback", cnt(conn, 'raw_artifacts') == raw0)
check("20. integrity ok after apply+rollback", conn.execute("PRAGMA integrity_check").fetchone()[0] == 'ok')

print("# all-or-nothing: child insert failure -> no partial write (16)")
run('scripts/promote.py', 'plan', '--db', DB, '--batch', 'T4')
pf = os.path.join(PLANDIR, 'plan-T4.json')
plan = json.load(io.open(pf, encoding='utf-8'))
plan['items'][0]['mappings'].append({'framework': 'X', 'version': '1', 'reference': 'r', 'mapping_strength': 'BOGUS', 'rationale': None})
io.open(pf, 'w', encoding='utf-8').write(json.dumps(plan, ensure_ascii=False))
before16 = cnt(conn, 'security_artifacts')
r4 = run('scripts/promote.py', 'apply', '--db', DB, '--plan', pf)
check("16. child-insert failure -> nothing written (all-or-nothing)",
      r4.returncode != 0 and cnt(conn, 'security_artifacts') == before16 == 0)

print("# audit log integrity (19)")
events = {r[0]: r[1] for r in conn.execute("SELECT event, COUNT(*) FROM promotion_audit_log GROUP BY event")}
check("19. audit log has PLAN/APPLY/ROLLBACK events", 'PLAN' in events and 'APPLY' in events and 'ROLLBACK' in events)

print("# final clean apply on the test DB")
run('scripts/promote.py', 'plan', '--db', DB, '--batch', 'FINAL')
run('scripts/promote.py', 'apply', '--db', DB, '--plan', os.path.join(PLANDIR, 'plan-FINAL.json'))
check("final apply promotes 4; integrity ok",
      cnt(conn, 'security_artifacts') == 4 and conn.execute("PRAGMA integrity_check").fetchone()[0] == 'ok')

print()
if fails:
    print("PROMOTION TESTS FAILED:", fails); sys.exit(1)
print("ALL PROMOTION TESTS PASSED.")
