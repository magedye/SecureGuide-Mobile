# -*- coding: utf-8 -*-
"""Generate migrations/013_threat_reference.sql — SADP v1.0 §2.4/§2.6.

Seeds the canonical THR-* threat taxonomy into lk_threat (the classification that
replaces the retired free-form 'Threat' tag) plus fallbacks, and the reviewable
amani_threat_alias mapping every amani threat_id vocabulary term to a THR-* code.
The importer maps amani threats through this alias FAIL-LOUD on any unmapped term.
Every value here is the §2.6 change-control record (see docs/SADP_CONFORMANCE.md §5)."""
import io
import os

MIG = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'migrations'))
OUT = os.path.join(MIG, '013_threat_reference.sql')

# canonical THR-* : (code, name_en, name_ar, category)
THREATS = [
    ('THR-MALWARE', 'Malware', 'برمجيات خبيثة', 'malicious_code'),
    ('THR-RANSOMWARE', 'Ransomware & Extortion', 'فدية وابتزاز', 'malicious_code'),
    ('THR-PHISHING', 'Phishing', 'تصيّد', 'social'),
    ('THR-SOCIAL-ENGINEERING', 'Social Engineering', 'هندسة اجتماعية', 'social'),
    ('THR-CREDENTIAL-THEFT', 'Credential Theft', 'سرقة بيانات الاعتماد', 'identity'),
    ('THR-ACCOUNT-TAKEOVER', 'Account Takeover', 'الاستيلاء على الحساب', 'identity'),
    ('THR-DATA-BREACH', 'Data Breach & Exposure', 'اختراق/كشف البيانات', 'data'),
    ('THR-DATA-EXFILTRATION', 'Data Exfiltration', 'تسريب البيانات', 'data'),
    ('THR-DATA-LOSS', 'Data Loss & Misdelivery', 'فقد/سوء تسليم البيانات', 'data'),
    ('THR-UNAUTHORIZED-ACCESS', 'Unauthorized Access & Intrusion', 'وصول غير مصرّح/اختراق', 'access'),
    ('THR-NETWORK-ATTACK', 'Network & Web Attack', 'هجوم شبكي/ويب', 'network'),
    ('THR-INTERCEPTION', 'Interception & Eavesdropping', 'اعتراض/تنصّت', 'network'),
    ('THR-DEVICE-COMPROMISE', 'Device & System Compromise', 'اختراق الجهاز/النظام', 'endpoint'),
    ('THR-DEVICE-LOSS', 'Device Loss or Theft', 'فقد/سرقة الجهاز', 'physical'),
    ('THR-PHYSICAL', 'Physical & Tampering', 'مادي/عبث', 'physical'),
    ('THR-SURVEILLANCE', 'Surveillance & Tracking', 'مراقبة/تتبّع', 'privacy'),
    ('THR-VULNERABILITY-EXPLOIT', 'Vulnerability Exploitation', 'استغلال الثغرات', 'exploitation'),
    ('THR-FINANCIAL-FRAUD', 'Financial Fraud', 'احتيال مالي', 'fraud'),
    ('THR-TARGETED-ATTACK', 'Targeted Attack', 'هجوم موجّه', 'exploitation'),
    ('THR-MISCONFIG', 'Misconfiguration & Drift', 'سوء إعداد/انحراف', 'configuration'),
]
FALLBACKS = [
    ('THR-NA', 'Not Applicable', 'لا ينطبق', 'fallback'),
    ('THR-UNKNOWN', 'Unknown / Undecided', 'غير محسوم', 'fallback'),
    ('THR-MULTI', 'Multiple Threats', 'تهديدات متعددة', 'fallback'),
]

