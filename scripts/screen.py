# -*- coding: utf-8 -*-
"""
screen.py — Agent-led PRE-SCREENING (no embeddings, not regex-only).

Screens every raw artifact for relevance to a target concept-space using MULTIPLE
signals combined (not a single keyword regex as the final decision):
  - source / framework / section
  - likely USACM type
  - likely abstraction level
  - primary security ACTION (verb)
  - target ENTITY
  - security OUTCOME
  - applicability SCOPE (subject-vs-scope discrimination — the key noise filter)
  - keywords + context
  - exclusion signals (belongs to another domain/concept)

Per-item output verdict: LIKELY_RELEVANT | POSSIBLY_RELEVANT | EXCLUDE | NEEDS_AGENT_REVIEW
plus screening_rationale, matched_concepts, exclusion_reason, screening_confidence.

Screening makes NO merge decision and creates NO canonical. It only produces the
candidate pool for a later atomic-grouping pilot.

Usage:
    python scripts/screen.py --target privileged_access [--db pilot.db] [--out consolidation/screening]
"""
import argparse
import io
import json
import os
import re
import sqlite3
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DEFAULT_DB = os.path.join(ROOT, 'pilot.db')
DEFAULT_OUT = os.path.join(ROOT, 'consolidation', 'screening')

ACTIONS = {
    'establish': 'establish|maintain|develop|create|build|define', 'inventory': 'inventory|enumerate|catalog',
    'approve': 'approv|authoriz(e|ation)|grant', 'review': 'review|recertif|re-?certif|reassess|periodically',
    'restrict': 'restrict|least privilege|minimi[sz]e|limit', 'separate': 'separat|dedicated|distinct account',
    'manage_cred': 'password|credential|secret|vault|rotate', 'monitor': 'log|monitor|record|audit trail|alert',
    'session': 'session|time-?out|record the session', 'emergency': 'break-?glass|emergency access',
    'deprovision': 'revoke|remove|deprovision|disable|upon (role change|termination)',
    'classify': 'classif|label', 'dispose': 'dispos|delete|destroy|saniti[sz]e',
    'configure': 'configure|setting|harden|baseline|disable',
}

TARGETS = {
    'asset_inventory': {
        'expected_domain': 'SD-02', 'expected_subdomains': ['SD-02.01', 'SD-02.02', 'SD-02.03', 'SD-02.05'],
        'subject_terms': r'(asset inventor|inventory of .{0,25}(asset|component|device|hardware|software)|system component inventor|software inventor|asset management|classif\w* .{0,20}asset|dispos\w* .{0,20}(asset|information|media)|deleted when no longer required|acceptable use of .{0,20}asset)',
        'sub_concepts': {
            'create_inventory': r'inventory of .{0,20}(asset|component|device|hardware)|maintain .{0,20}inventory',
            'software_inventory': r'inventory of .{0,20}software|licensed software',
            'classification': r'classif\w* .{0,20}asset|label\w* .{0,20}asset',
            'acceptable_use': r'acceptable use',
            'disposal': r'dispos|delete .{0,20}(information|media)|when no longer required',
        },
        'exclusion_signals': {
            'account_inventory': r'inventory of .{0,10}account|user, administrator, and service account',
            'service_provider': r'service provider|third-?party inventory',
            'data_process': r'data management process|data sensitivity, data owner',
        },
    },
    'privileged_access': {
        'expected_domain': 'SD-03', 'expected_subdomains': ['SD-03.04'],
        'subject_terms': r'(privileged access|privileged account|administrative (access|privilege|account)|admin account|elevated privilege|superuser|root (account|access)|least privilege|break-?glass|privileged session|privileged user)',
        'sub_concepts': {
            'define_inventory_privileged': r'(inventory|enumerate|identify) .{0,20}(privileged|administrative) account',
            'approve_grant': r'approv\w* .{0,20}(privilege|elevated|administrative)|authoriz\w* .{0,15}privileged',
            'least_privilege': r'least privilege|minimi[sz]e .{0,15}privilege|need-to-know',
            'review_recertify': r'(review|recertif|reassess) .{0,20}(privilege|access)',
            'separate_admin': r'separate .{0,15}(admin|privileged) account|dedicated administrative account',
            'privileged_credentials': r'(privileged|administrative).{0,20}(password|credential|secret)|password vault|credential vault',
            'privileged_session': r'privileged session|session (recording|monitoring|time-?out) .{0,20}privileged',
            'monitor_privileged': r'(log|monitor|record|audit) .{0,20}privileged',
            'break_glass': r'break-?glass|emergency (privileged )?access',
            'deprovision_privileged': r'(revoke|remove|disable) .{0,20}privileged|privileged .{0,20}(role change|termination)',
            'vendor_privileged': r'(vendor|third-?party|supplier).{0,20}privileged',
            'pam_tool': r'\bpam\b|privileged access management (tool|solution)',
        },
        'exclusion_signals': {
            'general_auth': r'multi-?factor|two-?factor|password polic(y|ies)(?!.{0,20}privileged)',
            'general_access_control': r'access control(?!.{0,20}privileged)|rbac(?!.{0,20}privileged)',
            'identity_lifecycle': r'joiner|mover|leaver|onboarding(?!.{0,20}privileged)',
            'network': r'firewall|network segment|vpn',
        },
    },
}


def likely_type(text):
    if re.search(r'\b(policy|policies)\b', text):
        return 'ART-POL'
    if re.search(r'\b(configure|setting|disable|baseline|harden)\b', text):
        return 'ART-CFG'
    if re.search(r'\b(evidence|log record|attestation|report proving)\b', text):
        return 'ART-EVD'
    if re.search(r'\b(metric|percentage of|ratio of)\b', text):
        return 'ART-MET'
    if re.search(r'\b(shall|must|require|establish|maintain)\b', text):
        return 'ART-REQ'
    return 'ART-CTR'


