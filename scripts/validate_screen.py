# -*- coding: utf-8 -*-
"""Tests for the pre-screening stage: determinism/idempotency, known-case
verdicts, and that screening never emits a merge decision or canonical."""
import io
import json
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB = os.path.join(ROOT, 'pilot.db')
OUT = os.path.join(ROOT, 'consolidation', 'screening')
PY = sys.executable
NP = 'nist_sp_800_53_rev_5_security_and_privacy_controls_for_information_systems_and_organizations'
fails = []


def run(target):
    subprocess.run([PY, 'scripts/screen.py', '--target', target, '--db', DB, '--out', OUT],
                   cwd=ROOT, capture_output=True)
    return json.load(io.open(os.path.join(OUT, f"{target}.json"), encoding='utf-8'))


def check(name, cond):
    print(("PASS" if cond else "FAIL"), "-", name)
    if not cond:
        fails.append(name)


def verdict_of(data, raw_id):
    r = next((x for x in data['results'] if x['raw_id'] == raw_id), None)
    return r['verdict'] if r else None


# idempotency
a1 = run('asset_inventory')
a2 = run('asset_inventory')
check("screening idempotent (identical output)", a1['results'] == a2['results'])

# known cases — asset_inventory
check("asset: CIS 5.1 account inventory -> EXCLUDE",
      verdict_of(a1, 'cis_controls_v8::0007') == 'EXCLUDE')
check("asset: CIS 1.1 asset inventory -> relevant/review",
      verdict_of(a1, 'cis_controls_v8::0000') in ('LIKELY_RELEVANT', 'POSSIBLY_RELEVANT', 'NEEDS_AGENT_REVIEW'))
check("asset: CIS 15.1 service-provider inventory -> EXCLUDE",
      verdict_of(a1, 'cis_controls_v8::0025') == 'EXCLUDE')

# known cases — privileged_access
p = run('privileged_access')
likely = [r for r in p['results'] if r['verdict'] == 'LIKELY_RELEVANT']
check("pam: >=5 LIKELY_RELEVANT found", len(likely) >= 5)
check("pam: at least one least_privilege concept", any('least_privilege' in r['matched_concepts'] for r in likely))
check("pam: most items EXCLUDE (noise filtered)",
      sum(1 for r in p['results'] if r['verdict'] == 'EXCLUDE') > 0.9 * p['total_scanned'])

# screening never decides merges or canonicals
sample = a1['results'][0]
check("screening emits no 'decision' field", 'decision' not in sample)
check("screening emits no 'canonical' field", 'canonical' not in sample and 'canonical_artifact' not in sample)
check("screening item has required fields",
      all(k in sample for k in ('verdict', 'screening_rationale', 'matched_concepts',
                                'exclusion_reason', 'screening_confidence')))

print()
if fails:
    print("SCREENING TESTS FAILED:", fails)
    sys.exit(1)
print("ALL SCREENING TESTS PASSED.")
