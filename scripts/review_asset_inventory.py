# -*- coding: utf-8 -*-
"""
review_asset_inventory.py — INDEPENDENT review layer over the Asset Inventory
Pilot decisions. This is a distinct reviewer pass (not the original agent's
decision): it re-checks atomicity, USACM type/abstraction, SDT validity,
forbidden merges, English drafting, lineage completeness, and mapping_strength
(including DIRECT). It writes a `review` block into each AI-*.json and emits
ASSET_INVENTORY_REVIEW_REPORT.md.

Reads/writes only consolidation/asset_inventory/*.json and the report.
Never touches raw_artifacts or security_artifacts.
"""
import io
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DIR = os.path.join(ROOT, 'consolidation', 'asset_inventory')

# Independent reviewer verdicts (keyed by candidate_group_id).
REVIEWS = {
    'AI-01': dict(
        review_status='APPROVED_WITH_CHANGES',
        reviewer_notes='Correct atomic inventory requirement merged from 3 sources. But the title/definition say "establish AND maintain", overlapping AI-02 (currency). NCA 2-1-1 is broader (explicitly includes software and data), while CIS 1.1 is device-centric.',
        validation_findings=['type/abstraction/SDT valid', 'sub-domain belongs to primary', 'lineage complete (3 DIRECT)'],
        required_changes=['Scope AI-01 to "establish and hold" the inventory; let AI-02 own "keep current".',
                          'Note NCA breadth (software/data) so software items are not double-counted vs AI-06.'],
        final_confidence=0.85, ready_for_promotion=False),
    'AI-02': dict(
        review_status='APPROVED',
        reviewer_notes='Atomic "keep inventory current/accurate" control from two CM-8 enhancements; clean scope, correctly related to AI-01.',
        validation_findings=['ART-CTR valid', 'both sources DIRECT and genuinely about currency', 'SD-02.01 correct'],
        required_changes=['On promotion fill control_nature/function/testability (already in missing_fields).'],
        final_confidence=0.85, ready_for_promotion=True),
    'AI-03': dict(
        review_status='REJECTED',
        reviewer_notes='CM-8(4) owner accountability is an ATTRIBUTE of the inventory (AI-01), not a standalone atomic requirement. Promoting it as a separate canonical would fragment the model.',
        validation_findings=['single source', 'semantically an attribute of AI-01'],
        required_changes=['Do NOT promote as standalone. Convert to RELATE_ONLY / fold "record accountable owner" as an attribute requirement of AI-01.'],
        final_confidence=0.5, ready_for_promotion=False),
    'AI-04': dict(
        review_status='SPLIT_REQUIRED',
        reviewer_notes='CM-8(6) (record configuration content) and CM-8(7) (central repository) are two DISTINCT enhancement ideas grouped together. RELATE_ONLY is right, but they must be split into two separate relationships to AI-01.',
        validation_findings=['correctly not merged', 'but group is not itself atomic (two ideas)'],
        required_changes=['Split into AI-04a (inventory content/config) and AI-04b (central repository); relate each to AI-01 separately.'],
        final_confidence=0.7, ready_for_promotion=False),
    'AI-05': dict(
        review_status='APPROVED',
        reviewer_notes='Distinct detective/corrective control for unauthorized assets; correctly separated from maintaining the inventory list.',
        validation_findings=['ART-CTR valid', 'DIRECT source genuinely about detection', 'SD-02.01 correct'],
        required_changes=['On promotion fill control fields.'],
        final_confidence=0.85, ready_for_promotion=True),
    'AI-06': dict(
        review_status='APPROVED',
        reviewer_notes='Software inventory correctly separated into SD-02.02, not merged with hardware/asset inventory. CIS 2.2 (supported software) correctly excluded.',
        validation_findings=['SD-02.02 correct (not SD-02.01)', 'DIRECT source genuinely software inventory'],
        required_changes=[],
        final_confidence=0.88, ready_for_promotion=True),
    'AI-07': dict(
        review_status='APPROVED_WITH_CHANGES',
        reviewer_notes='Classification/labeling correctly separated into SD-02.03. ECC 2-1-5 adds "handling" beyond classify/label — a scope difference that should not be silently dropped.',
        validation_findings=['SD-02.03 correct', 'both DIRECT but ECC includes handling scope'],
        required_changes=['Either widen canonical to include handling, or record a separate handling artifact and mark ECC 2-1-5 PARTIAL with rationale.'],
        final_confidence=0.8, ready_for_promotion=False),
    'AI-08': dict(
        review_status='APPROVED',
        reviewer_notes='Acceptable-use correctly placed in SD-08.05 (not asset inventory). Requirement/policy (2-1-3) vs implementation (2-1-4) correctly kept separate via EQUIVALENCE_GROUP with INDIRECT+rationale on the implementation.',
        validation_findings=['ART-POL valid', 'SD-08.05 correct', 'req/impl not merged', 'INDIRECT mapping has rationale'],
        required_changes=['On promotion set effective_date (in missing_fields).'],
        final_confidence=0.85, ready_for_promotion=True),
    'AI-09': dict(
        review_status='APPROVED_WITH_CHANGES',
        reviewer_notes='Governance lifecycle correctly kept separate from the concrete inventory control (different abstraction). Open question: SD-02.01 vs SD-01.02 (Policies/Standards) for a governance requirement.',
        validation_findings=['EQUIVALENCE_GROUP appropriate', 'INDIRECT stages have rationale', 'confidence 0.75 <= 0.80 -> human review'],
        required_changes=['Confirm SD-02.01 vs SD-01.02 for asset-management governance before promotion.'],
        final_confidence=0.72, ready_for_promotion=False),
    'AI-10': dict(
        review_status='APPROVED_WITH_CHANGES',
        reviewer_notes='ISO 8.10 is information/media DELETION (data end-of-life). SD-02.05 (Privacy, Retention & Disposal) is correct, but the title "Secure Information Disposal" should make clear it is information/media deletion, not physical asset disposal.',
        validation_findings=['SD-02.05 correct', 'single DIRECT source'],
        required_changes=['Clarify scope: information/media deletion; consider a separate physical media sanitization artifact if sources appear.'],
        final_confidence=0.78, ready_for_promotion=False),
}