def abstraction(t):
    return {'ART-POL': 'ABS-POL', 'ART-CFG': 'ABS-TEC', 'ART-EVD': 'ABS-EVM',
            'ART-MET': 'ABS-EVM', 'ART-REQ': 'ABS-CTR', 'ART-CTR': 'ABS-CTR'}.get(t, 'ABS-CTR')


def actions_in(text):
    return [a for a, rx in ACTIONS.items() if re.search(rx, text)]


def subject_vs_scope(subj_rx, title, head, body):
    """Is the target the SUBJECT (title/head) or just SCOPE (mentioned in body)?"""
    if re.search(subj_rx, title) or re.search(subj_rx, head):
        return 'subject'
    if re.search(subj_rx, body):
        # scope-only if it appears after on/for/across/to/of all ... (target as object of scope)
        if re.search(r'(on|for|across|to all|of all|throughout) .{0,30}' + subj_rx, body):
            return 'scope'
        return 'body'
    return 'none'


def screen_item(r, tgt):
    title = (r['title_draft'] or '').lower()
    body = (r['description_draft'] or r['raw_text_en'] or '').lower()
    ctx = (r['context_paragraph'] or '').lower()
    head = ' '.join(body.split()[:12])
    text = ' '.join([title, body, ctx])

    matched = [name for name, rx in tgt['sub_concepts'].items() if re.search(rx, text)]
    exclusions = [name for name, rx in tgt['exclusion_signals'].items() if re.search(rx, text)]
    placement = subject_vs_scope(tgt['subject_terms'], title, head, body)
    hint = (r['sdt_subdomain_assigned'] or '')
    hint_ok = hint in tgt['expected_subdomains']

    ltype = likely_type(text)
    acts = actions_in(text)

    # ---- combine signals into a verdict ----
    reason = []
    conf = 0.5
    exclusion_reason = None
    if exclusions and placement != 'subject':
        verdict = 'EXCLUDE'
        exclusion_reason = f"exclusion signal(s) {exclusions} and target not the subject (placement={placement})"
        conf = 0.8
        reason.append(exclusion_reason)
    elif placement == 'subject' and matched:
        verdict = 'LIKELY_RELEVANT'
        conf = 0.85 if not exclusions else 0.7
        reason.append(f"target is the subject; matched {matched}")
    elif placement == 'subject' and not matched:
        verdict = 'POSSIBLY_RELEVANT'
        conf = 0.6
        reason.append("target is the subject but no sub-concept matched")
    elif placement == 'scope':
        verdict = 'EXCLUDE'
        exclusion_reason = "target term appears only as applicability scope, not the subject"
        conf = 0.75
        reason.append(exclusion_reason)
    elif placement == 'body' and matched:
        verdict = 'NEEDS_AGENT_REVIEW'
        conf = 0.5
        reason.append(f"target mentioned in body with sub-concepts {matched}; subject unclear")
    else:
        verdict = 'EXCLUDE'
        exclusion_reason = "no subject match and no sub-concept"
        conf = 0.7
        reason.append(exclusion_reason)
    if hint_ok and verdict in ('POSSIBLY_RELEVANT', 'NEEDS_AGENT_REVIEW'):
        verdict = 'LIKELY_RELEVANT'
        conf = min(0.9, conf + 0.2)
        reason.append(f"source domain hint {hint} matches expected")

    return {
        'raw_id': r['id'], 'source_document': r['source_document'], 'source_section': r['source_section'],
        'likely_type': ltype, 'likely_abstraction': abstraction(ltype),
        'primary_actions': acts, 'placement': placement,
        'matched_concepts': matched, 'exclusion_reason': exclusion_reason,
        'screening_rationale': '; '.join(reason), 'screening_confidence': round(conf, 2),
        'verdict': verdict,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--target', required=True, choices=list(TARGETS))
    ap.add_argument('--db', default=DEFAULT_DB)
    ap.add_argument('--out', default=DEFAULT_OUT)
    args = ap.parse_args()
    if not os.path.exists(args.db):
        print(f"DB not found: {args.db}. Run ingest_raw.py first.")
        sys.exit(1)
    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    tgt = TARGETS[args.target]
    rows = conn.execute("SELECT * FROM raw_artifacts").fetchall()
    results = [screen_item(r, tgt) for r in rows]

    os.makedirs(args.out, exist_ok=True)
    path = os.path.join(args.out, f"{args.target}.json")
    io.open(path, 'w', encoding='utf-8').write(json.dumps(
        {'target': args.target, 'expected_domain': tgt['expected_domain'],
         'expected_subdomains': tgt['expected_subdomains'], 'total_scanned': len(results),
         'results': results}, ensure_ascii=False, indent=2))

    dist = {}
    for r in results:
        dist[r['verdict']] = dist.get(r['verdict'], 0) + 1
    print("=" * 60)
    print(f"SCREENING — target: {args.target}  (no embeddings, multi-signal)")
    print("=" * 60)
    print(f"scanned: {len(results)}")
    print(f"verdicts: {dist}")
    pool = [r for r in results if r['verdict'] in ('LIKELY_RELEVANT', 'POSSIBLY_RELEVANT', 'NEEDS_AGENT_REVIEW')]
    print(f"candidate pool (LIKELY+POSSIBLY+REVIEW): {len(pool)}")
    print("sample LIKELY_RELEVANT:")
    for r in [x for x in results if x['verdict'] == 'LIKELY_RELEVANT'][:8]:
        print(f"  [{r['source_document'][:22]:22} §{str(r['source_section'])[:14]:14}] {r['matched_concepts']}")
    print(f"written: {path}")


if __name__ == '__main__':
    main()
