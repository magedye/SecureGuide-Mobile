# -*- coding: utf-8 -*-
"""Emit golden scoring fixtures with HAND-COMPUTED expected outputs (independent
of scoring.py) into tests/fixtures/golden/scoring/scenarios.json. Each scenario
exercises one mechanic of amani's engine; the expected numbers are derived by
explicit arithmetic in the comments, not by running the engine — so the gate
(validate_scoring.py) is a real cross-check, not the code testing itself."""
import io
import json
import os

OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'tests', 'fixtures', 'golden', 'scoring'))
FULL = {'view_tier': 'full', 'platforms': []}       # everything applicable


def c(id, w=0, rr=3, st='not_assessed', dom='D1', pri='high', eff='low',
      deps=None, tier='essential', plat=None, excluded=False, disabled=False, exc=None):
    return {'id': id, 'scoring_weight': w, 'risk_reduction': rr, 'user_status': st,
            'domain': dom, 'priority': pri, 'effort': eff, 'dependencies': deps or [],
            'tier': tier, 'platform_ids': plat or [], 'excluded': excluded,
            'disabled': disabled, 'exception_type': exc}


SCENARIOS = [
    {  # weighted average: wAch=4*1+6*0=4 /10 *100 = 40 ; cov 1/2 ; rr=4*1/6=66.6667
        'name': 'weighted_basic', 'settings': FULL,
        'controls': [c('A', w=4, rr=4, st='implemented'), c('B', w=6, rr=2, st='not_assessed')],
        'expect': {'overall': 40.0, 'band': 'At Risk', 'capped': False,
                   'assessment_coverage': 50.0, 'risk_reduction_pct': 66.66667,
                   'total_controls': 2, 'domain_scores': {'D1': 40.0}, 'critical_total': 0},
    },
    {  # open critical caps: raw=20/21*100=95.238 -> capped to 60
        'name': 'critical_cap_open', 'settings': FULL,
        'controls': [c('A', w=10, rr=5, st='implemented'), c('B', w=10, rr=5, st='implemented'),
                     c('C', w=1, rr=5, st='not_assessed', dom='D2', pri='critical')],
        'expect': {'overall': 60.0, 'band': 'At Risk', 'capped': True,
                   'assessment_coverage': 66.66667, 'risk_reduction_pct': 66.66667,
                   'domain_scores': {'D1': 100.0, 'D2': 0.0},
                   'critical_total': 1, 'critical_compliant': 0, 'remaining_critical_risk': 1},
    },
    {  # critical implemented -> no cap: raw=100
        'name': 'critical_cap_closed', 'settings': FULL,
        'controls': [c('A', w=10, st='implemented'), c('C', w=10, st='implemented', dom='D2', pri='critical')],
        'expect': {'overall': 100.0, 'band': 'Excellent', 'capped': False,
                   'critical_total': 1, 'critical_compliant': 1, 'remaining_critical_risk': 0},
    },
    {  # dependency clamp: X implemented(1) but dep DEP not compliant -> vEff=0.5
       #   wAch = 10*0 + 10*0.5 = 5 /20 *100 = 25
        'name': 'dependency_clamp', 'settings': FULL,
        'controls': [c('DEP', w=10, st='not_assessed'),
                     c('X', w=10, st='implemented', deps=['DEP'])],
        'expect': {'overall': 25.0, 'band': 'At Risk', 'capped': False, 'assessment_coverage': 50.0},
    },
    {  # dependency satisfied: DEP implemented -> X credited full -> 100
        'name': 'dependency_ready', 'settings': FULL,
        'controls': [c('DEP', w=10, st='implemented'),
                     c('X', w=10, st='implemented', deps=['DEP'])],
        'expect': {'overall': 100.0, 'band': 'Excellent'},
    },
    {  # band lower boundary 61 inclusive -> Fair
        'name': 'band_61', 'settings': FULL,
        'controls': [c('A', w=61, st='implemented'), c('B', w=39, st='not_assessed')],
        'expect': {'overall': 61.0, 'band': 'Fair'},
    },
    {  # 75 -> Strong
        'name': 'band_75', 'settings': FULL,
        'controls': [c('A', w=75, st='implemented'), c('B', w=25, st='not_assessed')],
        'expect': {'overall': 75.0, 'band': 'Strong'},
    },
    {  # 90 -> Excellent
        'name': 'band_90', 'settings': FULL,
        'controls': [c('A', w=90, st='implemented'), c('B', w=10, st='not_assessed')],
        'expect': {'overall': 90.0, 'band': 'Excellent'},
    },
    {  # 60.9 just below 61 -> At Risk
        'name': 'band_below_61', 'settings': FULL,
        'controls': [c('A', w=609, st='implemented'), c('B', w=391, st='not_assessed')],
        'expect': {'overall': 60.9, 'band': 'At Risk'},
    },
    {  # tier gating: very_advanced excluded from an 'advanced' view
        'name': 'tier_gating', 'settings': {'view_tier': 'advanced', 'platforms': []},
        'controls': [c('A', w=10, st='implemented', tier='essential'),
                     c('B', w=10, st='implemented', tier='very_advanced')],
        'expect': {'overall': 100.0, 'total_controls': 1},
    },
    {  # platform gating: windows-only control dropped for an android user
        'name': 'platform_gating', 'settings': {'view_tier': 'full', 'platforms': ['android']},
        'controls': [c('A', w=10, st='implemented', plat=['windows']),
                     c('B', w=10, st='not_assessed', plat=['all'])],
        'expect': {'overall': 0.0, 'total_controls': 1},
    },
    {  # explicitly excluded control leaves the applicable set
        'name': 'excluded_control', 'settings': FULL,
        'controls': [c('A', w=10, st='implemented', excluded=True), c('B', w=10, st='not_assessed')],
        'expect': {'overall': 0.0, 'total_controls': 1},
    },
    {  # no applicable controls -> empty score
        'name': 'empty_applicable', 'settings': {'view_tier': 'essential', 'platforms': []},
        'controls': [c('A', w=10, st='implemented', tier='very_advanced')],
        'expect': {'overall': 0.0, 'total_controls': 0, 'assessment_coverage': 0.0},
    },
    {  # recommendation ordering: severity -> dep-ready -> effort -> weight -> id
       # expected order: C1(crit), H3(high,ready,w8), H1(high,ready,w5), H2(high,not-ready), M1(med)
        'name': 'recommendations_order', 'settings': FULL,
        'controls': [
            c('IMP', w=1, st='implemented'),
            c('C1', w=1, pri='critical', eff='high', st='not_assessed'),
            c('H1', w=5, pri='high', eff='low', st='not_assessed'),
            c('H2', w=9, pri='high', eff='low', st='not_assessed', deps=['X_not_impl']),
            c('H3', w=8, pri='high', eff='low', st='not_assessed'),
            c('M1', w=10, pri='medium', eff='low', st='not_assessed'),
        ],
        'expect_recommendations': ['C1', 'H3', 'H1', 'H2', 'M1'],
    },
]


def main():
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, 'scenarios.json')
    io.open(path, 'w', encoding='utf-8').write(json.dumps(SCENARIOS, ensure_ascii=False, indent=2))
    print(f"wrote {len(SCENARIOS)} golden scoring scenarios -> {path}")


if __name__ == '__main__':
    main()
