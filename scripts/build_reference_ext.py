# -*- coding: utf-8 -*-
"""
Generates migrations/009_reference_extensions.sql — the reference data for the
content-enrichment layer (migrations 007/008), kept SEPARATE from 003 so the
committed migrations 001-006 are never modified.

Emits:
  - New lk_* extension lists (each with a `usacm_map` to the nearest canonical
    USACM value, mirroring ref_asset_types.category).
  - scoring_policy + scoring_bands seed rows (tables created in 007).
  - amani_domain_alias seed rows (amani domain key -> SDT primary/sub).
  - reference/content_ext_lists.json (machine-readable mirror).

Run: python scripts/build_reference_ext.py
"""
import io
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MIG = os.path.join(ROOT, 'migrations')
REF = os.path.join(ROOT, 'reference')

# lk lists: list_code -> (rows[(code,name_en,name_ar,usacm_map,map_note)])
LK = {
    'lk_security_objective': [
        ('confidentiality', 'Confidentiality', 'السرية', None, 'CIA property; no USACM canonical'),
        ('integrity', 'Integrity', 'السلامة', None, None),
        ('availability', 'Availability', 'التوافر', None, None),
        ('authenticity', 'Authenticity', 'الأصالة', None, None),
        ('accountability', 'Accountability', 'المساءلة', None, None),
        ('non_repudiation', 'Non-Repudiation', 'عدم الإنكار', None, None),
        ('privacy', 'Privacy', 'الخصوصية', None, 'hint SD-02'),
        ('safety', 'Safety', 'السلامة العامة', None, None),
    ],
    'lk_objective_strength': [
        ('primary', 'Primary', 'أساسي', None, None),
        ('supporting', 'Supporting', 'داعم', None, None),
        ('none', 'None', 'لا يوجد', None, None),
    ],
    'lk_csf_function': [
        ('govern', 'Govern', 'الحوكمة', 'ABS-GOV', None),
        ('identify', 'Identify', 'التعريف', 'ABS-RIS', None),
        ('protect', 'Protect', 'الحماية', 'FUN-PRE', None),
        ('detect', 'Detect', 'الكشف', 'FUN-DET', None),
        ('respond', 'Respond', 'الاستجابة', 'FUN-COR', None),
        ('recover', 'Recover', 'التعافي', 'FUN-REC', None),
    ],
    'lk_control_purpose': [
        ('preventive', 'Preventive', 'وقائي', 'FUN-PRE', None),
        ('deterrent', 'Deterrent', 'ردعي', 'FUN-DRR', None),
        ('detective', 'Detective', 'كشفي', 'FUN-DET', None),
        ('corrective', 'Corrective', 'تصحيحي', 'FUN-COR', None),
        ('containment', 'Containment', 'احتواء', 'FUN-COR', None),
        ('recovery', 'Recovery', 'استرداد', 'FUN-REC', None),
        ('compensating', 'Compensating', 'تعويضي', 'FUN-COM', None),
        ('directive', 'Directive', 'توجيهي', 'FUN-PRE', None),
        ('monitoring', 'Monitoring', 'مراقبة', 'FUN-DET', None),
        ('assurance', 'Assurance', 'ضمان', 'FUN-DET', None),
    ],
    'lk_implementation_type': [
        ('administrative', 'Administrative', 'إداري', 'NAT-ORG', None),
        ('technical', 'Technical', 'تقني', 'NAT-TEC', None),
        ('operational', 'Operational', 'تشغيلي', 'NAT-ORG', None),
        ('physical', 'Physical', 'مادي', 'NAT-PHY', None),
        ('human', 'Human', 'بشري', 'NAT-HUM', None),
        ('legal_contractual', 'Legal/Contractual', 'قانوني/تعاقدي', 'NAT-ORG', None),
        ('architectural', 'Architectural', 'معماري', 'NAT-TEC', None),
    ],
    'lk_tier': [
        ('essential', 'Essential', 'أساسي', 'INITIAL', None),
        ('advanced', 'Advanced', 'متقدّم', 'DEFINED', None),
        ('very_advanced', 'Very Advanced', 'متقدّم جداً', 'MANAGED', None),
        ('full', 'Full', 'كامل', 'OPTIMIZED', None),
    ],
    'lk_platform': [
        ('all', 'All Platforms', 'كل المنصات', None, "surface via artifact_tags Technology"),
        ('windows', 'Windows', 'ويندوز', None, None),
        ('macos', 'macOS', 'ماك', None, None),
        ('linux', 'Linux', 'لينكس', None, None),
        ('ios', 'iOS', 'iOS', None, None),
        ('android', 'Android', 'أندرويد', None, None),
        ('web', 'Web', 'ويب', None, None),
        ('browser', 'Browser', 'المتصفح', None, None),
        ('router', 'Router', 'راوتر', None, None),
        ('iot', 'IoT', 'إنترنت الأشياء', None, None),
        ('cloud', 'Cloud', 'سحابة', None, None),
    ],
}

