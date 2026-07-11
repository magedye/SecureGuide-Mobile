# -*- coding: utf-8 -*-
"""Writes the Asset Inventory Golden Dataset fixtures (authored expected results)
to tests/fixtures/golden/asset_inventory/. These are the source-of-truth
expectations that scripts/validate_golden.py checks the pilot output against."""
import io
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
GOLD = os.path.join(ROOT, 'tests', 'fixtures', 'golden', 'asset_inventory')
NP = 'nist_sp_800_53_rev_5_security_and_privacy_controls_for_information_systems_and_organizations'

CASES = [
    {'id': 'G01', 'case_type': 'CANONICALIZE_correct', 'maps_to_group': 'AI-01',
     'description': 'Three sources expressing the same asset-inventory requirement merge into one canonical.',
     'input_raw_ids': ['cis_controls_v8::0000', 'nca_ecc_1_2018::0005', f'{NP}::0309'],
     'expected_decision': 'CANONICALIZE', 'accepted_members': ['cis_controls_v8::0000', 'nca_ecc_1_2018::0005', f'{NP}::0309'],
     'excluded': [], 'expected_classification': {'type': 'ART-REQ', 'primary_domain': 'SD-02', 'sub_domain': 'SD-02.01'},
     'expected_rationale_keywords': ['inventory'], 'expected_canonical_title': 'Enterprise Asset Inventory',
     'validation_rules': ['sub_domain belongs to primary_domain', 'all source mappings DIRECT', '>=2 sources']},

    {'id': 'G02', 'case_type': 'EQUIVALENCE_GROUP_correct', 'maps_to_group': 'AI-08',
     'description': 'Acceptable-use policy define+implement grouped as equivalence, canonical=policy.',
     'input_raw_ids': ['essential_cybersecurity_controls_ecc_2_2024::0037', 'essential_cybersecurity_controls_ecc_2_2024::0038'],
     'expected_decision': 'EQUIVALENCE_GROUP', 'accepted_members': ['essential_cybersecurity_controls_ecc_2_2024::0037', 'essential_cybersecurity_controls_ecc_2_2024::0038'],
     'excluded': ['cis_controls_v8::0000'], 'expected_classification': {'type': 'ART-POL', 'primary_domain': 'SD-08', 'sub_domain': 'SD-08.05'},
     'expected_rationale_keywords': ['acceptable use'], 'expected_canonical_title': 'Acceptable Use of Assets Policy',
     'validation_rules': ['acceptable-use in SD-08.05 not SD-02.01', 'implementation mapped INDIRECT with rationale']},

    {'id': 'G03', 'case_type': 'RELATE_ONLY_correct', 'maps_to_group': 'AI-04',
     'description': 'CM-8 content/repository enhancements relate to the base inventory, not merged.',
     'input_raw_ids': [f'{NP}::0315', f'{NP}::0316'],
     'expected_decision': 'RELATE_ONLY', 'accepted_members': [f'{NP}::0315', f'{NP}::0316'],
     'excluded': [], 'expected_classification': None,
     'expected_rationale_keywords': ['relate', 'enhancement'], 'expected_canonical_title': None,
     'validation_rules': ['no canonical produced', 'mappings INDIRECT with rationale']},

    {'id': 'G04', 'case_type': 'verbal_similarity_reject', 'maps_to_group': 'AI-01',
     'description': 'Account inventory (CIS 5.1) shares the word "inventory" but MUST NOT merge with asset inventory.',
     'input_raw_ids': ['cis_controls_v8::0000', 'cis_controls_v8::0007'],
     'expected_decision': 'CANONICALIZE', 'accepted_members': ['cis_controls_v8::0000'],
     'excluded': ['cis_controls_v8::0007'], 'expected_classification': {'type': 'ART-REQ', 'primary_domain': 'SD-02', 'sub_domain': 'SD-02.01'},
     'expected_rationale_keywords': ['account'], 'expected_canonical_title': 'Enterprise Asset Inventory',
     'validation_rules': ['cis::0007 must be excluded, not a member', 'account inventory belongs to SD-03']},

    {'id': 'G05', 'case_type': 'requirement_vs_procedure', 'maps_to_group': 'AI-09',
     'description': 'ECC identify(req) / implement(procedure) must not merge into one artifact.',
     'input_raw_ids': ['essential_cybersecurity_controls_ecc_2_2024::0035', 'essential_cybersecurity_controls_ecc_2_2024::0036', 'essential_cybersecurity_controls_ecc_2_2024::0040'],
     'expected_decision': 'EQUIVALENCE_GROUP', 'accepted_members': ['essential_cybersecurity_controls_ecc_2_2024::0035', 'essential_cybersecurity_controls_ecc_2_2024::0036', 'essential_cybersecurity_controls_ecc_2_2024::0040'],
     'excluded': ['cis_controls_v8::0000'], 'expected_classification': {'type': 'ART-REQ', 'primary_domain': 'SD-02', 'sub_domain': 'SD-02.01'},
     'expected_rationale_keywords': ['implement', 'review'], 'expected_canonical_title': 'Asset Management Program Requirements',
     'validation_rules': ['implement/review mapped INDIRECT not merged', 'canonical is the requirement stage']},

    {'id': 'G06', 'case_type': 'inventory_vs_classification', 'maps_to_group': 'AI-07',
     'description': 'Asset classification is a distinct concept in SD-02.03, not asset inventory (SD-02.01).',
     'input_raw_ids': ['nca_ecc_1_2018::0006', 'essential_cybersecurity_controls_ecc_2_2024::0039'],
     'expected_decision': 'CANONICALIZE', 'accepted_members': ['nca_ecc_1_2018::0006', 'essential_cybersecurity_controls_ecc_2_2024::0039'],
     'excluded': ['cis_controls_v8::0000'], 'expected_classification': {'type': 'ART-REQ', 'primary_domain': 'SD-02', 'sub_domain': 'SD-02.03'},
     'expected_rationale_keywords': ['classif'], 'expected_canonical_title': 'Asset Classification & Labeling',
     'validation_rules': ['sub_domain == SD-02.03 (NOT SD-02.01)', 'inventory item excluded']},

    {'id': 'G07', 'case_type': 'inventory_vs_acceptable_use', 'maps_to_group': 'AI-08',
     'description': 'Acceptable use is SD-08.05, must not be grouped with inventory.',
     'input_raw_ids': ['essential_cybersecurity_controls_ecc_2_2024::0037', 'cis_controls_v8::0000'],
     'expected_decision': 'EQUIVALENCE_GROUP', 'accepted_members': ['essential_cybersecurity_controls_ecc_2_2024::0037'],
     'excluded': ['cis_controls_v8::0000'], 'expected_classification': {'type': 'ART-POL', 'primary_domain': 'SD-08', 'sub_domain': 'SD-08.05'},
     'expected_rationale_keywords': ['acceptable use'], 'expected_canonical_title': 'Acceptable Use of Assets Policy',
     'validation_rules': ['acceptable-use sub_domain != SD-02.01', 'inventory item excluded']},

    {'id': 'G08', 'case_type': 'low_confidence', 'maps_to_group': 'AI-09',
     'description': 'Governance-vs-control boundary is uncertain; confidence <= 0.80 must require human review.',
     'input_raw_ids': ['essential_cybersecurity_controls_ecc_2_2024::0035'],
     'expected_decision': 'EQUIVALENCE_GROUP', 'accepted_members': None,
     'excluded': [], 'expected_classification': {'type': 'ART-REQ', 'primary_domain': 'SD-02', 'sub_domain': 'SD-02.01'},
     'expected_rationale_keywords': ['governance'], 'expected_canonical_title': 'Asset Management Program Requirements',
     'validation_rules': ['decision_confidence <= 0.80', 'requires_human_review == 1', 'review_status in {APPROVED_WITH_CHANGES}']},

    {'id': 'G09', 'case_type': 'needs_split', 'maps_to_group': 'AI-04',
     'description': 'A group holding two distinct ideas (content + repository) must be flagged SPLIT_REQUIRED.',
     'input_raw_ids': [f'{NP}::0315', f'{NP}::0316'],
     'expected_decision': 'RELATE_ONLY', 'accepted_members': None,
     'excluded': [], 'expected_classification': None,
     'expected_rationale_keywords': ['split'], 'expected_canonical_title': None,
     'validation_rules': ['review_status == SPLIT_REQUIRED']},

    {'id': 'G10', 'case_type': 'indirect_mapping_with_rationale', 'maps_to_group': 'AI-08',
     'description': 'A non-DIRECT mapping (implementation of a policy) must carry a rationale.',
     'input_raw_ids': ['essential_cybersecurity_controls_ecc_2_2024::0038'],
     'expected_decision': 'EQUIVALENCE_GROUP', 'accepted_members': None,
     'excluded': [], 'expected_classification': {'type': 'ART-POL', 'primary_domain': 'SD-08', 'sub_domain': 'SD-08.05'},
     'expected_rationale_keywords': ['implementation'], 'expected_canonical_title': 'Acceptable Use of Assets Policy',
     'validation_rules': ['mapping for ecc::0038 is INDIRECT AND has non-empty rationale']},
]


def main():
    os.makedirs(GOLD, exist_ok=True)
    for c in CASES:
        io.open(os.path.join(GOLD, f"{c['id']}.json"), 'w', encoding='utf-8').write(
            json.dumps(c, ensure_ascii=False, indent=2))
    io.open(os.path.join(GOLD, 'index.json'), 'w', encoding='utf-8').write(
        json.dumps([{'id': c['id'], 'case_type': c['case_type'], 'maps_to_group': c['maps_to_group']} for c in CASES],
                   ensure_ascii=False, indent=2))
    print(f"wrote {len(CASES)} golden cases + index to {GOLD}")


if __name__ == '__main__':
    main()
