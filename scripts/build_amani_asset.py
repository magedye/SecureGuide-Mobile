# -*- coding: utf-8 -*-
"""
build_amani_asset.py — read-only generator that turns the promoted catalog
(security_artifacts + child tables + lineage) back into an amani v4 asset JSON.
Together with import_amani_content.py it forms an inverse pair over the reviewable
amani_domain_alias / amani_* tags: catalog -> asset -> catalog reproduces the
same control set and domains.

  * amani id      : recovered via lineage (staging.promoted_artifact_id ->
                    raw_artifacts.external_raw_id); falls back to the catalog id.
  * domain/sub    : from the amani_domain / amani_sub tags (authoritative);
                    else reversed through amani_domain_alias.
  * priority      : from the amani_priority tag (critical vs high are both
                    OBL-MND, so the tag preserves the original).
  * rich content  : actions/evidence + the enterprise{} block rebuilt from the
                    007 child tables; scoring scalars from security_artifacts.
  * scoring_policy: embedded from scoring_policy / scoring_bands.

Usage:
    python scripts/build_amani_asset.py --db catalog.db --out asset.json [--validate]
"""
import argparse
import io
import json
import os
import sqlite3
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def tagmap(conn, prefix):
    out = {}
    for r in conn.execute("SELECT artifact_id, tag_value FROM artifact_tags WHERE tag_value LIKE ?", (prefix + '%',)):
        out[r[0]] = r[1][len(prefix):]
    return out


def taglist(conn, prefix):
    out = {}
    for r in conn.execute("SELECT artifact_id, tag_value FROM artifact_tags WHERE tag_value LIKE ?", (prefix + '%',)):
        out.setdefault(r[0], []).append(r[1][len(prefix):])
    return out


def rows_by_artifact(conn, table, cols):
    out = {}
    for r in conn.execute(f"SELECT artifact_id,{cols} FROM {table}"):
        out.setdefault(r[0], []).append(r)
    return out


def build_enterprise(aid, objs, csf, purp, impl, mat, evid, vsteps, vnote, vnote_ar):
    """Rebuild the amani enterprise{} block from the 007 child tables. Returns
    None if the control carries no enterprise facets (a personal control)."""
    if not any([objs.get(aid), csf.get(aid), purp.get(aid), impl.get(aid), mat.get(aid), evid.get(aid), vsteps.get(aid)]):
        return None
    e = {}
    if objs.get(aid):
        e['security_objectives'] = {code: strength for (_, code, strength) in objs[aid]}
    if csf.get(aid):
        block = {'primary': [], 'supporting': []}
        for (_, code, strength) in csf[aid]:
            block.setdefault(strength, []).append(code)
        e['csf_functions'] = {k: v for k, v in block.items() if v}
    if purp.get(aid):
        e['control_purposes'] = {'primary': [code for (_, code) in purp[aid]]}
    if impl.get(aid):
        codes = [code for (_, code) in impl[aid]]
        e['implementation_types'] = {'primary': codes[0], 'supporting': codes[1:]} if codes else {}
    if mat.get(aid):
        e['maturity_requirements'] = {
            tier: {'objective_en': oe, 'objective_ar': oar}
            for (_, tier, oe, oar) in mat[aid]}
    vg = {}
    if vnote.get(aid):
        vg['methodology_en'] = vnote[aid]
    if vnote_ar.get(aid):
        vg['methodology_ar'] = vnote_ar[aid]
    if evid.get(aid):
        vg['evidence_types'] = [et for (_, et) in evid[aid]]
    if vsteps.get(aid):
        vg['testing_steps'] = [{'step_en': te, 'step_ar': ta}
                               for (_, seq, te, ta) in sorted(vsteps[aid], key=lambda x: x[1])]
    if vg:
        e['verification_guidance'] = vg
    return e


