# -*- coding: utf-8 -*-
"""
import_amani_content.py — bring amani's 706 authored controls into SecureGuide
as raw_artifacts + staging_artifacts, WITHOUT bypassing the canonical model or
the single promotion write path.

  * raw_artifacts  : deterministic id `amani_v4::NNNN` + content_hash (lineage).
  * staging_artifacts : one candidate per control, classified into USACM/SDT via
    the reviewable `amani_domain_alias` table (FAIL-LOUD on any unmapped domain),
    with amani's rich content carried into the proposed_*_json / scoring columns
    that promote.py already normalizes. Everything lands as NEEDS_REVIEW / not
    ready_for_promotion — a human curates, then the standard path takes over:
        promote.py validate -> plan -> (review) -> apply

Idempotent: re-running rewrites the same deterministic rows (content_hash is
timestamp-free, so a promotion plan stays valid across reruns).

Usage:
    python scripts/import_amani_content.py --input <amani_content_v4.json> \
        --db catalog.db [--apply]          # omit --apply for a dry run
"""
import argparse
import hashlib
import io
import json
import os
import sqlite3
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MIG = os.path.join(ROOT, 'migrations')
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import _promote_common as C
import glob as _glob

MIGRATIONS = sorted(_glob.glob(os.path.join(MIG, '*.sql')))
CATALOG_ID = 'amani_v4'

# --- reviewable vocabulary bridges (amani term -> canonical), fail-soft to a
#     documented default; structural mismatches (domain keys) are fail-loud. ---
IMPL_ALIAS = {'process': 'operational'}                      # amani-only impl term
EVIDENCE_MAP = {'System Configuration': 'CONFIG', 'Config Dump': 'CONFIG',
                'AD Security Settings': 'CONFIG', 'GPO Report': 'REPORT',
                'Policy Document': 'DOCUMENT', 'Security Policy': 'DOCUMENT',
                'Audit Logs': 'LOG'}
PURPOSE_TO_FUN = {'preventive': 'FUN-PRE', 'deterrent': 'FUN-DRR', 'detective': 'FUN-DET',
                  'corrective': 'FUN-COR', 'containment': 'FUN-COR', 'recovery': 'FUN-REC',
                  'compensating': 'FUN-COM', 'directive': 'FUN-PRE', 'monitoring': 'FUN-DET',
                  'assurance': 'FUN-DET'}
IMPL_TO_NAT = {'technical': 'NAT-TEC', 'administrative': 'NAT-ORG', 'operational': 'NAT-ORG',
               'physical': 'NAT-PHY', 'human': 'NAT-HUM', 'legal_contractual': 'NAT-ORG',
               'architectural': 'NAT-TEC'}
PRIORITY_TO_OBL = {'critical': 'OBL-MND', 'high': 'OBL-MND', 'medium': 'OBL-REC', 'low': 'OBL-OPT'}


def ensure_schema(conn):
    if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='raw_artifacts'").fetchone():
        return False
    for p in MIGRATIONS:
        conn.executescript(io.open(p, encoding='utf-8').read())
    conn.commit()
    return True


def load_alias(conn):
    return {r['amani_key']: (r['sdt_primary'], r['sdt_sub'], r['needs_review'])
            for r in conn.execute("SELECT amani_key, sdt_primary, sdt_sub, needs_review FROM amani_domain_alias")}


def dedup(seq):
    out = []
    for x in seq:
        if x is not None and x not in out:
            out.append(x)
    return out


def flatten_strength(block):
    """{'primary':[...], 'supporting':[...]} -> [(code, strength)] (primary wins on dup)."""
    pairs, seen = [], set()
    for st in ('primary', 'supporting'):
        v = (block or {}).get(st)
        for code in ([v] if isinstance(v, str) else (v or [])):
            if code and code not in seen:
                pairs.append((code, st)); seen.add(code)
    return pairs


