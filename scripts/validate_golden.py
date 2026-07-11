# -*- coding: utf-8 -*-
"""
validate_golden.py — compares the ACTUAL Asset Inventory pilot output
(consolidation/asset_inventory/AI-*.json, incl. the independent review block)
against the Golden Dataset expectations (tests/fixtures/golden/asset_inventory/).

Fails if any run decision, classification, membership, exclusion, mapping, or
review flag diverges from the golden expectation.
"""
import io
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
GOLD = os.path.join(ROOT, 'tests', 'fixtures', 'golden', 'asset_inventory')
OUT = os.path.join(ROOT, 'consolidation', 'asset_inventory')
fails = []


def load(d, name):
    return json.load(io.open(os.path.join(d, name), encoding='utf-8'))


def check(case_id, name, cond):
    if not cond:
        fails.append(f"{case_id}: {name}")


def main():
    cases = load(GOLD, 'index.json')
    review = load(OUT, 'review.json')  # standalone review record (independent of pilot regen)
    for ci in cases:
        g = load(GOLD, f"{ci['id']}.json")
        grp = load(OUT, f"{g['maps_to_group']}.json")
        cid = g['id']

        # decision
        check(cid, f"decision == {g['expected_decision']}", grp['decision'] == g['expected_decision'])

        # membership / exclusion
        for rid in (g.get('accepted_members') or []):
            check(cid, f"member {rid} present", rid in grp['member_raw_ids'])
        for rid in g.get('excluded', []):
            # excluded means: NOT a member (it may be listed in excluded_raw_ids or simply absent)
            check(cid, f"excluded {rid} not a member", rid not in grp['member_raw_ids'])

        # classification
        ec = g.get('expected_classification')
        if ec is None:
            check(cid, "no canonical (RELATE_ONLY/none)", grp.get('canonical_artifact') in (None, {}))
        else:
            can = grp.get('canonical_artifact') or {}
            check(cid, f"type {ec['type']}", can.get('type') == ec['type'])
            check(cid, f"primary_domain {ec['primary_domain']}", can.get('primary_domain') == ec['primary_domain'])
            check(cid, f"sub_domain {ec['sub_domain']}", can.get('sub_domain') == ec['sub_domain'])
            check(cid, "sub belongs to primary", (can.get('sub_domain') or '')[:5] == can.get('primary_domain'))

        # canonical title
        if g.get('expected_canonical_title'):
            can = grp.get('canonical_artifact') or {}
            check(cid, "canonical title matches", can.get('title_en') == g['expected_canonical_title'])

        # case-type specific rules
        ct = g['case_type']
        if ct == 'low_confidence':
            check(cid, "confidence <= 0.80", grp['decision_confidence'] <= 0.80)
            check(cid, "requires_human_review", grp['requires_human_review'] == 1)
        if ct == 'needs_split':
            check(cid, "review SPLIT_REQUIRED", review.get(g['maps_to_group'], {}).get('review_status') == 'SPLIT_REQUIRED')
        if ct == 'indirect_mapping_with_rationale':
            target = g['input_raw_ids'][0]
            m = next((x for x in grp['source_mappings'] if x['raw_id'] == target), None)
            check(cid, "indirect mapping present", m is not None and m['mapping_strength'] != 'DIRECT')
            check(cid, "indirect mapping has rationale", bool(m and m.get('rationale')))
        if ct in ('inventory_vs_classification', 'inventory_vs_acceptable_use'):
            can = grp.get('canonical_artifact') or {}
            check(cid, "not placed in SD-02.01", can.get('sub_domain') != 'SD-02.01')
        if ct == 'requirement_vs_procedure':
            # implementation source must be INDIRECT (not merged as equal)
            impl = 'essential_cybersecurity_controls_ecc_2_2024::0036'
            m = next((x for x in grp['source_mappings'] if x['raw_id'] == impl), None)
            check(cid, "implementation mapped INDIRECT", m is not None and m['mapping_strength'] != 'DIRECT')

    print(f"golden cases checked: {len(cases)}")
    if fails:
        print("GOLDEN MISMATCHES:")
        for f in fails:
            print("  -", f)
        sys.exit(1)
    print("ALL GOLDEN CASES MATCH the pilot output.")


if __name__ == '__main__':
    main()