SCORING_POLICY = ('default', 60, 0.5, 0, 'amani-equivalent: critical cap 60, dependency clamp 0.5')
SCORING_BANDS = [  # (band_code, min_score, label_en, label_ar, sort)
    ('at_risk', 0, 'At Risk', 'في خطر', 0),
    ('fair', 61, 'Fair', 'مقبول', 1),
    ('strong', 75, 'Strong', 'قوي', 2),
    ('excellent', 90, 'Excellent', 'ممتاز', 3),
]

# amani domain key -> (sdt_primary, sdt_sub|None, confidence, needs_review, note)
AMANI_DOMAIN_ALIAS = {
    # personal (11)
    'identity_accounts': ('SD-03', 'SD-03.02', 0.75, 1, 'accounts/passwords; spans lifecycle+authz'),
    'devices': ('SD-04', 'SD-04.02', 0.8, 0, 'endpoint security'),
    'applications_browsing': ('SD-05', None, 0.6, 1, 'apps(SD-05) vs browsing/web(SD-04.05)'),
    'communications': ('SD-04', 'SD-04.05', 0.75, 0, 'email/web/digital comms'),
    'networks_connectivity': ('SD-04', 'SD-04.01', 0.85, 0, 'network & comms security'),
    'financial_transactions': ('SD-02', None, 0.5, 1, 'personal concept; not a clean SDT domain'),
    'data_privacy': ('SD-02', 'SD-02.04', 0.7, 1, 'data protection / privacy'),
    'physical_travel': ('SD-08', 'SD-08.04', 0.75, 0, 'physical & environmental'),
    'human_factors': ('SD-08', 'SD-08.01', 0.8, 0, 'awareness & training'),
    'incident_recovery': ('SD-07', 'SD-07.01', 0.8, 0, 'incident management'),
    'smart_home_iot': ('SD-04', 'SD-04.02', 0.6, 1, 'IoT/endpoint'),
    # enterprise codes (7)
    'GRC': ('SD-01', None, 0.7, 1, 'Governance, Risk & Compliance'),
    'IAM': ('SD-03', 'SD-03.03', 0.8, 0, 'Identity & Access Management'),
    'IPS': ('SD-04', None, 0.6, 1, 'Infrastructure Protection & Security'),
    'DPP': ('SD-02', 'SD-02.04', 0.75, 0, 'Data Protection & Privacy'),
    'DMR': ('SD-06', None, 0.6, 1, 'Detection, Monitoring & Response'),
    'APP': ('SD-05', 'SD-05.01', 0.8, 0, 'Application Security'),
    'RCR': ('SD-07', 'SD-07.04', 0.75, 0, 'Resilience, Continuity & Recovery'),
}


def s(v):
    return 'NULL' if v is None else "'" + str(v).replace("'", "''") + "'"


