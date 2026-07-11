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

# The staging content that defines a promotable artifact (order-stable, hashed).
HASH_FIELDS = [
    'title_en', 'definition_short_en', 'definition_full_en', 'objective_en', 'canonical_statement',
    'proposed_type', 'proposed_abstraction_level', 'proposed_primary_domain', 'proposed_sub_domain',
    'proposed_obligation_level', 'proposed_requirement_type', 'proposed_control_nature',
    'proposed_control_function', 'proposed_testability', 'proposed_asset_type', 'proposed_asset_criticality',
    'proposed_mappings_json', 'merge_action',
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
    return b
