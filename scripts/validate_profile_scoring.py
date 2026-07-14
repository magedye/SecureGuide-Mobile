# -*- coding: utf-8 -*-
"""Acceptance tests for profile-aware scoring and exception semantics."""
import glob
import io
import os
import sqlite3
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import scoring as S

fails = []


def check(name, condition):
    print(('PASS' if condition else 'FAIL'), '-', name)
    if not condition:
        fails.append(name)


def add_artifact(conn, aid, priority='PRI-MEDIUM'):
    weight = {'PRI-CRITICAL': 10, 'PRI-HIGH': 7, 'PRI-MEDIUM': 4, 'PRI-LOW': 1}[priority]
    conn.execute("""INSERT INTO security_artifacts(
        id,type,title_en,definition_short_en,primary_domain,sub_domain,
        abstraction_level,source,source_type,obligation_level,requirement_type,
        granularity_level,priority,priority_weight,publication_status,source_document,
        scoring_weight,risk_reduction,tier,effort_level)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
        aid, 'ART-REQ', aid, f'{aid} requirement', 'SD-01', 'SD-01.02',
        'ABS-POL', 'SRC-STD', 'STANDARD', 'OBL-MND', 'RQT-STD', 'GRN-DETAILED',
        priority, weight, 'APPROVED', 'profile-score-test', 10, 3, 'essential', 'low'))


conn = sqlite3.connect(':memory:')
conn.row_factory = sqlite3.Row
for path in sorted(glob.glob(os.path.join(ROOT, 'migrations', '*.sql'))):
    conn.executescript(io.open(path, encoding='utf-8').read())
conn.execute('PRAGMA foreign_keys=ON')

for aid, pri in (('A', 'PRI-CRITICAL'), ('B', 'PRI-HIGH'),
                 ('C', 'PRI-CRITICAL'), ('D', 'PRI-MEDIUM')):
    add_artifact(conn, aid, pri)
conn.execute("INSERT INTO enterprise_profiles(id,name) VALUES ('P1','Primary')")
conn.execute("INSERT INTO enterprise_profiles(id,name) VALUES ('P2','Other')")
conn.execute("""INSERT INTO profile_artifacts(
    id,profile_id,artifact_id,implementation_status,verification_status,effectiveness)
    VALUES ('PA-A','P1','A','STS-FULL','VER-PASS','EFF-HIGH')""")
conn.execute("""INSERT INTO profile_artifacts(
    id,profile_id,artifact_id,implementation_status,verification_status,effectiveness)
    VALUES ('PA-B','P1','B','STS-FULL','VER-PASS','EFF-HIGH')""")
conn.execute("""INSERT INTO profile_artifacts(
    id,profile_id,artifact_id,implementation_status,verification_status,effectiveness)
    VALUES ('PA-C','P1','C','STS-FULL','VER-NOT-VERIFIED','EFF-UNKNOWN')""")
conn.execute("""INSERT INTO profile_artifacts(
    id,profile_id,artifact_id,implementation_status,verification_status,effectiveness)
    VALUES ('PA-D','P1','D','STS-PARTIAL','VER-FAIL','EFF-LOW')""")
conn.execute("""INSERT INTO profile_artifacts(
    id,profile_id,artifact_id,implementation_status,verification_status,effectiveness)
    VALUES ('PA-P2','P2','B','STS-FULL','VER-PASS','EFF-HIGH')""")

conn.execute("""INSERT INTO profile_exceptions(
  id,profile_artifact_id,exception_status,justification,workflow_status,
  approved_by,approval_date,expiry_date)
  VALUES ('EX-B','PA-B','EXC-NOT-APPLICABLE','not in scope','APPROVED',
          'Owner','2026-01-01','2027-01-01')""")
conn.execute("""INSERT INTO profile_exceptions(
  id,profile_artifact_id,exception_status,justification,workflow_status,
  approved_by,approval_date,expiry_date,risk_accepted_by)
  VALUES ('EX-C','PA-C','EXC-RISK-ACCEPTED','legacy risk','APPROVED',
          'CISO','2026-01-01','2027-01-01','Risk Owner')""")
conn.execute("""INSERT INTO profile_exceptions(
  id,profile_artifact_id,exception_status,justification,workflow_status,
  approved_by,approval_date,expiry_date)
  VALUES ('EX-D','PA-D','EXC-DEFERRED','scheduled later','APPROVED',
          'CISO','2026-01-01','2027-01-01')""")
conn.commit()

controls = S.controls_from_catalog(conn, 'P1')
check('loader returns only active profile rows', {c['id'] for c in controls} == {'A', 'B', 'C', 'D'})
by_id = {c['id']: c for c in controls}
check('profile priority is loaded, not hard-coded', by_id['A']['priority'] == 'critical')
check('not-applicable is excluded from denominator', by_id['B']['excluded'])
check('accepted risk remains applicable', not by_id['C']['excluded'] and by_id['C']['exception_type'] == 'accepted_risk')
check('deferred remains applicable', not by_id['D']['excluded'] and by_id['D']['exception_type'] == 'deferred')

policy = S.load_policy(conn)
result = S.score(controls, {'view_tier': 'full', 'platforms': []}, policy)
check('applicable denominator excludes only N/A/unavailable', result['total_controls'] == 3)
check('accepted/deferred contribute zero implementation credit', abs(result['implementation_score_raw'] - (100/3)) < 1e-6)
check('accepted critical risk does not lift cap by default', result['remaining_critical_risk'] == 1)
check('verification remains a separate indicator', abs(result['verification_coverage'] - (100/3)) < 1e-6)
check('verification assessment coverage counts pass/fail', abs(result['verification_assessment_coverage'] - (200/3)) < 1e-6)
check('effectiveness-known is reported independently', abs(result['effectiveness_known'] - (200/3)) < 1e-6)
check('formula version is explicit', result['formula_version'] == 'profile-score-v1')

recs = {r['id']: r for r in S.recommend(controls, {'view_tier': 'full', 'platforms': []}, policy)}
check('recommendation explains accepted risk', 'exception:accepted_risk' in recs['C']['reason_codes'])
check('recommendation explains deferred state', 'exception:deferred' in recs['D']['reason_codes'])

try:
    S.controls_from_catalog(conn, None)
except ValueError:
    check('database scoring refuses missing active profile', True)
else:
    check('database scoring refuses missing active profile', False)

conn.close()
if fails:
    print('PROFILE SCORING VALIDATION FAILED:', fails)
    sys.exit(1)
print('ALL PROFILE SCORING CHECKS PASSED.')
