# -*- coding: utf-8 -*-
"""Shared helpers for the promotion workflow (final_review + promote)."""
import hashlib
import json
import re

# Fields per USACM type that MUST be present before promotion.
REQUIRED_BY_TYPE = {
    'ART-REQ': ['proposed_requirement_type'],
    'ART-CTR': ['proposed_control_nature', 'proposed_control_function', 'proposed_testability'],
    'ART-CTE': ['proposed_control_nature', 'proposed_control_function', 'proposed_testability'],
    'ART-AST': ['proposed_asset_type', 'proposed_asset_criticality'],
}

# Enrichment code sets — mirror the 007 CHECK enums so the promotion gate can
# reject bad authored collections fail-loud (never silently drop via OR IGNORE).
OBJ_CODES = {'confidentiality', 'integrity', 'availability', 'authenticity',
             'accountability', 'non_repudiation', 'privacy', 'safety'}
OBJ_STRENGTH = {'primary', 'supporting', 'none'}
CSF_CODES = {'govern', 'identify', 'protect', 'detect', 'respond', 'recover'}
CSF_STRENGTH = {'primary', 'supporting'}
PURPOSE_CODES = {'preventive', 'deterrent', 'detective', 'corrective', 'containment',
                 'recovery', 'compensating', 'directive', 'monitoring', 'assurance'}
IMPL_CODES = {'administrative', 'technical', 'operational', 'physical', 'human',
              'legal_contractual', 'architectural'}
TIER_CODES = {'essential', 'advanced', 'very_advanced', 'full'}
EVIDENCE_TYPES = {'DOCUMENT', 'SCREENSHOT', 'LOG', 'REPORT', 'CONFIG', 'ATTESTATION', 'LINK', 'OTHER'}
ACTION_KINDS = {'ACTION', 'VERIFICATION'}

# The staging content that defines a promotable artifact (order-stable, hashed).
HASH_FIELDS = [
    'title_en', 'definition_short_en', 'definition_full_en', 'objective_en', 'canonical_statement',
    'proposed_type', 'proposed_abstraction_level', 'proposed_primary_domain', 'proposed_sub_domain',
    'proposed_obligation_level', 'proposed_requirement_type', 'proposed_control_nature',
    'proposed_control_function', 'proposed_testability', 'proposed_asset_type', 'proposed_asset_criticality',
    'proposed_mappings_json', 'merge_action',
    # --- content enrichment (007) ---
    'title_ar', 'definition_short_ar', 'definition_full_ar', 'objective_ar',
    'evidence_en', 'evidence_ar', 'verification_method_note', 'verification_method_note_ar',
    'proposed_scoring_weight', 'proposed_risk_reduction', 'proposed_effort_level', 'proposed_tier',
    'proposed_actions_json', 'proposed_variants_json', 'proposed_security_objectives_json',
    'proposed_csf_functions_json', 'proposed_control_purposes_json', 'proposed_implementation_types_json',
    'proposed_maturity_requirements_json', 'proposed_verification_json',
]


def load_valid(conn):
    def s(t):
        return {r[0] for r in conn.execute(f"SELECT code FROM {t}")}
    return {
        'type': s('lk_artifact_type'), 'abs': s('lk_abstraction_level'), 'dom': s('lk_sdt_domain'),
        'sub': s('lk_sdt_subdomain'), 'obl': s('lk_obligation_level'), 'rqt': s('lk_requirement_type'),
        'nat': s('lk_control_nature'), 'fun': s('lk_control_function'), 'tst': s('lk_testability'),
        'asset_type': s('lk_asset_type'),
        'strength': {'DIRECT', 'INDIRECT', 'PARTIAL', 'INFORMATIVE'},
        'asset_crit': {'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'},
    }


def content_hash(row):
    payload = {k: (row[k] if k in row.keys() else None) for k in HASH_FIELDS}
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()


def count_mandatory_verbs(text):
    return len(re.findall(r'\b(shall|must|require[sd]?|establish|administer|restrict|prohibit|monitor|route|separate|maintain|delete|classif\w+)\b', (text or '').lower()))


