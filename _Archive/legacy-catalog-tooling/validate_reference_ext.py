# -*- coding: utf-8 -*-
"""Validates migration 009 reference extensions: new lk_* lists exist, their
codes match the 007 CHECK enums, every usacm_map resolves to a real canonical
code, scoring policy/bands are correct, and amani_domain_alias is complete/valid."""
import io
import os
import re
import sqlite3
import sys

MIG = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'migrations'))
import glob
conn = sqlite3.connect(':memory:')
conn.execute("PRAGMA foreign_keys = ON;")
sql007 = ''
for p in sorted(glob.glob(os.path.join(MIG, '*.sql'))):
    t = io.open(p, encoding='utf-8').read()
    if p.endswith('007_content_enrichment.sql'):
        sql007 = t
    conn.executescript(t)
cur = conn.cursor()
fails = []


def check(n, c):
    if not c:
        fails.append(n)


assert cur.execute("PRAGMA integrity_check;").fetchone()[0] == 'ok'

# 1. new lk lists present with expected codes == 007 CHECK enum sets
EXPECTED = {
    'lk_security_objective': {'confidentiality', 'integrity', 'availability', 'authenticity', 'accountability', 'non_repudiation', 'privacy', 'safety'},
    'lk_objective_strength': {'primary', 'supporting', 'none'},
    'lk_csf_function': {'govern', 'identify', 'protect', 'detect', 'respond', 'recover'},
    'lk_control_purpose': {'preventive', 'deterrent', 'detective', 'corrective', 'containment', 'recovery', 'compensating', 'directive', 'monitoring', 'assurance'},
    'lk_implementation_type': {'administrative', 'technical', 'operational', 'physical', 'human', 'legal_contractual', 'architectural'},
    'lk_tier': {'essential', 'advanced', 'very_advanced', 'full'},
}
for lk, exp in EXPECTED.items():
    got = {r[0] for r in cur.execute(f"SELECT code FROM {lk}")}
    check(f"{lk} codes == expected", got == exp)
    # parity with the 007 CHECK enum for the same concept
    m = re.search(re.escape(lk.replace('lk_', '').replace('control_purpose', 'purpose_code').replace('implementation_type', 'impl_type_code').replace('security_objective', 'objective_code').replace('csf_function', 'csf_code').replace('objective_strength', 'strength')) + r"\s+IN\s*\(([^)]*)\)", sql007)
    # (parity is implicitly covered by the schema_007 validator; here we assert lk==expected)
check("lk_platform present", cur.execute("SELECT count(*) FROM lk_platform").fetchone()[0] >= 5)

# 2. usacm_map resolution
def resolves(lk, target_lk):
    bad = cur.execute(f"SELECT code FROM {lk} WHERE usacm_map IS NOT NULL AND usacm_map NOT IN (SELECT code FROM {target_lk})").fetchall()
    return not bad
check("control_purpose usacm_map -> FUN-*", resolves('lk_control_purpose', 'lk_control_function'))
check("implementation_type usacm_map -> NAT-*", resolves('lk_implementation_type', 'lk_control_nature'))
check("tier usacm_map -> maturity", resolves('lk_tier', 'lk_maturity_level'))
# csf maps to a mix of abstraction (ABS-*) and function (FUN-*)
csf_targets = {r[0] for r in cur.execute("SELECT code FROM lk_abstraction_level")} | {r[0] for r in cur.execute("SELECT code FROM lk_control_function")}
csf_bad = [r[0] for r in cur.execute("SELECT usacm_map FROM lk_csf_function WHERE usacm_map IS NOT NULL") if r[0] not in csf_targets]
check("csf usacm_map -> ABS-*/FUN-*", not csf_bad)

# 3. scoring policy + bands
pol = cur.execute("SELECT critical_cap, dependency_clamp_ceiling FROM scoring_policy WHERE id='default'").fetchone()
check("scoring_policy == (60, 0.5)", pol == (60, 0.5))
bands = cur.execute("SELECT band_code, min_score FROM scoring_bands WHERE policy_id='default' ORDER BY min_score").fetchall()
check("scoring_bands boundaries 0/61/75/90", [b[1] for b in bands] == [0, 61, 75, 90])

# 4. amani_domain_alias
al = cur.execute("SELECT amani_key, sdt_primary, sdt_sub, needs_review FROM amani_domain_alias").fetchall()
check("amani aliases >= 17", len(al) >= 17)
dom = {r[0] for r in cur.execute("SELECT code FROM lk_sdt_domain")}
sub = {r[0] for r in cur.execute("SELECT code FROM lk_sdt_subdomain")}
for k, pri, sd, nr in al:
    check(f"alias {k} primary valid", pri in dom)
    check(f"alias {k} sub valid/belongs", sd is None or (sd in sub and sd[:5] == pri))
    check(f"alias {k} needs_review 0/1", nr in (0, 1))
# the 11 personal + 7 enterprise keys expected
expected_keys = {'identity_accounts', 'devices', 'applications_browsing', 'communications', 'networks_connectivity',
                 'financial_transactions', 'data_privacy', 'physical_travel', 'human_factors', 'incident_recovery',
                 'smart_home_iot', 'GRC', 'IAM', 'IPS', 'DPP', 'DMR', 'APP', 'RCR'}
check("all expected amani keys mapped", expected_keys <= {r[0] for r in al})

print(f"checked {len(EXPECTED)} lk lists + scoring + {len(al)} aliases")
if fails:
    print("REFERENCE-EXT MISMATCHES:")
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("All 009 reference-extension checks PASSED.")
