# -*- coding: utf-8 -*-
"""Tests that rich content-enrichment collections flow through promote.py:
authored actions/objectives/csf/purposes/impl-types/maturity/verification/variants
+ scoring/AR scalars are normalized into the new child tables + columns on apply,
removed on rollback, and that a bad enrichment value aborts the whole batch
(all-or-nothing)."""
import io
import json
import os
import subprocess
import sqlite3
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB = os.path.join(ROOT, 'rich_test.db')
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


def rehash(conn, sid):
    r = conn.execute("SELECT * FROM staging_artifacts WHERE id=?", (sid,)).fetchone()
    conn.execute("UPDATE staging_artifacts SET content_hash=? WHERE id=?", (C.content_hash(r), sid))


if os.path.exists(DB):
    os.remove(DB)
run('scripts/ingest_raw.py', '--db', DB)
run('scripts/pilot_asset_inventory.py', '--db', DB, '--apply')
run('scripts/final_review.py', '--db', DB)
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA foreign_keys=ON")

# inject rich content into STG-CANON-AI-02 (final id SG-CTR-AI-02)
SID, FID = 'STG-CANON-AI-02', 'SG-CTR-AI-02'
conn.execute("""UPDATE staging_artifacts SET
    title_ar=?, definition_short_ar=?, evidence_en=?, evidence_ar=?,
    verification_method_note=?, verification_method_note_ar=?,
    proposed_scoring_weight=?, proposed_risk_reduction=?, proposed_effort_level=?, proposed_tier=?,
    proposed_actions_json=?, proposed_variants_json=?, proposed_security_objectives_json=?,
    proposed_csf_functions_json=?, proposed_control_purposes_json=?, proposed_implementation_types_json=?,
    proposed_maturity_requirements_json=?, proposed_verification_json=?,
    proposed_threats_json=?, proposed_platforms_json=?, proposed_priority=? WHERE id=?""", (
    'صيانة حداثة جرد الأصول', 'يحافظ على حداثة الجرد', 'inventory register', 'سجل الجرد',
    'review register', 'مراجعة السجل',
    6.9, 5, 'low', 'essential',
    json.dumps([{'kind': 'ACTION', 'seq': 0, 'text_en': 'Open inventory tool', 'text_ar': 'افتح الأداة'},
                {'kind': 'ACTION', 'seq': 1, 'text_en': 'Reconcile assets', 'text_ar': 'طابق الأصول'}]),
    json.dumps([{'platform': 'windows', 'title_en': 'Windows inventory', 'sort_order': 0}]),
    json.dumps([{'objective_code': 'integrity', 'strength': 'primary'}, {'objective_code': 'availability', 'strength': 'supporting'}]),
    json.dumps([{'csf_code': 'identify', 'strength': 'primary'}]),
    json.dumps(['detective', 'directive']),
    json.dumps(['administrative', 'technical']),
    json.dumps([{'tier_code': 'advanced', 'objective_en': 'Full inventory', 'scope_en': 'all assets'}]),
    json.dumps({'evidence_types': ['LOG', 'REPORT'], 'testing_steps': [{'seq': 0, 'text_en': 'Sample register', 'text_ar': 'عيّنة'}]}),
    json.dumps([{'threat_code': 'THR-UNAUTHORIZED-ACCESS'}, {'threat_code': 'THR-MISCONFIG'}]),
    json.dumps(['windows', 'linux']),
    'PRI-HIGH',
    SID))
rehash(conn, SID)
conn.commit()

run('scripts/promote.py', 'plan', '--db', DB, '--batch', 'RICH1')
r1 = run('scripts/promote.py', 'apply', '--db', DB, '--plan', os.path.join(PLANDIR, 'plan-RICH1.json'))


def cnt(t, w=''):
    return conn.execute(f"SELECT COUNT(*) FROM {t} {w}").fetchone()[0]