def _parse_json(row, col):
    """Return (value, error). value is None if column absent/empty."""
    if col not in row.keys() or not row[col]:
        return None, None
    try:
        return json.loads(row[col]), None
    except Exception:
        return None, f"malformed JSON in {col}"


def enrichment_blockers(row):
    """Validate the authored rich collections (007) against their code enums so
    a bad code is caught here rather than silently swallowed at apply time.
    Returns a list of blocker strings; empty = clean (or nothing authored)."""
    b = []

    def coll(col):
        v, err = _parse_json(row, col)
        if err:
            b.append(err)
            return None
        if v is None:
            return None
        if not isinstance(v, list):
            b.append(f"{col} must be a JSON array")
            return None
        return v

    objs = coll('proposed_security_objectives_json')
    if objs is not None:
        seen = set()
        for o in objs:
            code, st = (o.get('objective_code'), o.get('strength')) if isinstance(o, dict) else (None, None)
            if code not in OBJ_CODES:
                b.append(f"invalid objective_code {code}")
            if st not in OBJ_STRENGTH:
                b.append(f"invalid objective strength {st}")
            if code in seen:
                b.append(f"duplicate objective_code {code}")
            seen.add(code)

    csf = coll('proposed_csf_functions_json')
    if csf is not None:
        seen = set()
        for c in csf:
            code, st = (c.get('csf_code'), c.get('strength')) if isinstance(c, dict) else (None, None)
            if code not in CSF_CODES:
                b.append(f"invalid csf_code {code}")
            if st not in CSF_STRENGTH:
                b.append(f"invalid csf strength {st}")
            if code in seen:
                b.append(f"duplicate csf_code {code}")
            seen.add(code)

    for col, codes, label in (('proposed_control_purposes_json', PURPOSE_CODES, 'purpose_code'),
                              ('proposed_implementation_types_json', IMPL_CODES, 'impl_type_code')):
        items = coll(col)
        if items is not None:
            seen = set()
            for it in items:
                code = it.get(label) if isinstance(it, dict) else it
                if code not in codes:
                    b.append(f"invalid {label} {code}")
                if code in seen:
                    b.append(f"duplicate {label} {code}")
                seen.add(code)

    mat = coll('proposed_maturity_requirements_json')
    if mat is not None:
        seen = set()
        for m in mat:
            tc = m.get('tier_code') if isinstance(m, dict) else None
            if tc not in TIER_CODES:
                b.append(f"invalid maturity tier_code {tc}")
            if tc in seen:
                b.append(f"duplicate maturity tier_code {tc}")
            seen.add(tc)

    acts = coll('proposed_actions_json')
    if acts is not None:
        for a in acts:
            if not isinstance(a, dict):
                b.append('action entry not an object'); continue
            if a.get('kind', 'ACTION') not in ACTION_KINDS:
                b.append(f"invalid action kind {a.get('kind')}")
            if not isinstance(a.get('seq'), int) or a.get('seq') < 0:
                b.append(f"action seq must be int>=0 (got {a.get('seq')})")
            if not a.get('text_en'):
                b.append('action missing text_en')

    var = coll('proposed_variants_json')
    if var is not None:
        seen = set()
        for v in var:
            plat = v.get('platform') if isinstance(v, dict) else None
            if not plat:
                b.append('variant missing platform')
            elif plat in seen:
                b.append(f"duplicate variant platform {plat}")
            seen.add(plat)

    verif, err = _parse_json(row, 'proposed_verification_json')
    if err:
        b.append(err)
    elif verif is not None:
        if not isinstance(verif, dict):
            b.append('proposed_verification_json must be a JSON object')
        else:
            for et in verif.get('evidence_types', []) or []:
                if et not in EVIDENCE_TYPES:
                    b.append(f"invalid evidence_type {et}")
            for st in verif.get('testing_steps', []) or []:
                if not isinstance(st, dict) or not isinstance(st.get('seq'), int) or st.get('seq') < 0:
                    b.append('verification step seq must be int>=0')
                elif not st.get('text_en'):
                    b.append('verification step missing text_en')
    return b