def build():
    out = ['-- ============================================================================',
           '-- SecureGuide — Migration 009: Reference Extensions (content-enrichment layer)',
           '-- GENERATED by scripts/build_reference_ext.py — do not edit by hand.',
           '-- New lk_* extension lists (with usacm_map) + scoring policy/bands + amani alias.',
           '-- Kept separate from 003 so migrations 001-006 are never modified.',
           '-- ============================================================================', '',
           'PRAGMA foreign_keys = ON;', '',
           "INSERT OR IGNORE INTO schema_migrations (version, description) VALUES ('009','Reference extensions: enrichment lk_* + scoring policy/bands + amani domain alias');", '']

    for lk, rows in LK.items():
        out.append(f'-- {lk}')
        out.append(f'CREATE TABLE IF NOT EXISTS {lk} (')
        out.append('    code TEXT PRIMARY KEY, name_en TEXT, name_ar TEXT,')
        out.append('    usacm_map TEXT, map_note TEXT, sort_order INTEGER NOT NULL DEFAULT 0')
        out.append(');')
        for i, (code, en, ar, um, note) in enumerate(rows):
            out.append(f"INSERT OR IGNORE INTO {lk} (code,name_en,name_ar,usacm_map,map_note,sort_order) "
                       f"VALUES ({s(code)},{s(en)},{s(ar)},{s(um)},{s(note)},{i});")
        out.append('')

    out.append('-- scoring_policy + scoring_bands (tables created in 007)')
    out.append("INSERT OR IGNORE INTO scoring_policy (id,critical_cap,dependency_clamp_ceiling,accepted_risk_lifts_cap,note) "
               f"VALUES ({s(SCORING_POLICY[0])},{SCORING_POLICY[1]},{SCORING_POLICY[2]},{SCORING_POLICY[3]},{s(SCORING_POLICY[4])});")
    for bc, mn, en, ar, so in SCORING_BANDS:
        out.append(f"INSERT OR IGNORE INTO scoring_bands (policy_id,band_code,min_score,label_en,label_ar,sort_order) "
                   f"VALUES ('default',{s(bc)},{mn},{s(en)},{s(ar)},{so});")
    out.append('')

    out.append('-- amani_domain_alias (table created in 007)')
    for k, (pri, sub, conf, nr, note) in AMANI_DOMAIN_ALIAS.items():
        out.append(f"INSERT OR IGNORE INTO amani_domain_alias (amani_key,sdt_primary,sdt_sub,confidence,needs_review,note) "
                   f"VALUES ({s(k)},{s(pri)},{s(sub)},{conf},{nr},{s(note)});")
    out.append('')

    io.open(os.path.join(MIG, '009_reference_extensions.sql'), 'w', encoding='utf-8', newline='\n').write('\n'.join(out))

    # JSON mirror
    js = {lk: [{'code': c, 'name_en': en, 'name_ar': ar, 'usacm_map': um} for (c, en, ar, um, _n) in rows]
          for lk, rows in LK.items()}
    js['scoring_policy'] = {'critical_cap': SCORING_POLICY[1], 'dependency_clamp_ceiling': SCORING_POLICY[2]}
    js['scoring_bands'] = [{'code': b[0], 'min': b[1], 'label_en': b[2]} for b in SCORING_BANDS]
    js['amani_domain_alias'] = {k: {'sdt_primary': v[0], 'sdt_sub': v[1], 'needs_review': v[3]}
                                for k, v in AMANI_DOMAIN_ALIAS.items()}
    io.open(os.path.join(REF, 'content_ext_lists.json'), 'w', encoding='utf-8').write(
        json.dumps(js, ensure_ascii=False, indent=2))

    print(f"lk lists: {len(LK)} | scoring bands: {len(SCORING_BANDS)} | amani aliases: {len(AMANI_DOMAIN_ALIAS)}")
    print("Wrote migrations/009_reference_extensions.sql + reference/content_ext_lists.json")


if __name__ == '__main__':
    build()