def build_enrichment(ctrl):
    """Map amani content -> the proposed_*_json / scoring columns promote.py reads.
    Returns (fields_dict, notes[]) where notes flag any lossy alias used."""
    notes = []
    e = ctrl.get('enterprise') or {}
    f = {}

    # scoring scalars (personal controls carry an explicit weight; enterprise don't).
    # coerce to float so the hashed value matches the REAL column on read-back
    # (else an int weight hashes as "6" but reloads as 6.0 -> stale-plan mismatch).
    sw = ctrl.get('scoring_weight')
    f['proposed_scoring_weight'] = float(sw) if sw is not None else None
    rr = ctrl.get('risk_reduction')
    f['proposed_risk_reduction'] = rr if isinstance(rr, int) and 2 <= rr <= 5 else None
    f['proposed_effort_level'] = ctrl.get('effort') if ctrl.get('effort') in ('low', 'medium', 'high') else None
    f['proposed_tier'] = ctrl.get('tier') if ctrl.get('tier') in C.TIER_CODES else None

    # actions (personal) + AR/EN content
    acts = []
    for i, (en, ar) in enumerate(zip(ctrl.get('actions_en') or [], ctrl.get('actions_ar') or [])):
        acts.append({'kind': 'ACTION', 'seq': i, 'text_en': en, 'text_ar': ar})
    f['proposed_actions_json'] = json.dumps(acts, ensure_ascii=False) if acts else None
    f['evidence_en'] = ctrl.get('evidence_en')
    f['evidence_ar'] = ctrl.get('evidence_ar')

    # security objectives (dict code->strength)
    objs = [{'objective_code': c, 'strength': s}
            for c, s in (e.get('security_objectives') or {}).items()
            if c in C.OBJ_CODES and s in C.OBJ_STRENGTH]
    f['proposed_security_objectives_json'] = json.dumps(objs, ensure_ascii=False) if objs else None

    # csf functions ({primary:[...],supporting:[...]})
    csf = [{'csf_code': c, 'strength': s} for c, s in flatten_strength(e.get('csf_functions'))
           if c in C.CSF_CODES and s in C.CSF_STRENGTH]
    f['proposed_csf_functions_json'] = json.dumps(csf, ensure_ascii=False) if csf else None

    # control purposes (flatten, dedup, validate)
    purposes = dedup(c for c, _ in flatten_strength(e.get('control_purposes')) if c in C.PURPOSE_CODES)
    f['proposed_control_purposes_json'] = json.dumps(purposes, ensure_ascii=False) if purposes else None

    # implementation types (flatten, alias 'process'->operational, dedup, validate)
    impl_raw = [c for c, _ in flatten_strength(e.get('implementation_types'))]
    impl = []
    for c in impl_raw:
        mapped = IMPL_ALIAS.get(c, c)
        if c in IMPL_ALIAS:
            notes.append(f"impl '{c}'->'{mapped}'")
        if mapped in C.IMPL_CODES:
            impl.append(mapped)
    impl = dedup(impl)
    f['proposed_implementation_types_json'] = json.dumps(impl, ensure_ascii=False) if impl else None

    # maturity requirements ({tier:{objective_en/ar}})
    mat = []
    for tier, v in (e.get('maturity_requirements') or {}).items():
        if tier in C.TIER_CODES:
            mat.append({'tier_code': tier, 'objective_en': v.get('objective_en'),
                        'objective_ar': v.get('objective_ar')})
    f['proposed_maturity_requirements_json'] = json.dumps(mat, ensure_ascii=False) if mat else None

    # verification guidance -> {evidence_types[], testing_steps[]}
    vg = e.get('verification_guidance') or {}
    ev, ev_other = [], False
    for label in (vg.get('evidence_types') or []):
        if label in C.EVIDENCE_TYPES:          # already canonical (e.g. a round-trip)
            code = label
        else:
            code = EVIDENCE_MAP.get(label, 'OTHER')
            if code == 'OTHER' and label not in EVIDENCE_MAP:
                ev_other = True
        ev.append(code)
    ev = dedup(ev)
    if ev_other:
        notes.append('unmapped evidence_type->OTHER')
    steps = [{'seq': i, 'text_en': s.get('step_en'), 'text_ar': s.get('step_ar')}
             for i, s in enumerate(vg.get('testing_steps') or []) if s.get('step_en')]
    verif = {}
    if ev:
        verif['evidence_types'] = ev
    if steps:
        verif['testing_steps'] = steps
    f['proposed_verification_json'] = json.dumps(verif, ensure_ascii=False) if verif else None
    f['verification_method_note'] = vg.get('methodology_en') or ((ctrl.get('verification') or {}).get('type'))
    f['verification_method_note_ar'] = vg.get('methodology_ar')

    # testability signal (automated step present -> AUTO)
    f['_auto'] = any(s.get('is_automated') for s in (vg.get('testing_steps') or []))
    return f, notes


