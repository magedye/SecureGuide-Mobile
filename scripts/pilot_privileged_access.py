# -*- coding: utf-8 -*-
"""
pilot_privileged_access.py — Privileged Access Management Pilot (SD-03.04 ONLY).

Second, bounded consolidation pilot. Uses screen.py's candidate pool, then the
agent splits it into ATOMIC PAM concepts (read + reason, no embeddings, no
regex-only decisions), honoring: no expansion outside SD-03.04; group >20 must
split; a canonical with >1 independent mandatory verb must split; any decision
confidence <= 0.80 requires human review; DIRECT still semantically verified.

Reuses validators from pilot_asset_inventory. Never writes security_artifacts,
never modifies raw.

Usage: python scripts/pilot_privileged_access.py [--db pilot.db] [--apply]
"""
import argparse
import io
import json
import os
import re
import sqlite3
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import pilot_asset_inventory as P  # reuse load_valid / validate_canonical / validate_mappings / lineage

OUT = os.path.join(ROOT, 'consolidation', 'privileged_access')
NP = P.NP
REVIEW_THRESHOLD = 0.80  # confidence <= this -> requires human review (PAM pilot rule)
MAX_GROUP = 20

GROUPS = [
    {
        'candidate_group_id': 'PA-01', 'concept_name': 'Manage Privileged Accounts', 'expected_sub_domain': 'SD-03.04',
        'members': [(f'{NP}::0008', 'NIST AC-2(7)(a) — establish and administer privileged user accounts per role-based scheme.')],
        'excluded': [(f'{NP}::0389', 'IA-2(1) MFA for privileged accounts is authentication (PA-04), not account management.')],
        'differences': 'AC-2(7) has multiple clauses (establish + monitor). This atomic artifact takes only "establish/administer privileged accounts"; the monitoring clause is handled by PA-05.',
        'decision': 'CANONICALIZE', 'decision_confidence': 0.85, 'requires_human_review': 0,
        'decision_rationale': 'Clear privileged-account management control; single mandatory action (establish/administer). Monitoring clause split to PA-05.',
        'canonical': {
            'title_en': 'Privileged Account Management', 'definition_short_en': 'This control requires that privileged user accounts be established and administered under an approved, role-based scheme.',
            'definition_full_en': 'This artifact requires privileged (administrative) user accounts to be created, assigned, and administered according to an approved, role-based scheme so that elevated access is deliberate and accountable. It applies to all systems with privileged accounts. The minimum expected outcome is a governed set of privileged accounts with defined roles. Verification is by reviewing the privileged-account register and role assignments.',
            'objective_en': 'Ensure privileged accounts exist only under deliberate, accountable administration.',
            'type': 'ART-CTR', 'abstraction_level': 'ABS-CTR', 'primary_domain': 'SD-03', 'sub_domain': 'SD-03.04',
            'obligation_level': 'OBL-MND', 'classification_confidence': 0.85,
            'classification_rationale': 'AC-2(7) privileged account administration; SD-03.04.',
            'verification_method_note': 'Review privileged-account register and role assignments.',
            'missing_fields': ['control_nature', 'control_function', 'testability'],
        },
        'source_mappings': [(f'{NP}::0008', 'DIRECT', None)],
    },
    {
        'candidate_group_id': 'PA-02', 'concept_name': 'Restrict Privileged Access Scope', 'expected_sub_domain': 'SD-03.04',
        'members': [
            (f'{NP}::0070', 'NIST AC-6(5) — restrict privileged accounts to authorized personnel only.'),
            (f'{NP}::0071', 'NIST AC-6(6) — prohibit privileged access by non-organizational users.'),
        ],
        'excluded': [
            (f'{NP}::0065', 'AC-6 general least privilege belongs to SD-03.03 (Authorization), not PAM.'),
            ('enterprise_infrastructure_benchmarks::0001', 'AD-02 is a Domain-Admin tiering CONFIG (ART-CFG) — must not merge control with configuration (PA-07).'),
        ],
        'differences': 'Both restrict WHO may hold/use privileged accounts; same atomic idea (minimize the privileged population). Distinct from general least privilege (SD-03.03).',
        'decision': 'CANONICALIZE', 'decision_confidence': 0.85, 'requires_human_review': 0,
        'decision_rationale': 'AC-6(5) and AC-6(6) both restrict the privileged-account population; merged as one PAM control.',
        'canonical': {
            'title_en': 'Privileged Access Restriction', 'definition_short_en': 'This control restricts privileged accounts to explicitly authorized personnel and prohibits privileged access by non-organizational users.',
            'definition_full_en': 'This artifact requires that privileged access be granted only to explicitly authorized personnel and denied to non-organizational users, minimizing the privileged-account population. It applies to all systems with privileged accounts. The minimum expected outcome is a documented, enforced restriction of privileged access. Verification is by reviewing privileged-account holders against authorization records.',
            'objective_en': 'Minimize who can exercise privileged access.',
            'type': 'ART-CTR', 'abstraction_level': 'ABS-CTR', 'primary_domain': 'SD-03', 'sub_domain': 'SD-03.04',
            'obligation_level': 'OBL-MND', 'classification_confidence': 0.85,
            'classification_rationale': 'AC-6(5)/AC-6(6) restrict the privileged population; SD-03.04.',
            'verification_method_note': 'Review privileged-account holders vs authorization records.',
            'missing_fields': ['control_nature', 'control_function', 'testability'],
        },
        'source_mappings': [(f'{NP}::0070', 'DIRECT', None), (f'{NP}::0071', 'DIRECT', None)],
    },
    {
        'candidate_group_id': 'PA-03', 'concept_name': 'Separate Administrative and Regular Accounts', 'expected_sub_domain': 'SD-03.04',
        'members': [
            (f'{NP}::0067', 'NIST AC-6(2) — privileged users use non-privileged accounts for non-security functions.'),
            (f'{NP}::0075', 'NIST AC-6(10) — prevent non-privileged users from executing privileged functions.'),
        ],
        'excluded': [],
        'differences': 'AC-6(2) mandates a separate non-privileged account for routine work; AC-6(10) enforces the privilege boundary. Grouped as separation-of-privileged-use; AC-6(10) is boundary enforcement (INDIRECT), not an equal restatement.',
        'decision': 'EQUIVALENCE_GROUP', 'decision_confidence': 0.78, 'requires_human_review': 1,
        'decision_rationale': 'Same theme (separate privileged from routine use) but two distinct mechanisms; canonical = AC-6(2), AC-6(10) related (REL-SUP). Confidence 0.78 <= 0.80 -> human review.',
        'canonical': {
            'title_en': 'Separation of Administrative Accounts', 'definition_short_en': 'This control requires privileged users to perform non-administrative work with separate non-privileged accounts.',
            'definition_full_en': 'This artifact requires that individuals with privileged access use distinct non-privileged accounts for routine, non-administrative activity, so that day-to-day work does not occur under elevated privilege. It applies to all privileged users. The minimum expected outcome is that each privileged user has and uses a separate standard account for routine work. Verification is by sampling privileged users for separate-account usage.',
            'objective_en': 'Keep routine activity off privileged accounts.',
            'type': 'ART-CTR', 'abstraction_level': 'ABS-CTR', 'primary_domain': 'SD-03', 'sub_domain': 'SD-03.04',
            'obligation_level': 'OBL-MND', 'classification_confidence': 0.78,
            'classification_rationale': 'AC-6(2) separate administrative account; AC-6(10) boundary enforcement related; SD-03.04.',
            'verification_method_note': 'Sample privileged users for separate-account usage.',
            'missing_fields': ['control_nature', 'control_function', 'testability'],
        },
        'source_mappings': [(f'{NP}::0067', 'DIRECT', None),
                            (f'{NP}::0075', 'INDIRECT', 'Privilege-boundary enforcement supports separation (REL-SUP), not an equal restatement.')],
    },
    {
        'candidate_group_id': 'PA-04', 'concept_name': 'Multi-Factor Authentication for Privileged Accounts', 'expected_sub_domain': 'SD-03.04',
        'members': [
            (f'{NP}::0389', 'NIST IA-2(1) — MFA for access to privileged accounts.'),
            ('nca_ecc_1_2018::0009', 'NCA 2-2-3 — MFA for remote access AND all privileged accounts.'),
        ],
        'excluded': [
            (f'{NP}::0390', 'IA-2(2) MFA for NON-privileged accounts — SD-03.02, not PAM.'),
            ('cis_controls_v8::0012', 'CIS 6.5 MFA for administrative access — general authentication (SD-03.02).'),
        ],
        'differences': 'MFA specifically protecting privileged accounts. Boundary with SD-03.02 (Authentication) is genuine; NCA 2-2-3 also covers remote access (partial).',
        'decision': 'CANONICALIZE', 'decision_confidence': 0.68, 'requires_human_review': 1,
        'decision_rationale': 'MFA-for-privileged is a recognized PAM control, but the mechanism is authentication (SD-03.02). Confidence 0.68 -> human review to confirm SD-03.04 vs SD-03.02 placement.',
        'canonical': {
            'title_en': 'Multi-Factor Authentication for Privileged Access', 'definition_short_en': 'This control requires multi-factor authentication for all access to privileged accounts.',
            'definition_full_en': 'This artifact requires that access to privileged (administrative) accounts always use multi-factor authentication, raising the assurance of elevated access. It applies to all privileged accounts and interfaces. The minimum expected outcome is enforced MFA on every privileged authentication path. Verification is by testing privileged logon paths for MFA enforcement.',
            'objective_en': 'Ensure privileged access is protected by strong authentication.',
            'type': 'ART-CTR', 'abstraction_level': 'ABS-CTR', 'primary_domain': 'SD-03', 'sub_domain': 'SD-03.04',
            'obligation_level': 'OBL-MND', 'classification_confidence': 0.68,
            'classification_rationale': 'IA-2(1) MFA for privileged accounts; placed in SD-03.04 pending review vs SD-03.02.',
            'verification_method_note': 'Test privileged logon paths for MFA enforcement.',
            'missing_fields': ['control_nature', 'control_function', 'testability'],
        },
        'source_mappings': [(f'{NP}::0389', 'DIRECT', None),
                            ('nca_ecc_1_2018::0009', 'PARTIAL', 'NCA 2-2-3 also covers remote access; only its privileged-account clause applies here.')],
    },
    {
        'candidate_group_id': 'PA-05', 'concept_name': 'Monitor Privileged Activity', 'expected_sub_domain': 'SD-03.04',
        'members': [
            (f'{NP}::0590', 'NIST SI-4(20) — additional monitoring of privileged users.'),
        ],
        'excluded': [
            (f'{NP}::0203', 'AU-9(4) protects audit-log management access — audit protection (SD-06.01), not privileged-user monitoring.'),
        ],
        'differences': 'Monitoring the activity of privileged users specifically. Boundary with SD-06.01 (Logging & Monitoring) is genuine.',
        'decision': 'CANONICALIZE', 'decision_confidence': 0.7, 'requires_human_review': 1,
        'decision_rationale': 'Privileged-user activity monitoring; single source. Confidence 0.7 -> review (SD-03.04 vs SD-06.01 boundary).',
        'canonical': {
            'title_en': 'Privileged Activity Monitoring', 'definition_short_en': 'This control requires additional monitoring of the activities performed by privileged users.',
            'definition_full_en': 'This artifact requires enhanced monitoring of privileged-user activity so that misuse of elevated access can be detected. It applies to all privileged users and sessions. The minimum expected outcome is recorded, reviewable privileged-activity monitoring. Verification is by reviewing privileged-activity monitoring records.',
            'objective_en': 'Detect misuse of privileged access.',
            'type': 'ART-CTR', 'abstraction_level': 'ABS-CTR', 'primary_domain': 'SD-03', 'sub_domain': 'SD-03.04',
            'obligation_level': 'OBL-MND', 'classification_confidence': 0.7,
            'classification_rationale': 'SI-4(20) privileged-user monitoring; SD-03.04 pending review vs SD-06.01.',
            'verification_method_note': 'Review privileged-activity monitoring records.',
            'missing_fields': ['control_nature', 'control_function', 'testability'],
        },
        'source_mappings': [(f'{NP}::0590', 'DIRECT', None)],
    },
    {
        'candidate_group_id': 'PA-06', 'concept_name': 'Dedicated Privileged Access Interface', 'expected_sub_domain': 'SD-03.04',
        'members': [
            (f'{NP}::0421', 'NIST SC-7(15) — route privileged accesses through a dedicated, managed interface for access control and auditing.'),
        ],
        'excluded': [],
        'differences': 'A jump-host / dedicated interface for privileged access. Boundary with SD-04.01 (Network) is genuine but the purpose is privileged access mediation.',
        'decision': 'CANONICALIZE', 'decision_confidence': 0.72, 'requires_human_review': 1,
        'decision_rationale': 'Dedicated privileged-access interface (jump host); single source. Confidence 0.72 -> review (SD-03.04 vs SD-04.01).',
        'canonical': {
            'title_en': 'Dedicated Privileged Access Path', 'definition_short_en': 'This control requires privileged access to be routed through a dedicated, managed interface for access control and auditing.',
            'definition_full_en': 'This artifact requires that privileged network access pass through a dedicated, managed interface (such as a jump host or bastion) so that it can be controlled and audited centrally. It applies to networked privileged access. The minimum expected outcome is that privileged access cannot bypass the managed interface. Verification is by testing that privileged paths traverse the dedicated interface.',
            'objective_en': 'Mediate and audit all privileged access through a controlled path.',
            'type': 'ART-CTR', 'abstraction_level': 'ABS-CTR', 'primary_domain': 'SD-03', 'sub_domain': 'SD-03.04',
            'obligation_level': 'OBL-MND', 'classification_confidence': 0.72,
            'classification_rationale': 'SC-7(15) dedicated privileged-access interface; SD-03.04 pending review vs SD-04.01.',
            'verification_method_note': 'Test that privileged paths traverse the dedicated interface.',
            'missing_fields': ['control_nature', 'control_function', 'testability'],
        },
        'source_mappings': [(f'{NP}::0421', 'DIRECT', None)],
    },
    {
        'candidate_group_id': 'PA-07', 'concept_name': 'Domain Admin Tiering (Configuration)', 'expected_sub_domain': 'SD-03.04',
        'members': [
            ('enterprise_infrastructure_benchmarks::0001', 'AD-02 — restrict Domain Admin accounts to Domain Controllers; use tiering to prevent lateral movement.'),
        ],
        'excluded': [
            (f'{NP}::0070', 'AC-6(5) is a general privileged-restriction CONTROL (PA-02); AD-02 is a concrete AD CONFIG — must not merge control with config.'),
        ],
        'differences': 'A concrete technical configuration (AD tiering), type ART-CFG — kept separate from the control PA-02 per the forbidden control/config merge.',
        'decision': 'CANONICALIZE', 'decision_confidence': 0.75, 'requires_human_review': 1,
        'decision_rationale': 'Concrete AD tiering configuration (ART-CFG); single source. Confidence 0.75 -> review. Relates to PA-02 but is not merged (config vs control).',
        'canonical': {
            'title_en': 'Domain Admin Account Tiering', 'definition_short_en': 'This configuration restricts Domain Admin accounts to Domain Controllers and applies an administrative tiering model to prevent lateral movement.',
            'definition_full_en': 'This artifact requires configuring Active Directory so that Domain Admin accounts are usable only on Domain Controllers, with an administrative tier model that prevents high-tier credentials from being exposed on lower-tier systems. It applies to AD environments. The minimum expected outcome is enforced tier isolation for Domain Admin accounts. Verification is by testing that Domain Admin credentials cannot authenticate to lower-tier systems.',
            'objective_en': 'Prevent exposure and lateral movement of Domain Admin credentials.',
            'type': 'ART-CFG', 'abstraction_level': 'ABS-TEC', 'primary_domain': 'SD-03', 'sub_domain': 'SD-03.04',
            'obligation_level': 'OBL-REC', 'classification_confidence': 0.75,
            'classification_rationale': 'AD-02 Domain Admin tiering configuration; SD-03.04; ART-CFG (config), related to PA-02.',
            'verification_method_note': 'Test that Domain Admin credentials cannot authenticate to lower-tier systems.',
            'missing_fields': [],
        },
        'source_mappings': [('enterprise_infrastructure_benchmarks::0001', 'DIRECT', None)],
    },
]