def build_asset(conn):
    # lineage: catalog id -> amani external id
    amani_id = {}
    for r in conn.execute("SELECT s.promoted_artifact_id, r.external_raw_id FROM staging_artifacts s "
                          "JOIN raw_artifacts r ON r.id = s.raw_artifact_id WHERE s.promoted_artifact_id IS NOT NULL"):
        amani_id[r[0]] = r[1]

    dom = tagmap(conn, 'amani_domain:')
    sub = tagmap(conn, 'amani_sub:')
    pri = tagmap(conn, 'amani_priority:')
    threat_ids = {}
    asset_ids = {}
    plat_ids = {}
    for r in conn.execute("SELECT artifact_id, tag_type, tag_value FROM artifact_tags"):
        aid, tt, tv = r
        if tt == 'Threat':
            threat_ids.setdefault(aid, []).append(tv)
        elif tt == 'Data':
            asset_ids.setdefault(aid, []).append(tv)
        elif tv.startswith('platform:'):
            plat_ids.setdefault(aid, []).append(tv[len('platform:'):])

    # amani domain alias for reverse fallback
    alias_rev = {}
    for r in conn.execute("SELECT amani_key, sdt_primary, sdt_sub FROM amani_domain_alias"):
        alias_rev[(r[1], r[2])] = r[0]

    actions = rows_by_artifact(conn, 'artifact_actions', 'kind,seq,text_en,text_ar')
    objs = rows_by_artifact(conn, 'artifact_security_objectives', 'objective_code,strength')
    csf = rows_by_artifact(conn, 'artifact_csf_functions', 'csf_code,strength')
    purp = rows_by_artifact(conn, 'artifact_control_purposes', 'purpose_code')
    impl = rows_by_artifact(conn, 'artifact_implementation_types', 'impl_type_code')
    mat = rows_by_artifact(conn, 'artifact_maturity_requirements', 'tier_code,objective_en,objective_ar')
    evid = rows_by_artifact(conn, 'artifact_verification_evidence_types', 'evidence_type')

    # source refs from framework_mappings.reference
    refs = {}
    for r in conn.execute("SELECT artifact_id, reference FROM framework_mappings WHERE reference IS NOT NULL"):
        refs.setdefault(r[0], []).append(r[1])

    controls = []
    for a in conn.execute("SELECT * FROM security_artifacts WHERE is_active=1 ORDER BY id"):
        aid = a['id']
        ext = amani_id.get(aid, aid)
        d = dom.get(aid)
        if not d:  # reverse via alias
            d = alias_rev.get((a['primary_domain'], a['sub_domain']))
        base_actions = [x for x in actions.get(aid, []) if x[0] == 'ACTION']
        vsteps = {aid: [x for x in actions.get(aid, []) if x[0] == 'VERIFICATION']} if actions.get(aid) else {}
        vnote = {aid: a['verification_method_note']} if a['verification_method_note'] else {}
        vnote_ar = {aid: a['verification_method_note_ar']} if a['verification_method_note_ar'] else {}
        ent = build_enterprise(aid, objs, csf, purp, impl, mat, evid, vsteps, vnote, vnote_ar)

        c = {
            'id': ext, 'domain': d, 'sub_domain': sub.get(aid, a['sub_domain']),
            'title_ar': a['title_ar'], 'title_en': a['title_en'],
            'description_ar': a['definition_short_ar'], 'description_en': a['definition_short_en'],
            'priority': pri.get(aid, 'medium'), 'tier': a['tier'] or 'essential',
            'effort': a['effort_level'] or 'medium', 'risk_reduction': a['risk_reduction'] or 3,
            'scoring_weight': a['scoring_weight'] or 0,
            'threat_ids': sorted(threat_ids.get(aid, [])), 'asset_ids': sorted(asset_ids.get(aid, [])),
            'platform_ids': sorted(plat_ids.get(aid, [])) or ['all'],
            'dependencies': [], 'source_refs': sorted(refs.get(aid, [])),
            'evidence_en': a['evidence_required'], 'evidence_ar': a['evidence_required_ar'],
        }
        if base_actions:
            c['actions_en'] = [x[2] for x in sorted(base_actions, key=lambda x: x[1])]
            c['actions_ar'] = [x[3] for x in sorted(base_actions, key=lambda x: x[1])]
        if ent:
            c['enterprise'] = ent
        controls.append(c)

    # taxonomy from lk_sdt_*
    taxonomy = {
        'domains': [{'code': r[0], 'name_en': r[1]} for r in conn.execute("SELECT code,name_en FROM lk_sdt_domain ORDER BY code")],
        'sub_domains': [{'code': r[0], 'name_en': r[1]} for r in conn.execute("SELECT code,name_en FROM lk_sdt_subdomain ORDER BY code")],
    }
    # scoring policy block
    pol = conn.execute("SELECT critical_cap, dependency_clamp_ceiling, accepted_risk_lifts_cap FROM scoring_policy WHERE id='default'").fetchone()
    bands = conn.execute("SELECT band_code, min_score, label_en, label_ar FROM scoring_bands WHERE policy_id='default' ORDER BY min_score").fetchall()
    scoring_policy = {
        'critical_cap': pol[0] if pol else 60,
        'dependency_clamp_ceiling': pol[1] if pol else 0.5,
        'accepted_risk_lifts_cap': bool(pol[2]) if pol else False,
        'bands': [{'code': b[0], 'min': b[1], 'label_en': b[2], 'label_ar': b[3]} for b in bands],
    }

    def aux(table, cols):
        try:
            return [dict(zip(cols.split(','), r)) for r in conn.execute(f"SELECT {cols} FROM {table}")]
        except sqlite3.OperationalError:
            return []

    return {
        'schema_version': 4, 'content_version': 'generated',
        'generated_from': 'SecureGuide catalog.db',
        'taxonomy': taxonomy,
        'controls': controls,
        'scoring_policy': scoring_policy,
        'glossary': aux('glossary_terms', 'id,term_en,term_ar,definition_en'),
        'incident_playbooks': aux('incident_playbooks', 'id,title_en'),
        'breach_checks': aux('breach_checks', 'id,title_en'),
        'security_tool_categories': aux('security_tool_categories', 'id,name_en'),
        'security_tools': aux('security_tools', 'id,name_en'),
        'profiles': aux('catalog_personas', 'id,name_en'),
    }