def main():
    index = json.load(io.open(os.path.join(DIR, 'index.json'), encoding='utf-8'))
    rows = []
    dist = {}
    for gid, rv in REVIEWS.items():
        path = os.path.join(DIR, f"{gid}.json")
        pkt = json.load(io.open(path, encoding='utf-8'))
        pkt['review'] = rv                       # independent review block
        io.open(path, 'w', encoding='utf-8').write(json.dumps(pkt, ensure_ascii=False, indent=2))
        dist[rv['review_status']] = dist.get(rv['review_status'], 0) + 1
        rows.append((gid, pkt['concept_name'], pkt['decision'], rv['review_status'],
                     rv['final_confidence'], 'YES' if rv['ready_for_promotion'] else 'no'))

    # report
    ready = [r[0] for r in rows if r[5] == 'YES']
    md = []
    md.append('# ASSET_INVENTORY_REVIEW_REPORT')
    md.append('')
    md.append('> طبقة مراجعة **مستقلة** عن قرار الوكيل الأصلي، على مخرجات Asset Inventory Pilot.')
    md.append('> التاريخ: 2026-07-11 · المصدر: `consolidation/asset_inventory/AI-*.json` (أُضيف إليها بلوك `review`).')
    md.append('')
    md.append('## توزيع نتائج المراجعة')
    for k, v in sorted(dist.items()):
        md.append(f'- **{k}**: {v}')
    md.append('')
    md.append('## الجدول')
    md.append('| المجموعة | المفهوم | قرار الوكيل | نتيجة المراجعة | ثقة نهائية | جاهز للترقية |')
    md.append('|---|---|---|---|---|---|')
    for gid, concept, dec, rs, fc, ready_f in rows:
        md.append(f'| {gid} | {concept} | {dec} | **{rs}** | {fc} | {ready_f} |')
    md.append('')
    md.append('## القرارات الصريحة على الحديّتين (كما هو مطلوب)')
    md.append('- **AI-03** → **REJECTED** كعنصر مستقل: "مالك الأصل" خاصية ضمن AI-01، لا canonical مستقل. لا يُرقّى.')
    md.append('- **AI-09** → **APPROVED_WITH_CHANGES** ويبقى `NEEDS_REVIEW`: يُحسم SD-02.01 مقابل SD-01.02 قبل الترقية. لا يُرقّى الآن.')
    md.append('')
    md.append('## الجاهز للترقية (بعد استيفاء الحقول الناقصة على مستوى الكتالوج)')
    md.append(f'- {", ".join(ready) if ready else "لا يوجد"}  ({len(ready)}/10).')
    md.append('')
    md.append('## أبرز الملاحظات')
    md.append('- **ذرية:** AI-01 يتداخل مع AI-02 (establish+maintain)؛ AI-04 غير ذرّي (فكرتان) → SPLIT.')
    md.append('- **فروق نطاقية لم تُسقَط:** NCA 2-1-1 أوسع (يشمل البرمجيات/البيانات)؛ ECC 2-1-5 يضيف "handling".')
    md.append('- **قواعد المنع صحيحة:** فصل الجرد عن التصنيف (SD-02.03) وعن الاستخدام المقبول (SD-08.05) وعن البرمجيات (SD-02.02)، وفصل المتطلب عن التنفيذ (EQUIVALENCE_GROUP).')
    md.append('- **mapping_strength:** كل DIRECT خضع لتحقق دلالي؛ التحسينات (CM-8(6/7)) وتنفيذ ECC رُبطت INDIRECT مع rationale.')
    md.append('')
    md.append('## الخلاصة')
    md.append(f'{dist.get("APPROVED",0)} معتمدة مباشرة، {dist.get("APPROVED_WITH_CHANGES",0)} بتعديلات، '
              f'{dist.get("REJECTED",0)} مرفوضة، {dist.get("SPLIT_REQUIRED",0)} تحتاج تقسيماً. '
              'لا يُرقّى أي عنصر إلى `security_artifacts` في هذه المرحلة.')
    io.open(os.path.join(ROOT, 'ASSET_INVENTORY_REVIEW_REPORT.md'), 'w', encoding='utf-8').write('\n'.join(md))

    # standalone review record (survives pilot regeneration of AI-*.json)
    io.open(os.path.join(DIR, 'review.json'), 'w', encoding='utf-8').write(
        json.dumps(REVIEWS, ensure_ascii=False, indent=2))

    print(f"reviewed {len(rows)} groups. distribution: {dist}")
    print(f"ready_for_promotion: {ready}")
    print("wrote review blocks into AI-*.json + ASSET_INVENTORY_REVIEW_REPORT.md")


if __name__ == '__main__':
    main()