UNCLASSIFIED = [
    (f'{NP}::0065', 'AC-6 general least privilege', 'General authorization principle -> SD-03.03, not PAM.'),
    ('nca_ecc_1_2018::0007', 'NCA 2-2-1 least privilege / need-to-know', 'General authorization -> SD-03.03.'),
    ('the_nist_cybersecurity_framework_csf_2_0::0056', 'CSF PR.AA-05 least privilege & SoD', 'General access policy -> SD-03.03.'),
    (f'{NP}::0389 (non-priv variants IA-2(2..9))', 'MFA for non-privileged accounts', 'Authentication for non-privileged -> SD-03.02.'),
    ('mitre_att_ck_enterprise::0098 / ::0142', 'Credential theft techniques', 'Threats (ART-THR) -> SD-06.05, not controls.'),
    (f'{NP}::0203', 'AU-9(4) audit management access', 'Audit-log protection -> SD-06.01.'),
    (f'{NP}::1084 / ::1172 / ::1192', 'SA-8/SA-17/SC-2 design-time least privilege', 'Secure development -> SD-05.x.'),
]


def count_mandatory_verbs(text):
    return len(re.findall(r'\b(shall|must|require[sd]?|establish|administer|restrict|prohibit|monitor|route|separate)\b', (text or '').lower()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', default=os.path.join(ROOT, 'pilot.db'))
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()
    if not os.path.exists(args.db):
        print("DB not found. Run ingest_raw.py --db pilot.db"); sys.exit(1)
    conn = sqlite3.connect(args.db); conn.execute("PRAGMA foreign_keys=ON")
    v = P.load_valid(conn)
    os.makedirs(OUT, exist_ok=True)

    # referenced raw ids must exist
    ids = {rid for g in GROUPS for rid, _ in g['members']}
    missing = [i for i in ids if not conn.execute("SELECT 1 FROM raw_artifacts WHERE id=?", (i,)).fetchone()]
    if missing:
        print("MISSING raw ids:", missing); sys.exit(1)

    index, dist, errors, applied = [], {}, [], 0
    for g in GROUPS:
        errs = P.validate_mappings(v, g)
        if g['canonical']:
            errs += P.validate_canonical(v, g['canonical'])
        # PAM rules
        if len(g['members']) > MAX_GROUP:
            errs.append(f"group >{MAX_GROUP} must be split")
        if g['decision_confidence'] <= REVIEW_THRESHOLD and not g['requires_human_review']:
            errs.append("confidence <= 0.80 must require human review")
        if g['canonical'] and g['canonical']['sub_domain'] != 'SD-03.04':
            errs.append("PAM pilot: sub_domain must be SD-03.04")
        if g['canonical'] and count_mandatory_verbs(g['canonical']['definition_short_en']) > 2:
            errs.append("canonical short definition has too many mandatory verbs (must be atomic)")
        if errs:
            errors.append((g['candidate_group_id'], errs))

        packet = {
            'candidate_group_id': g['candidate_group_id'], 'concept_name': g['concept_name'],
            'expected_sub_domain': g['expected_sub_domain'],
            'member_raw_ids': [m[0] for m in g['members']], 'excluded_raw_ids': [x[0] for x in g['excluded']],
            'member_reasons': {m[0]: m[1] for m in g['members']}, 'exclusion_reasons': {x[0]: x[1] for x in g['excluded']},
            'differences': g['differences'], 'decision': g['decision'],
            'decision_confidence': g['decision_confidence'], 'requires_human_review': g['requires_human_review'],
            'decision_rationale': g['decision_rationale'], 'canonical_artifact': g['canonical'],
            'source_mappings': [P.lineage(conn, rid, s, rat) for rid, s, rat in g['source_mappings']],
            'validation': 'OK' if not errs else errs,
        }
        io.open(os.path.join(OUT, f"{g['candidate_group_id']}.json"), 'w', encoding='utf-8').write(
            json.dumps(packet, ensure_ascii=False, indent=2))
        index.append({'id': g['candidate_group_id'], 'concept': g['concept_name'], 'sub_domain': g['expected_sub_domain'],
                      'members': len(g['members']), 'excluded': len(g['excluded']), 'decision': g['decision'],
                      'confidence': g['decision_confidence'], 'requires_human_review': g['requires_human_review']})
        dist[g['decision']] = dist.get(g['decision'], 0) + 1

        if args.apply and g['canonical'] and not errs:
            c = g['canonical']; grp = f"EG-{g['candidate_group_id']}"; stg = f"STG-CANON-{g['candidate_group_id']}"
            status = 'NEEDS_REVIEW' if (g['requires_human_review'] or c['classification_confidence'] <= 0.70) else 'READY'
            conn.execute("INSERT OR IGNORE INTO equivalence_groups (id,label,concept_domain) VALUES (?,?,?)", (grp, c['title_en'], c['primary_domain']))
            conn.execute("""INSERT INTO staging_artifacts
                (id,title_en,definition_short_en,definition_full_en,objective_en,proposed_type,proposed_abstraction_level,
                 proposed_primary_domain,proposed_sub_domain,proposed_obligation_level,classification_confidence,
                 classification_rationale,requires_human_review,proposed_mappings_json,canonical_group_id,merge_action,
                 curation_status,quality_score) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET title_en=excluded.title_en,definition_short_en=excluded.definition_short_en,
                 definition_full_en=excluded.definition_full_en,objective_en=excluded.objective_en,proposed_type=excluded.proposed_type,
                 proposed_abstraction_level=excluded.proposed_abstraction_level,proposed_primary_domain=excluded.proposed_primary_domain,
                 proposed_sub_domain=excluded.proposed_sub_domain,proposed_obligation_level=excluded.proposed_obligation_level,
                 classification_confidence=excluded.classification_confidence,classification_rationale=excluded.classification_rationale,
                 requires_human_review=excluded.requires_human_review,proposed_mappings_json=excluded.proposed_mappings_json,
                 canonical_group_id=excluded.canonical_group_id,merge_action=excluded.merge_action,
                 curation_status=excluded.curation_status,quality_score=excluded.quality_score,updated_at=datetime('now')""",
                (stg, c['title_en'], c['definition_short_en'], c['definition_full_en'], c['objective_en'], c['type'],
                 c['abstraction_level'], c['primary_domain'], c['sub_domain'], c['obligation_level'], c['classification_confidence'],
                 c['classification_rationale'], 1 if status == 'NEEDS_REVIEW' else 0,
                 json.dumps(packet['source_mappings'], ensure_ascii=False), grp, g['decision'], status, 88))
            applied += 1

    io.open(os.path.join(OUT, 'index.json'), 'w', encoding='utf-8').write(json.dumps(index, ensure_ascii=False, indent=2))
    io.open(os.path.join(OUT, 'unclassified.json'), 'w', encoding='utf-8').write(
        json.dumps([{'raw_id': r, 'label': l, 'reason': w} for r, l, w in UNCLASSIFIED], ensure_ascii=False, indent=2))
    if args.apply:
        conn.commit()

    review_n = sum(1 for g in GROUPS if g['requires_human_review'])
    print("=" * 60)
    print("PRIVILEGED ACCESS PILOT (SD-03.04 only)")
    print("=" * 60)
    print(f"atomic groups: {len(GROUPS)} | members: {sum(len(g['members']) for g in GROUPS)} | excluded near-misses: {sum(len(g['excluded']) for g in GROUPS)}")
    print(f"decision distribution: {dist}")
    print(f"requires human review (conf<=0.80): {review_n}/{len(GROUPS)}")
    print(f"validation errors: {len(errors)}")
    for gid, es in errors:
        print("  -", gid, es)
    print(f"canonicals {'APPLIED' if args.apply else 'validated (dry-run)'}: {applied}")
    print(f"catalog writes: 0 | raw writes: 0 | outputs: {OUT}")
    if errors:
        sys.exit(1)


if __name__ == '__main__':
    main()
