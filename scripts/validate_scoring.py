# -*- coding: utf-8 -*-
"""Gate for Phase 4. Runs scoring.py's engine against the hand-computed golden
scenarios (critical-cap, dependency-clamp, band boundaries, coverage, domain
scores, recommendation ordering) and asserts an exact match within epsilon,
plus a few invariants over the real 706-control amani dataset."""
import io
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import scoring as S

GOLDEN = os.path.join(ROOT, 'tests', 'fixtures', 'golden', 'scoring', 'scenarios.json')
AMANI = os.environ.get('AMANI_JSON', r'd:/APP/amani/SecureGuide/archive/amani_content_v4.json')
EPS = 0.001
POLICY = dict(S.DEFAULT_POLICY)
fails = []


def check(n, cond):
    print(("PASS" if cond else "FAIL"), "-", n)
    if not cond:
        fails.append(n)


def close(a, b):
    return a is not None and b is not None and abs(float(a) - float(b)) <= EPS


if not os.path.exists(GOLDEN):
    from build_amani_scoring_golden import main as build
    build()
scenarios = json.load(io.open(GOLDEN, encoding='utf-8'))
check("golden fixtures present (14 scenarios)", len(scenarios) >= 14)

for sc in scenarios:
    name = sc['name']
    if 'expect' in sc:
        rs = S.score(sc['controls'], sc['settings'], POLICY)
        for k, exp in sc['expect'].items():
            if k == 'domain_scores':
                got = rs['domain_scores']
                ok = set(got) == set(exp) and all(close(got[d], exp[d]) for d in exp)
                check(f"{name}: domain_scores", ok)
            elif k == 'band':
                check(f"{name}: band={exp}", rs['band'] == exp)
            elif k == 'capped':
                check(f"{name}: capped={exp}", rs['capped'] == exp)
            elif isinstance(exp, bool) or isinstance(exp, int) and k in (
                    'total_controls', 'critical_total', 'critical_compliant', 'remaining_critical_risk',
                    'assessed_controls', 'critical_accepted'):
                check(f"{name}: {k}={exp}", rs[k] == exp)
            else:
                check(f"{name}: {k}={exp}", close(rs[k], exp))
    if 'expect_recommendations' in sc:
        recs = S.recommend(sc['controls'], sc['settings'], POLICY)
        got_ids = [r['id'] for r in recs]
        check(f"{name}: recommendation order {sc['expect_recommendations']}",
              got_ids == sc['expect_recommendations'])

# ---- invariants on the real amani dataset (parity sanity, not exact numbers) ----
if os.path.exists(AMANI):
    data = json.load(io.open(AMANI, encoding='utf-8'))
    ctrls = data['controls']
    ids = {c['id'] for c in ctrls}
    # a user who selected every platform present -> the whole catalog is applicable
    union = sorted({p for c in ctrls for p in (c.get('platform_ids') or []) if p != 'all'})
    settings = {'view_tier': 'full', 'platforms': union}

    all_ctrl = S.controls_from_amani(data, states=None)
    rs_none = S.score(all_ctrl, settings, POLICY)
    check("real: nothing implemented -> overall 0", close(rs_none['overall'], 0.0))
    check("real: whole catalog applicable with all platforms", rs_none['total_controls'] == len(ctrls))
    has_critical = any(c.get('priority') == 'critical' for c in ctrls)
    check("real: open criticals -> capped when criticals exist", rs_none['capped'] == has_critical)

    # all implemented, dependencies satisfiable (strip the 7 dangling deps that
    # point outside the dataset) -> a perfect 100.
    dangling = {(c['id'], d) for c in ctrls for d in (c.get('dependencies') or []) if d not in ids}
    clean = S.controls_from_amani(data, states={c['id']: 'implemented' for c in ctrls})
    for c in clean:
        c['dependencies'] = [d for d in c['dependencies'] if (c['id'], d) not in dangling]
    rs_full = S.score(clean, settings, POLICY)
    check("real: all implemented (deps resolved) -> overall 100", close(rs_full['overall'], 100.0))
    check("real: all implemented -> band Excellent", rs_full['band'] == 'Excellent')
    check("real: all implemented -> not capped", rs_full['capped'] is False)
    check("real: all implemented -> coverage 100%", close(rs_full['assessment_coverage'], 100.0))
    check("real: all implemented -> no recommendations left", len(S.recommend(clean, settings, POLICY)) == 0)

    # dangling deps DO clamp on the real data (faithful to amani): overall < 100.
    raw_impl = S.controls_from_amani(data, states={c['id']: 'implemented' for c in ctrls})
    rs_raw = S.score(raw_impl, settings, POLICY)
    check("real: unresolved dangling deps clamp overall below 100",
          rs_raw['overall'] < 100.0 and rs_raw['overall'] > 99.0)

    # deterministic ordering: recommend on all-not-assessed is stable & critical-first
    recs = S.recommend(all_ctrl, settings, POLICY)
    if recs:
        first_pri = [S.SEV_RANK.get(r['priority'], 2) for r in recs]
        check("real: recommendations sorted by severity band", first_pri == sorted(first_pri))
else:
    print("NOTE: amani json not found; skipped real-dataset invariants.")

print()
if fails:
    print("SCORING VALIDATION FAILED:", fails); sys.exit(1)
print("ALL SCORING CHECKS PASSED.")
