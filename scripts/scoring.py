# -*- coding: utf-8 -*-
"""
scoring.py — headless, config-driven port of amani's v3 RiskScoringEngine +
RecommendationEngine (lib/v3/engine/*.dart). Reproduces the same four indicators
over the APPLICABLE set with the dependency clamp and critical cap, reading the
tunable numbers from the DB (scoring_policy / scoring_bands) instead of literals.

Pure core `score(controls, settings, policy)` mirrors the Dart 1:1; loaders adapt
either amani JSON or catalog.db into the normalized control shape.

CLI:
    python scripts/scoring.py --input amani_content_v4.json [--states states.json]
        [--view-tier full] [--platforms all] [--json] [--top 10]
    python scripts/scoring.py --db catalog.db --profile PRF-X [--json]
"""
import argparse
import io
import json
import os
import sqlite3
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# status -> fraction of risk achieved (ControlV3.statusValue)
IMPLEMENTED, PARTIAL, NOT_ASSESSED = 'implemented', 'partial', 'not_assessed'
TIER_RANK = {'essential': 0, 'advanced': 1, 'very_advanced': 2, 'full': 3}
SEV_RANK = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
EFF_RANK = {'low': 0, 'medium': 1, 'high': 2}
SHARED_PLATFORMS = {'web', 'router', 'iot', 'mobile', 'desktop', 'laptop'}

# policy fallback == ScoringPolicy.standard (used only if the DB has no rows)
DEFAULT_POLICY = {
    'critical_cap': 60, 'dependency_clamp_ceiling': 0.5, 'accepted_risk_lifts_cap': 0,
    'bands': [(0, 'At Risk'), (61, 'Fair'), (75, 'Strong'), (90, 'Excellent')],
}


def status_value(s):
    return 1.0 if s == IMPLEMENTED else (0.5 if s == PARTIAL else 0.0)


def band_for(score, bands):
    """bands: list of (min, label) ordered low->high (ScoringPolicy.bandFor)."""
    result = bands[0][1]
    for mn, label in bands:
        if score >= mn:
            result = label
    return result


def platform_applies(c, platforms):
    selected = platforms or ['android']
    pids = c.get('platform_ids') or []
    if not pids or 'all' in pids:
        return True
    if any(p in SHARED_PLATFORMS for p in pids):
        return True
    return any(p in selected for p in pids)


def is_included(c, settings):
    if c.get('disabled'):
        return False
    if not platform_applies(c, settings.get('platforms') or []):
        return False
    view = settings.get('view_tier', 'full')
    if view == 'full':
        return True
    return TIER_RANK.get(c.get('tier'), 0) <= TIER_RANK.get(view, 0)
    # (profile escalations are a no-op in amani's current engine)


def score(controls, settings, policy):
    """1:1 port of RiskScoringEngine.calculate. Returns a RiskScore dict."""
    ceiling = policy['dependency_clamp_ceiling']
    cap = policy['critical_cap']
    bands = policy['bands']

    applicable = [c for c in controls if is_included(c, settings) and not c.get('excluded')]
    if not applicable:
        return {'overall': 0.0, 'band': band_for(0.0, bands), 'capped': False,
                'assessment_coverage': 0.0, 'risk_reduction_pct': 0.0,
                'assessed_controls': 0, 'total_controls': 0, 'remaining_critical_risk': 0,
                'critical_total': 0, 'critical_compliant': 0, 'critical_accepted': 0,
                'domain_scores': {}}

    compliant_ids = {c['id'] for c in applicable if c.get('user_status') == IMPLEMENTED}

    def v_eff(c):
        v = status_value(c.get('user_status', NOT_ASSESSED))
        ready = all(d in compliant_ids for d in (c.get('dependencies') or []))
        if ready:
            return v
        return v if v < ceiling else ceiling

    w_total = w_ach = rr_total = rr_ach = 0.0
    assessed = crit_total = crit_compliant = crit_accepted = 0
    dom_w, dom_a = {}, {}

    for c in applicable:
        w = 1.0 if (c.get('scoring_weight') or 0) <= 0 else float(c['scoring_weight'])
        ve = v_eff(c)
        w_total += w
        w_ach += w * ve
        rr_raw = c.get('risk_reduction') or 0
        rr = 1.0 if rr_raw <= 0 else float(rr_raw)
        rr_total += rr
        rr_ach += rr * ve
        if c.get('user_status', NOT_ASSESSED) != NOT_ASSESSED:
            assessed += 1
        d = c.get('domain') or ''
        dom_w[d] = dom_w.get(d, 0.0) + w
        dom_a[d] = dom_a.get(d, 0.0) + w * ve
        if c.get('priority') == 'critical':
            crit_total += 1
            if c.get('user_status') == IMPLEMENTED:
                crit_compliant += 1
            elif c.get('exception_type') == 'accepted_risk':
                crit_accepted += 1

    raw = 0.0 if w_total == 0 else w_ach / w_total * 100
    crit_remaining = crit_total - crit_compliant
    capped = crit_remaining > 0
    overall = cap if (capped and raw > cap) else raw
    domain_scores = {d: (0.0 if dom_w[d] == 0 else dom_a[d] / dom_w[d] * 100) for d in dom_w}

    return {'overall': overall, 'band': band_for(overall, bands), 'capped': capped,
            'assessment_coverage': assessed / len(applicable) * 100,
            'risk_reduction_pct': 0.0 if rr_total == 0 else rr_ach / rr_total * 100,
            'assessed_controls': assessed, 'total_controls': len(applicable),
            'remaining_critical_risk': crit_remaining, 'critical_total': crit_total,
            'critical_compliant': crit_compliant, 'critical_accepted': crit_accepted,
            'domain_scores': domain_scores}