def promotion_blockers(row, valid):
    """Return a list of blocker strings. Empty list = promotable."""
    b = []
    if row['ready_for_promotion'] != 1:
        b.append('not ready_for_promotion')
    if (row['final_review_status'] or '') not in ('APPROVED', 'SPLIT_AND_APPROVED'):
        b.append(f"final_review_status={row['final_review_status']} (not approved)")
    if (row['curation_status'] or '') == 'REJECTED':
        b.append('curation_status REJECTED')
    if row['requires_human_review'] == 1:
        b.append('requires_human_review=1 (NEEDS_REVIEW must not be promoted)')
    if row['classification_confidence'] is not None and row['classification_confidence'] <= 0.70:
        b.append('confidence <= 0.70')
    existing = row['promotion_blockers']
    if existing:
        try:
            for x in json.loads(existing):
                b.append(f"declared blocker: {x}")
        except Exception:
            b.append('declared blockers present')
    t = row['proposed_type']
    if t not in valid['type']:
        b.append(f"invalid type {t}")
    if row['proposed_primary_domain'] not in valid['dom']:
        b.append('invalid primary_domain')
    sd = row['proposed_sub_domain']
    if sd not in valid['sub']:
        b.append('invalid sub_domain')
    elif row['proposed_primary_domain'] and sd[:5] != row['proposed_primary_domain']:
        b.append('sub_domain does not belong to primary_domain')
    if row['proposed_obligation_level'] not in valid['obl']:
        b.append('invalid obligation_level')
    if not row['title_en'] or not row['definition_short_en']:
        b.append('missing English drafting (title/definition)')
    # type-specific required fields + value validity
    for f in REQUIRED_BY_TYPE.get(t, []):
        v = row[f] if f in row.keys() else None
        if not v:
            b.append(f"missing required field for {t}: {f}")
        else:
            vk = {'proposed_requirement_type': 'rqt', 'proposed_control_nature': 'nat',
                  'proposed_control_function': 'fun', 'proposed_testability': 'tst',
                  'proposed_asset_type': 'asset_type', 'proposed_asset_criticality': 'asset_crit'}[f]
            if v not in valid[vk]:
                b.append(f"invalid {f}={v}")
    # lineage / mappings
    try:
        maps = json.loads(row['proposed_mappings_json']) if row['proposed_mappings_json'] else []
    except Exception:
        maps = []
    if not maps:
        b.append('lineage/mappings missing')
    for m in maps:
        if not m.get('source_document') or not m.get('raw_id'):
            b.append(f"incomplete lineage entry {m.get('raw_id')}")
        ms = m.get('mapping_strength')
        if ms not in valid['strength']:
            b.append(f"invalid mapping_strength {ms}")
        elif ms != 'DIRECT' and not m.get('rationale'):
            b.append(f"non-DIRECT mapping without rationale ({m.get('raw_id')})")
    # atomicity: canonical must express a single security idea
    if count_mandatory_verbs(row['definition_short_en']) > 2:
        b.append('canonical short definition is not atomic (multiple mandatory verbs)')
    # optional enrichment fields (007) — validate only if present
    def _opt(k):
        return row[k] if k in row.keys() else None
    sw = _opt('proposed_scoring_weight')
    if sw is not None and sw < 0:
        b.append('scoring_weight < 0')
    rr = _opt('proposed_risk_reduction')
    if rr is not None and not (2 <= rr <= 5):
        b.append('risk_reduction not in 2..5')
    ef = _opt('proposed_effort_level')
    if ef is not None and ef not in ('low', 'medium', 'high'):
        b.append(f'invalid effort_level {ef}')
    tr = _opt('proposed_tier')
    if tr is not None and tr not in ('essential', 'advanced', 'very_advanced', 'full'):
        b.append(f'invalid tier {tr}')
    # authored rich collections (007) — reject bad codes fail-loud
    b.extend(enrichment_blockers(row))
    return b