def build_mappings(ctrl, raw_id, registry):
    refs = ctrl.get('source_refs') or []
    maps = []
    for ref in refs:
        name = registry.get(ref) or ref
        maps.append({'raw_id': raw_id, 'source_document': name, 'source_version': '4.1.0',
                     'source_section': ref, 'mapping_strength': 'INFORMATIVE',
                     'rationale': f"Imported from amani source_ref {ref}"})
    if not maps:
        maps.append({'raw_id': raw_id, 'source_document': 'amani SecureGuide v4', 'source_version': '4.1.0',
                     'source_section': ctrl.get('sub_domain'), 'mapping_strength': 'INFORMATIVE',
                     'rationale': 'Imported amani control without external source refs'})
    return maps


RAW_COLS =('id', 'source_catalog_id', 'external_raw_id', 'source_document', 'source_type',
            'source_section', 'source_version', 'source_url', 'title_draft', 'description_draft',
            'raw_text_en', 'raw_text_ar', 'original_heading', 'context_paragraph',
            'keywords_json', 'entities_mentioned_json', 'usacm_type_assigned',
            'sdt_domain_assigned', 'sdt_subdomain_assigned', 'requires_classification',
            'needs_human_review', 'is_ambiguous', 'ambiguity_reason', 'raw_json', 'source_file', 'content_hash')