def recommend(controls, settings, policy=None):
    """1:1 port of RecommendationEngineV3.build — deterministic risk-first order."""
    compliant = {c['id'] for c in controls if c.get('user_status') == IMPLEMENTED}
    items = []
    for c in controls:
        if not is_included(c, settings):
            continue
        if c.get('excluded') or c.get('disabled'):
            continue
        if c.get('user_status') == IMPLEMENTED:
            continue
        ready = all(d in compliant for d in (c.get('dependencies') or []))
        items.append((c, c.get('priority', 'medium'), ready))
    items.sort(key=lambda t: (
        SEV_RANK.get(t[1], 2),
        0 if t[2] else 1,
        EFF_RANK.get(t[0].get('effort', 'medium'), 1),
        -float(t[0].get('scoring_weight') or 0),
        t[0]['id'],
    ))
    return [{'id': c['id'], 'priority': eff, 'dependency_ready': ready} for c, eff, ready in items]


# ------------------------------- loaders -----------------------------------
def load_policy(conn):
    """Read scoring_policy + scoring_bands from the DB; fall back to standard."""
    try:
        pol = conn.execute("SELECT critical_cap, dependency_clamp_ceiling, accepted_risk_lifts_cap "
                           "FROM scoring_policy WHERE id='default'").fetchone()
        bands = conn.execute("SELECT min_score, label_en FROM scoring_bands "
                            "WHERE policy_id='default' ORDER BY min_score").fetchall()
    except sqlite3.OperationalError:
        return dict(DEFAULT_POLICY)
    if not pol or not bands:
        return dict(DEFAULT_POLICY)
    return {'critical_cap': pol[0], 'dependency_clamp_ceiling': pol[1],
            'accepted_risk_lifts_cap': pol[2], 'bands': [(b[0], b[1]) for b in bands]}


def controls_from_amani(data, states=None):
    states = states or {}
    out = []
    for c in data.get('controls', []):
        out.append({
            'id': c['id'], 'domain': c.get('domain'), 'tier': c.get('tier', 'essential'),
            'priority': c.get('priority', 'medium'), 'effort': c.get('effort', 'medium'),
            'risk_reduction': c.get('risk_reduction', 3), 'scoring_weight': c.get('scoring_weight', 0),
            'dependencies': c.get('dependencies') or [], 'platform_ids': c.get('platform_ids') or [],
            'user_status': states.get(c['id'], NOT_ASSESSED), 'excluded': False, 'disabled': False,
        })
    return out


def controls_from_catalog(conn, profile=None, states=None):
    """Score promoted catalog controls. Uses the amani_domain tag when present so
    domain scores align with amani; falls back to primary_domain."""
    states = states or {}
    rows = conn.execute("SELECT id, primary_domain, tier, scoring_weight, risk_reduction, effort_level "
                        "FROM security_artifacts WHERE is_active=1").fetchall()
    dep = {}
    for r in conn.execute("SELECT source_id, target_id FROM artifact_relationships WHERE relation_type IN ('REL-DEP','DEP')"):
        dep.setdefault(r[0], []).append(r[1])
    tagdom = {}
    for r in conn.execute("SELECT artifact_id, tag_value FROM artifact_tags WHERE tag_value LIKE 'amani_domain:%'"):
        tagdom[r[0]] = r[1].split(':', 1)[1]
    out = []
    for r in rows:
        aid = r[0]
        out.append({
            'id': aid, 'domain': tagdom.get(aid, r[1]), 'tier': r[2] or 'essential',
            'priority': 'medium', 'effort': r[5] or 'medium',
            'risk_reduction': r[4] or 3, 'scoring_weight': r[3] or 0,
            'dependencies': dep.get(aid, []), 'platform_ids': [],
            'user_status': states.get(aid, NOT_ASSESSED), 'excluded': False, 'disabled': False,
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', help='amani_content_v4.json')
    ap.add_argument('--db', help='catalog.db')
    ap.add_argument('--profile')
    ap.add_argument('--states', help='JSON map {control_id: status}')
    ap.add_argument('--view-tier', default='full')
    ap.add_argument('--platforms', default='all')
    ap.add_argument('--top', type=int, default=10)
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args()

    states = json.load(io.open(args.states, encoding='utf-8')) if args.states else {}
    settings = {'view_tier': args.view_tier,
                'platforms': [] if args.platforms == 'all' else args.platforms.split(',')}

    if args.input:
        data = json.load(io.open(args.input, encoding='utf-8'))
        controls = controls_from_amani(data, states)
        policy = dict(DEFAULT_POLICY)
    elif args.db:
        conn = sqlite3.connect(args.db)
        policy = load_policy(conn)
        controls = controls_from_catalog(conn, args.profile, states)
    else:
        print("provide --input <amani.json> or --db <catalog.db>"); sys.exit(1)

    rs = score(controls, settings, policy)
    recs = recommend(controls, settings, policy)[:args.top]
    if args.json:
        print(json.dumps({'score': rs, 'recommendations': recs}, ensure_ascii=False, indent=2))
        return
    print(f"overall {rs['overall']:.2f}  band {rs['band']}  capped={rs['capped']}")
    print(f"coverage {rs['assessment_coverage']:.1f}%  riskReduction {rs['risk_reduction_pct']:.1f}%  "
          f"({rs['assessed_controls']}/{rs['total_controls']} assessed)")
    print(f"critical: total={rs['critical_total']} compliant={rs['critical_compliant']} "
          f"remaining={rs['remaining_critical_risk']}")
    print("top recommendations:")
    for r in recs:
        print(f"  {r['priority']:8} dep_ready={r['dependency_ready']}  {r['id']}")


if __name__ == '__main__':
    main()