# amani threat_id vocabulary -> THR-* (reviewable; importer fails loud if a term is absent)
ALIAS = {
    'malware': 'THR-MALWARE', 'THR-MALWARE-001': 'THR-MALWARE',
    'ransomware': 'THR-RANSOMWARE', 'THR-RANSOMWARE-001': 'THR-RANSOMWARE', 'extortion': 'THR-RANSOMWARE',
    'phishing': 'THR-PHISHING',
    'social_engineering': 'THR-SOCIAL-ENGINEERING',
    'credential_theft': 'THR-CREDENTIAL-THEFT', 'credential_attack': 'THR-CREDENTIAL-THEFT',
    'account_takeover': 'THR-ACCOUNT-TAKEOVER', 'account_lockout': 'THR-ACCOUNT-TAKEOVER',
    'identity_theft': 'THR-ACCOUNT-TAKEOVER', 'session_hijacking': 'THR-ACCOUNT-TAKEOVER',
    'sim_swap': 'THR-ACCOUNT-TAKEOVER',
    'data_breach': 'THR-DATA-BREACH', 'data_exposure': 'THR-DATA-BREACH',
    'data_exfiltration': 'THR-DATA-EXFILTRATION', 'THR-DATA-EXFIL-001': 'THR-DATA-EXFILTRATION',
    'data_loss': 'THR-DATA-LOSS', 'data_retention': 'THR-DATA-LOSS', 'misdelivery': 'THR-DATA-LOSS',
    'unauthorized_access': 'THR-UNAUTHORIZED-ACCESS', 'third_party_access_abuse': 'THR-UNAUTHORIZED-ACCESS',
    'THR-INTRUSION-001': 'THR-UNAUTHORIZED-ACCESS', 'cloud_compromise': 'THR-UNAUTHORIZED-ACCESS',
    'network_compromise': 'THR-NETWORK-ATTACK', 'router_compromise': 'THR-NETWORK-ATTACK',
    'THR-WEB-ATTACK-001': 'THR-NETWORK-ATTACK',
    'network_interception': 'THR-INTERCEPTION', 'message_interception': 'THR-INTERCEPTION',
    'proximity_attack': 'THR-INTERCEPTION',
    'device_compromise': 'THR-DEVICE-COMPROMISE', 'iot_compromise': 'THR-DEVICE-COMPROMISE',
    'malicious_charging': 'THR-DEVICE-COMPROMISE',
    'device_loss_theft': 'THR-DEVICE-LOSS',
    'physical_risk': 'THR-PHYSICAL', 'border_search': 'THR-PHYSICAL', 'tampering': 'THR-PHYSICAL',
    'surveillance': 'THR-SURVEILLANCE', 'tracking_profiling': 'THR-SURVEILLANCE',
    'exposure_targeting': 'THR-SURVEILLANCE', 'shoulder_surfing': 'THR-SURVEILLANCE',
    'vulnerability_exploitation': 'THR-VULNERABILITY-EXPLOIT', 'lateral_movement': 'THR-VULNERABILITY-EXPLOIT',
    'financial_fraud': 'THR-FINANCIAL-FRAUD',
    'targeted_attack': 'THR-TARGETED-ATTACK',
    'security_drift': 'THR-MISCONFIG', 'limited_control': 'THR-MISCONFIG',
    'single_point_failure': 'THR-MISCONFIG',
}
# terms whose mapping is a judgement call -> flag needs_review=1
REVIEW = {'account_lockout', 'cloud_compromise', 'limited_control', 'single_point_failure',
          'lateral_movement', 'exposure_targeting'}


def q(s):
    return "'" + s.replace("'", "''") + "'"


def main():
    codes = {c for c, *_ in THREATS} | {c for c, *_ in FALLBACKS}
    bad = {k: v for k, v in ALIAS.items() if v not in codes}
    assert not bad, f"alias maps to unknown THR codes: {bad}"

    L = [
        '-- ============================================================================',
        '-- SecureGuide — Migration 013: Threat reference data (SADP v1.0 §2.4/§2.6)',
        '-- ----------------------------------------------------------------------------',
        '-- Generated by scripts/build_threat_reference.py. Seeds the canonical THR-*',
        '-- taxonomy + fallbacks into lk_threat, and the reviewable amani_threat_alias.',
        '-- Additive & idempotent. Recorded in docs/SADP_CONFORMANCE.md §5.',
        '-- ============================================================================',
        '',
        "INSERT OR IGNORE INTO schema_migrations (version, description)",
        "VALUES ('013', 'Canonical THR-* threat taxonomy + amani_threat_alias (SADP 2.4)');",
        '',
        '-- ---- lk_threat : canonical taxonomy ----',
    ]
    for i, (code, en, ar, cat) in enumerate(THREATS):
        L.append(f"INSERT OR IGNORE INTO lk_threat (code, name_en, name_ar, category, sort_order) "
                 f"VALUES ({q(code)}, {q(en)}, {q(ar)}, {q(cat)}, {i});")
    L.append('-- fallbacks (SADP §2.3)')
    for i, (code, en, ar, cat) in enumerate(FALLBACKS):
        L.append(f"INSERT OR IGNORE INTO lk_threat (code, name_en, name_ar, category, sort_order) "
                 f"VALUES ({q(code)}, {q(en)}, {q(ar)}, {q(cat)}, {90 + i});")
    L.append('')
    L.append('-- ---- amani_threat_alias : amani vocabulary -> THR-* ----')
    for k in sorted(ALIAS):
        nr = 1 if k in REVIEW else 0
        L.append(f"INSERT OR IGNORE INTO amani_threat_alias (amani_key, threat_code, needs_review) "
                 f"VALUES ({q(k)}, {q(ALIAS[k])}, {nr});")
    L.append('')
    io.open(OUT, 'w', encoding='utf-8', newline='\n').write('\n'.join(L))
    print(f"wrote {OUT}: {len(THREATS)} THR-* + {len(FALLBACKS)} fallbacks + {len(ALIAS)} aliases")


if __name__ == '__main__':
    main()
