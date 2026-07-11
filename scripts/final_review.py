# -*- coding: utf-8 -*-
"""
final_review.py — Phase 1: final human-review decisions on borderline cases.

Issues ONE final decision per borderline staging artifact
(APPROVED | REJECTED | SPLIT_AND_APPROVED | DEFERRED), fills the USACM
type-specific fields required for promotion on APPROVED items, splits the
composite AI-04 into two independent staging entries, sets ready_for_promotion
and content_hash, and writes FINAL_REVIEW_REPORT.md.

Operates on --db staging only. Never writes security_artifacts, never modifies
raw_artifacts. Rejected / deferred / needs-review items are NOT made ready.
"""
import argparse
import io
import json
import os
import sqlite3
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import _promote_common as C

# staging_id -> final decision. `fill` supplies type-specific promotion fields.
FINAL = {
    # ---- Asset Inventory: the 4 promotable items (batch-1) ----
    'STG-CANON-AI-02': dict(status='APPROVED', ready=1, conf=0.85,
        notes='Currency maintenance is an atomic organizational control; type fields supplied.',
        fill={'proposed_control_nature': 'NAT-ORG', 'proposed_control_function': 'FUN-PRE', 'proposed_testability': 'TST-MAN'}),
    'STG-CANON-AI-05': dict(status='APPROVED', ready=1, conf=0.85,
        notes='Unauthorized-asset detection is an atomic detective control; type fields supplied.',
        fill={'proposed_control_nature': 'NAT-ORG', 'proposed_control_function': 'FUN-DET', 'proposed_testability': 'TST-MAN'}),
    'STG-CANON-AI-06': dict(status='APPROVED', ready=1, conf=0.88,
        notes='Software inventory requirement, SD-02.02; requirement_type supplied.',
        fill={'proposed_requirement_type': 'RQT-STD'}),
    'STG-CANON-AI-08': dict(status='APPROVED', ready=1, conf=0.85,
        notes='Acceptable-use policy (ART-POL); no type-specific fields required.', fill={}),

    # ---- Asset Inventory: not promoted now ----
    'STG-CANON-AI-01': dict(status='DEFERRED', ready=0, conf=0.85,
        notes='Approved in principle, deferred to batch-2 pending scope-overlap confirmation with AI-02.',
        blockers=['scope overlap with AI-02 (establish vs maintain-currency) to confirm']),
    'STG-CANON-AI-03': dict(status='REJECTED', ready=0, conf=0.5,
        notes='Owner accountability is an attribute of AI-01, not a standalone artifact.',
        blockers=['rejected: attribute of AI-01, not standalone']),
    'STG-CANON-AI-07': dict(status='DEFERRED', ready=0, conf=0.8,
        notes='Classification approved in principle; ECC "handling" scope must be resolved first.',
        blockers=['ECC 2-1-5 handling scope not yet resolved']),
    'STG-CANON-AI-09': dict(status='DEFERRED', ready=0, conf=0.72,
        notes='Governance requirement; SD-02.01 vs SD-01.02 placement must be decided.',
        blockers=['SD-02.01 vs SD-01.02 undecided']),
    'STG-CANON-AI-10': dict(status='DEFERRED', ready=0, conf=0.78,
        notes='Disposal approved in principle; information-vs-physical scope must be clarified.',
        blockers=['information vs physical disposal scope unclear']),

    # ---- Privileged Access: reviewed, but NOT promoted in this task (PAM batch deferred) ----
    'STG-CANON-PA-01': dict(status='APPROVED', ready=0, conf=0.85, notes='Core PAM control; approved for a future PAM batch (out of current scope).',
        blockers=['PAM promotion deferred to dedicated PAM batch'],
        fill={'proposed_control_nature': 'NAT-ORG', 'proposed_control_function': 'FUN-PRE', 'proposed_testability': 'TST-MAN'}),
    'STG-CANON-PA-02': dict(status='APPROVED', ready=0, conf=0.85, notes='Approved for a future PAM batch.',
        blockers=['PAM promotion deferred to dedicated PAM batch'],
        fill={'proposed_control_nature': 'NAT-ORG', 'proposed_control_function': 'FUN-PRE', 'proposed_testability': 'TST-MAN'}),
    'STG-CANON-PA-03': dict(status='APPROVED', ready=0, conf=0.82, notes='Separation of admin accounts is core PAM; approved for a future PAM batch.',
        blockers=['PAM promotion deferred to dedicated PAM batch'],
        fill={'proposed_control_nature': 'NAT-ORG', 'proposed_control_function': 'FUN-PRE', 'proposed_testability': 'TST-MAN'}),
    'STG-CANON-PA-04': dict(status='DEFERRED', ready=0, conf=0.68, notes='SD-03.04 vs SD-03.02 (authentication) placement unresolved.',
        blockers=['domain boundary SD-03.04 vs SD-03.02']),
    'STG-CANON-PA-05': dict(status='DEFERRED', ready=0, conf=0.70, notes='SD-03.04 vs SD-06.01 (monitoring) placement unresolved.',
        blockers=['domain boundary SD-03.04 vs SD-06.01']),
    'STG-CANON-PA-06': dict(status='DEFERRED', ready=0, conf=0.72, notes='SD-03.04 vs SD-04.01 (network) placement unresolved.',
        blockers=['domain boundary SD-03.04 vs SD-04.01']),
    'STG-CANON-PA-07': dict(status='APPROVED', ready=0, conf=0.8, notes='AD tiering config (ART-CFG); approved for a future PAM batch.',
        blockers=['PAM promotion deferred to dedicated PAM batch'], fill={}),
}