def validate_asset(conn, asset):
    problems = []
    alias = {r[0] for r in conn.execute("SELECT amani_key FROM amani_domain_alias")}
    for c in asset['controls']:
        if not c.get('domain'):
            problems.append(f"{c['id']}: no resolvable amani domain")
        elif c['domain'] not in alias:
            problems.append(f"{c['id']}: domain '{c['domain']}' not in amani_domain_alias")
        if not c.get('id'):
            problems.append("control without id")
    if not asset['scoring_policy']['bands']:
        problems.append("scoring_policy has no bands")
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', default=os.path.join(ROOT, 'catalog.db'))
    ap.add_argument('--out', default=os.path.join(ROOT, 'consolidation', 'amani_asset.json'))
    ap.add_argument('--validate', action='store_true')
    args = ap.parse_args()

    if not os.path.exists(args.db):
        print(f"DB not found: {args.db}"); sys.exit(1)
    conn = sqlite3.connect(args.db); conn.row_factory = sqlite3.Row
    asset = build_asset(conn)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    io.open(args.out, 'w', encoding='utf-8').write(json.dumps(asset, ensure_ascii=False, indent=2))
    print(f"wrote {len(asset['controls'])} controls -> {args.out}")

    if args.validate:
        problems = validate_asset(conn, asset)
        if problems:
            print(f"ASSET VALIDATION FAILED ({len(problems)}):")
            for p in problems[:20]:
                print("  -", p)
            sys.exit(1)
        print("asset validation OK: every control has a resolvable amani domain; scoring policy present.")


if __name__ == '__main__':
    main()