print("# normalization on apply")
check("artifact promoted", cnt('security_artifacts', f"WHERE id='{FID}'") == 1)
check("actions (2 ACTION + 1 VERIFICATION)", cnt('artifact_actions', f"WHERE artifact_id='{FID}'") == 3)
check("verification step kind", cnt('artifact_actions', f"WHERE artifact_id='{FID}' AND kind='VERIFICATION'") == 1)
check("variants (1)", cnt('artifact_variants', f"WHERE artifact_id='{FID}'") == 1)
check("security objectives (2)", cnt('artifact_security_objectives', f"WHERE artifact_id='{FID}'") == 2)
check("csf functions (1)", cnt('artifact_csf_functions', f"WHERE artifact_id='{FID}'") == 1)
check("control purposes (2)", cnt('artifact_control_purposes', f"WHERE artifact_id='{FID}'") == 2)
check("impl types (2)", cnt('artifact_implementation_types', f"WHERE artifact_id='{FID}'") == 2)
check("maturity reqs (1)", cnt('artifact_maturity_requirements', f"WHERE artifact_id='{FID}'") == 1)
check("evidence types (2)", cnt('artifact_verification_evidence_types', f"WHERE artifact_id='{FID}'") == 2)
check("threats normalized (2)", cnt('artifact_threats', f"WHERE artifact_id='{FID}'") == 2)
check("platforms normalized (2)", cnt('artifact_platforms', f"WHERE artifact_id='{FID}'") == 2)
check("baseline priority preserved (PRI-HIGH)", conn.execute("SELECT priority FROM security_artifacts WHERE id=?", (FID,)).fetchone()[0] == 'PRI-HIGH')
check("no tags written (SADP §2.4)", cnt('artifact_tags') == 0)
row = conn.execute("SELECT scoring_weight, tier, effort_level, risk_reduction, title_ar, evidence_required, evidence_required_ar FROM security_artifacts WHERE id=?", (FID,)).fetchone()
check("scoring/tier scalars on catalog", row['scoring_weight'] == 6.9 and row['tier'] == 'essential' and row['effort_level'] == 'low' and row['risk_reduction'] == 5)
check("AR + evidence content on catalog", row['title_ar'] == 'صيانة حداثة جرد الأصول' and row['evidence_required'] == 'inventory register' and row['evidence_required_ar'] == 'سجل الجرد')
check("integrity ok after apply", conn.execute("PRAGMA integrity_check").fetchone()[0] == 'ok')

print("# rollback removes rich children")
run('scripts/promote.py', 'rollback', '--db', DB, '--batch', 'RICH1')
removed = all(cnt(t, f"WHERE artifact_id='{FID}'") == 0 for t in (
    'artifact_actions', 'artifact_variants', 'artifact_security_objectives', 'artifact_csf_functions',
    'artifact_control_purposes', 'artifact_implementation_types', 'artifact_maturity_requirements',
    'artifact_verification_evidence_types', 'artifact_threats', 'artifact_platforms'))
check("all rich children removed on rollback", removed and cnt('security_artifacts', f"WHERE id='{FID}'") == 0)
check("integrity ok after rollback", conn.execute("PRAGMA integrity_check").fetchone()[0] == 'ok')

print("# fail-loud: bad enrichment code is BLOCKED (excluded, never silently promoted)")
# inject a bad objective strength on another ready item; it must be excluded from
# the plan with a blocker, never promoted with the bad content silently dropped.
SID2, FID2 = 'STG-CANON-AI-05', 'SG-CTR-AI-05'
conn.execute("UPDATE staging_artifacts SET proposed_security_objectives_json=? WHERE id=?",
             (json.dumps([{'objective_code': 'integrity', 'strength': 'STRONG'}]), SID2))  # STRONG invalid
rehash(conn, SID2)
conn.commit()
run('scripts/promote.py', 'plan', '--db', DB, '--batch', 'RICH2')
plan2 = json.load(io.open(os.path.join(PLANDIR, 'plan-RICH2.json'), encoding='utf-8'))
excl = {e['staging_id']: e for e in plan2['excluded']}
check("bad item excluded from plan with a blocker",
      SID2 in excl and any('strength' in str(x) for x in excl[SID2].get('blockers', [])))
check("bad item not in plan items", all(i['staging_id'] != SID2 for i in plan2['items']))
r2 = run('scripts/promote.py', 'apply', '--db', DB, '--plan', os.path.join(PLANDIR, 'plan-RICH2.json'))
check("apply succeeds for the clean items", r2.returncode == 0)
check("bad item NOT promoted", cnt('security_artifacts', f"WHERE id='{FID2}'") == 0)
check("no partial objective row for bad item", cnt('artifact_security_objectives', f"WHERE artifact_id='{FID2}'") == 0)
check("integrity ok after apply", conn.execute("PRAGMA integrity_check").fetchone()[0] == 'ok')

print()
if fails:
    print("RICH PROMOTION TESTS FAILED:", fails)
    sys.exit(1)
print("ALL RICH-CONTENT PROMOTION TESTS PASSED.")