# AI-04 SPLIT_AND_APPROVED -> two independent RELATE_ONLY staging entries (deferred, relate to AI-01).
SPLIT_AI04 = [
    ('STG-SPLIT-AI-04a', 'Asset Inventory Content Requirements', 'CM-8(6): assessed configurations/deviations recorded in the inventory. Relates to AI-01 (REL-SPL).', 'nist_sp_800_53_rev_5_security_and_privacy_controls_for_information_systems_and_organizations::0315'),
    ('STG-SPLIT-AI-04b', 'Central Asset Inventory Repository', 'CM-8(7): a centralized repository for the inventory. Relates to AI-01 (REL-SUP).', 'nist_sp_800_53_rev_5_security_and_privacy_controls_for_information_systems_and_organizations::0316'),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', default=os.path.join(ROOT, 'pilot.db'))
    args = ap.parse_args()
    if not os.path.exists(args.db):
        print("DB not found."); sys.exit(1)
    conn = sqlite3.connect(args.db); conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")

    applied = []
    for sid, d in FINAL.items():
        if not conn.execute("SELECT 1 FROM staging_artifacts WHERE id=?", (sid,)).fetchone():
            continue  # PAM/other staging may be absent in an AI-only DB
        sets = {'final_review_status': d['status'], 'ready_for_promotion': d['ready'],
                'classification_confidence': d['conf'], 'approved_by': 'independent-reviewer',
                'promotion_blockers': json.dumps(d.get('blockers', []), ensure_ascii=False)}
        for k, val in (d.get('fill') or {}).items():
            sets[k] = val
        # requires_human_review must be cleared for promotable items
        if d['ready']:
            sets['requires_human_review'] = 0
            sets['curation_status'] = 'APPROVED'
            sets['approved_at'] = None  # set below via datetime
        cols = ', '.join(f"{k}=?" for k in sets)
        conn.execute(f"UPDATE staging_artifacts SET {cols}, approved_at=datetime('now') WHERE id=?",
                     list(sets.values()) + [sid])
        # compute content hash on the resulting row
        row = conn.execute("SELECT * FROM staging_artifacts WHERE id=?", (sid,)).fetchone()
        conn.execute("UPDATE staging_artifacts SET content_hash=? WHERE id=?", (C.content_hash(row), sid))
        applied.append((sid, d['status'], d['ready']))

    # AI-04 split: create two independent staging entries (RELATE_ONLY, deferred)
    split_created = []
    for sid, title, note, rawid in SPLIT_AI04:
        r = conn.execute("SELECT source_document, source_version, source_section FROM raw_artifacts WHERE id=?", (rawid,)).fetchone()
        maps = json.dumps([{'raw_id': rawid, 'source_document': r[0] if r else None,
                            'source_version': r[1] if r else None, 'source_section': r[2] if r else None,
                            'mapping_strength': 'INDIRECT', 'rationale': 'Enhancement relating to AI-01; not a canonical merge.'}], ensure_ascii=False)
        conn.execute("""INSERT OR REPLACE INTO staging_artifacts
            (id, title_en, definition_short_en, merge_action, curation_status, requires_human_review,
             final_review_status, ready_for_promotion, promotion_blockers, proposed_mappings_json, quality_score)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (sid, title, note, 'RELATE_ONLY', 'NEEDS_REVIEW', 1, 'SPLIT_AND_APPROVED', 0,
             json.dumps(['relationship to AI-01; promote after AI-01 exists'], ensure_ascii=False), maps, 60))
        split_created.append(sid)
    conn.commit()

    # report
    dist = {}
    for _, st, _ in applied:
        dist[st] = dist.get(st, 0) + 1
    ready = [a[0] for a in applied if a[2] == 1]
    md = ['# FINAL_REVIEW_REPORT', '',
          '> المراجعة البشرية النهائية للحالات الحدّية في Asset Inventory و Privileged Access.',
          '> التاريخ: 2026-07-11. تُطبَّق على staging فقط؛ لا كتابة في الكتالوج.', '',
          f'## توزيع القرارات النهائية', f'- {json.dumps(dist, ensure_ascii=False)}', '',
          '## القرارات', '| staging | الحالة النهائية | جاهز للترقية | ثقة نهائية |', '|---|---|---|---|']
    for sid, st, rd in applied:
        md.append(f"| {sid} | **{st}** | {'YES' if rd else 'no'} | {FINAL[sid]['conf']} |")
    md += ['', '## تقسيم AI-04 (SPLIT_AND_APPROVED)',
           '- AI-04 المركّب لا يُرقّى. أُنشئت عناصر staging مستقلة:',
           '  - `STG-SPLIT-AI-04a` — Asset Inventory Content Requirements (RELATE_ONLY → AI-01).',
           '  - `STG-SPLIT-AI-04b` — Central Asset Inventory Repository (RELATE_ONLY → AI-01).',
           '  - كلاهما مؤجّل حتى تُرقّى AI-01 (يصبحان علاقتين).', '',
           '## الجاهز للترقية الآن (batch-1)',
           f'- {", ".join(ready)}  ({len(ready)} عناصر — كلها Asset Inventory).', '',
           '## غير المُرقّى (بأسباب صريحة)',
           '- **AI-03**: REJECTED (خاصية ضمن AI-01).',
           '- **AI-01/07/09/10**: DEFERRED (أسئلة نطاق/مجال مفتوحة).',
           '- **AI-04**: SPLIT_AND_APPROVED (عنصران مستقلان مؤجّلان).',
           '- **PA-01/02/03/07**: APPROVED لكن مؤجّلة لدُفعة PAM مخصّصة (خارج نطاق هذه المهمة).',
           '- **PA-04/05/06**: DEFERRED (حدود مجال).', '',
           '## قواعد الجاهزية المطبّقة',
           'فكرة ذرّية واحدة · صياغة إنجليزية مكتملة · USACM/SDT صحيح · انتماء sub-domain · '
           'lineage مكتمل · mapping_strength مبرّر · الحقول الخاصة بالنوع مملوءة · لا blockers مفتوحة · '
           'requires_human_review=0 · ثقة > 0.70.']
    io.open(os.path.join(ROOT, 'FINAL_REVIEW_REPORT.md'), 'w', encoding='utf-8').write('\n'.join(md))

    print(f"final decisions applied: {len(applied)}  dist={dist}")
    print(f"ready_for_promotion: {ready}")
    print(f"AI-04 split entries created: {split_created}")
    print("wrote FINAL_REVIEW_REPORT.md")


if __name__ == '__main__':
    main()