def import_controls(conn, controls, alias, registry, source_file, apply, threat_alias, lk_threats, lk_platforms):
    stats = {'raw_ins': 0, 'raw_upd': 0, 'raw_same': 0, 'stg': 0, 'review': 0, 'notes': 0}
    for idx, ctrl in enumerate(controls):
        raw_id = f"{CATALOG_ID}::{idx:04d}"
        stg_id = f"STG-AMANI-{idx:04d}"
        pri, sub, dom_needs_review = alias[ctrl['domain']]

        enr, notes = build_enrichment(ctrl)
        maps = build_mappings(ctrl, raw_id, registry)
        is_personal = bool(ctrl.get('actions_en'))
        # SADP: no tags. Threats -> THR-* (via alias, idempotent for canonical codes),
        # platforms -> lk_platform, priority -> PRI-*, amani lineage -> provenance.
        threats = dedup(t if t in lk_threats else threat_alias[t] for t in (ctrl.get('threat_ids') or []))
        threats_json = json.dumps([{'threat_code': t} for t in threats], ensure_ascii=False) if threats else None
        platforms = dedup(p for p in (ctrl.get('platform_ids') or []) if p in lk_platforms)
        platforms_json = json.dumps(platforms, ensure_ascii=False) if platforms else None
        priority = 'PRI-' + (ctrl.get('priority') or 'medium').upper()
        provenance = {'amani_id': ctrl['id'], 'amani_domain': ctrl['domain'],
                      'amani_sub': ctrl.get('sub_domain'), 'assets': ctrl.get('asset_ids') or []}
        # derive USACM control fields
        e = ctrl.get('enterprise') or {}
        impl_primary = None
        ip = (e.get('implementation_types') or {}).get('primary')
        impl_primary = IMPL_ALIAS.get(ip, ip) if isinstance(ip, str) else None
        nature = IMPL_TO_NAT.get(impl_primary, 'NAT-HUM' if is_personal else 'NAT-TEC')
        purp_primary = ((e.get('control_purposes') or {}).get('primary') or [None])
        purp_primary = purp_primary[0] if isinstance(purp_primary, list) else purp_primary
        function = PURPOSE_TO_FUN.get(purp_primary, 'FUN-PRE')
        testability = 'TST-AUTO' if enr.pop('_auto', False) else 'TST-MAN'
        obligation = PRIORITY_TO_OBL.get(ctrl.get('priority'), 'OBL-REC')

        review = is_personal or bool(notes) or dom_needs_review == 1
        confidence = 0.62 if is_personal else (0.66 if (notes or dom_needs_review) else 0.72)
        ambiguity = '; '.join(notes) if notes else None

        # ----- raw_artifacts (idempotent by content_hash) -----
        raw_json = json.dumps(ctrl, ensure_ascii=False, sort_keys=True)
        chash = hashlib.sha256(raw_json.encode('utf-8')).hexdigest()
        raw_vals = {
            'id': raw_id, 'source_catalog_id': CATALOG_ID, 'external_raw_id': ctrl['id'],
            'source_document': 'amani SecureGuide v4', 'source_type': 'GUIDELINE',
            'source_section': ctrl.get('sub_domain'), 'source_version': '4.1.0', 'source_url': None,
            'title_draft': ctrl.get('title_en'), 'description_draft': ctrl.get('description_en'),
            'raw_text_en': ctrl.get('description_en'), 'raw_text_ar': ctrl.get('description_ar'),
            'original_heading': ctrl.get('title_en'), 'context_paragraph': None,
            'keywords_json': json.dumps((ctrl.get('threat_ids') or []) + (ctrl.get('asset_ids') or []), ensure_ascii=False),
            'entities_mentioned_json': json.dumps(ctrl.get('asset_ids') or [], ensure_ascii=False),
            'usacm_type_assigned': 'ART-CTR', 'sdt_domain_assigned': pri, 'sdt_subdomain_assigned': sub,
            'requires_classification': 0, 'needs_human_review': 1 if review else 0,
            'is_ambiguous': 1 if notes else 0, 'ambiguity_reason': ambiguity,
            'raw_json': raw_json, 'source_file': source_file, 'content_hash': chash,
        }
        if apply:
            ex = conn.execute("SELECT content_hash FROM raw_artifacts WHERE id=?", (raw_id,)).fetchone()
            if ex is None:
                conn.execute(f"INSERT INTO raw_artifacts ({','.join(RAW_COLS)}) VALUES ({','.join('?' for _ in RAW_COLS)})",
                             [raw_vals[c] for c in RAW_COLS]); stats['raw_ins'] += 1
            elif ex[0] != chash:
                conn.execute(f"UPDATE raw_artifacts SET {','.join(c+'=?' for c in RAW_COLS[1:])} WHERE id=?",
                             [raw_vals[c] for c in RAW_COLS[1:]] + [raw_id]); stats['raw_upd'] += 1
            else:
                stats['raw_same'] += 1

        # ----- staging_artifacts row -----
        stg = {
            'id': stg_id, 'batch_id': 'AMANI-IMPORT', 'raw_artifact_id': raw_id,
            'title_en': ctrl.get('title_en'), 'title_ar': ctrl.get('title_ar'),
            'definition_short_en': ctrl.get('description_en'), 'definition_short_ar': ctrl.get('description_ar'),
            'definition_full_en': ctrl.get('description_en'), 'definition_full_ar': ctrl.get('description_ar'),
            'objective_en': ctrl.get('description_en'), 'objective_ar': ctrl.get('description_ar'),
            'canonical_statement': None,
            'proposed_type': 'ART-CTR', 'proposed_abstraction_level': 'ABS-CTR',
            'proposed_primary_domain': pri, 'proposed_sub_domain': sub,
            'proposed_obligation_level': obligation,
            'proposed_control_nature': nature, 'proposed_control_function': function,
            'proposed_testability': testability,
            'proposed_requirement_type': None, 'proposed_asset_type': None, 'proposed_asset_criticality': None,
            'classification_confidence': confidence,
            'classification_rationale': f"Imported from amani domain '{ctrl['domain']}' -> {pri}/{sub}; "
                                        f"type ART-CTR ({nature}/{function}/{testability}).",
            'rejected_alternatives': None,
            'requires_human_review': 1 if review else 0,
            'proposed_tags_json': None,  # SADP §2.4: tags retired
            'proposed_threats_json': threats_json, 'proposed_platforms_json': platforms_json,
            'proposed_priority': priority,
            'proposed_amani_provenance_json': json.dumps(provenance, ensure_ascii=False),
            'proposed_mappings_json': json.dumps(maps, ensure_ascii=False),
            'proposed_relationships_json': None,
            'canonical_group_id': None, 'merge_action': None,
            'curation_status': 'NEEDS_REVIEW' if review else 'CLASSIFIED',
            'quality_score': None, 'reviewer': None,
            'review_notes': ('; '.join(notes) if notes else None),
            'final_review_status': None, 'ready_for_promotion': 0, 'promotion_blockers': None,
            'evidence_en': enr.get('evidence_en'), 'evidence_ar': enr.get('evidence_ar'),
            'verification_method_note': enr.get('verification_method_note'),
            'verification_method_note_ar': enr.get('verification_method_note_ar'),
            'proposed_scoring_weight': enr.get('proposed_scoring_weight'),
            'proposed_risk_reduction': enr.get('proposed_risk_reduction'),
            'proposed_effort_level': enr.get('proposed_effort_level'),
            'proposed_tier': enr.get('proposed_tier'),
            'proposed_actions_json': enr.get('proposed_actions_json'),
            'proposed_variants_json': None,
            'proposed_security_objectives_json': enr.get('proposed_security_objectives_json'),
            'proposed_csf_functions_json': enr.get('proposed_csf_functions_json'),
            'proposed_control_purposes_json': enr.get('proposed_control_purposes_json'),
            'proposed_implementation_types_json': enr.get('proposed_implementation_types_json'),
            'proposed_maturity_requirements_json': enr.get('proposed_maturity_requirements_json'),
            'proposed_verification_json': enr.get('proposed_verification_json'),
        }
        stg['content_hash'] = C.content_hash(stg)
        if apply:
            stg_cols = [k for k in stg]
            conn.execute(
                f"INSERT OR REPLACE INTO staging_artifacts ({','.join(stg_cols)}, created_at, updated_at) "
                f"VALUES ({','.join('?' for _ in stg_cols)}, datetime('now'), datetime('now'))",
                [stg[c] for c in stg_cols])
        stats['stg'] += 1
        if review:
            stats['review'] += 1
        if notes:
            stats['notes'] += 1
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', required=True)
    ap.add_argument('--db', default=os.path.join(ROOT, 'catalog.db'))
    ap.add_argument('--apply', action='store_true', help='write rows (default: dry run)')
    args = ap.parse_args()

    data = json.load(io.open(args.input, encoding='utf-8'))
    controls = data.get('controls') or []
    registry = {s.get('code'): (s.get('name') or s.get('code')) for s in (data.get('source_registry') or [])}
    source_file = os.path.basename(args.input)

    if not os.path.exists(args.db):
        print(f"DB not found: {args.db} (run ingest_raw.py first, or point --db at a migrated DB)."); sys.exit(1)
    conn = sqlite3.connect(args.db); conn.row_factory = sqlite3.Row
    conn.isolation_level = None  # explicit BEGIN/COMMIT — no implicit transactions
    conn.execute("PRAGMA foreign_keys=ON")
    created = ensure_schema(conn)
    alias = load_alias(conn)
    if not alias:
        print("amani_domain_alias is empty — apply migration 009 (build_reference_ext) first."); sys.exit(1)

    # FAIL-LOUD: every control domain must be mapped; no silent pass.
    unmapped = sorted({c['domain'] for c in controls if c.get('domain') not in alias})
    if unmapped:
        print(f"IMPORT ABORTED: {len(unmapped)} unmapped amani domain key(s): {unmapped}")
        print("Add them to amani_domain_alias (migration 009) before importing."); sys.exit(1)

    # SADP threat/platform vocabularies (fail-loud on unmapped threat term)
    threat_alias = {r['amani_key']: r['threat_code'] for r in conn.execute("SELECT amani_key, threat_code FROM amani_threat_alias")}
    lk_threats = {r[0] for r in conn.execute("SELECT code FROM lk_threat")}
    lk_platforms = {r[0] for r in conn.execute("SELECT code FROM lk_platform")}
    if not lk_threats:
        print("lk_threat is empty — apply migrations 012/013 first."); sys.exit(1)
    unmapped_thr = sorted({t for c in controls for t in (c.get('threat_ids') or [])
                           if t not in lk_threats and t not in threat_alias})
    if unmapped_thr:
        print(f"IMPORT ABORTED: {len(unmapped_thr)} unmapped amani threat term(s): {unmapped_thr}")
        print("Add them to amani_threat_alias (migration 013) before importing."); sys.exit(1)
    unmapped_plat = sorted({p for c in controls for p in (c.get('platform_ids') or []) if p not in lk_platforms})
    if unmapped_plat:
        print(f"IMPORT ABORTED: {len(unmapped_plat)} platform(s) not in lk_platform: {unmapped_plat}")
        print("Add them to lk_platform (migration 015) before importing."); sys.exit(1)

    if args.apply:
        conn.execute("INSERT OR IGNORE INTO source_catalogs (id, name, source_type, version) VALUES (?,?,?,?)",
                     (CATALOG_ID, 'amani SecureGuide v4', 'GUIDELINE', '4.1.0'))
        conn.execute("INSERT OR IGNORE INTO curation_batches (id, source_catalog_id, name, status, item_count, notes) "
                     "VALUES (?,?,?,?,?,?)",
                     ('AMANI-IMPORT', CATALOG_ID, 'amani v4 content import', 'PROCESSING', len(controls),
                      'imported by import_amani_content.py'))
        conn.execute("BEGIN")
    stats = import_controls(conn, controls, alias, registry, source_file, args.apply,
                            threat_alias, lk_threats, lk_platforms)
    if args.apply:
        conn.execute("COMMIT"); conn.commit()

    print("=" * 64)
    print(f"AMANI IMPORT {'(APPLIED)' if args.apply else '(DRY RUN — no writes)'}  db={args.db}"
          + ('  [schema created]' if created else ''))
    print("=" * 64)
    print(f"controls read        : {len(controls)}")
    print(f"domains all mapped   : YES ({len(alias)} aliases)")
    print(f"raw ins/upd/unchanged: {stats['raw_ins']} / {stats['raw_upd']} / {stats['raw_same']}")
    print(f"staging rows         : {stats['stg']}")
    print(f"flagged for review   : {stats['review']}  (personal + aliased + alias-needs-review)")
    print(f"controls w/ alias note: {stats['notes']}")
    if not args.apply:
        print("\nDry run only. Re-run with --apply to write.")
    else:
        print("\nNext: python scripts/promote.py validate --db " + os.path.basename(args.db))


if __name__ == '__main__':
    main()
