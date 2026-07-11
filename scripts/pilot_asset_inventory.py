# -*- coding: utf-8 -*-
"""
pilot_asset_inventory.py — Asset Inventory consolidation Pilot (no embeddings).

Encodes the agent's ATOMIC grouping decisions for the Asset Inventory concept
(read from the real raw texts, split by meaning + abstraction + USACM type,
honoring the forbidden-merge rules), emits one JSON decision file per atomic
group + an index + an unclassified/conflicts list, validates every canonical
against the real lk_* lookup tables (USACM/SDT, sub-domain belongs-to), and
applies canonicals to staging only.

NEVER deletes/modifies raw_artifacts. NEVER writes security_artifacts.

Usage:
    python scripts/pilot_asset_inventory.py [--db pilot.db] [--apply]
"""
import argparse
import io
import json
import os
import sqlite3
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'consolidation', 'asset_inventory')
NP = 'nist_sp_800_53_rev_5_security_and_privacy_controls_for_information_systems_and_organizations'

# ---- Atomic groups (agent decisions, grounded in the actual source texts) ----
GROUPS = [
    {
        'candidate_group_id': 'AI-01',
        'concept_name': 'Establish & Maintain Asset Inventory',
        'expected_sub_domain': 'SD-02.01',
        'members': [
            ('cis_controls_v8::0000', 'CIS 1.1 — establish & maintain inventory of all enterprise assets (devices, network, IoT, servers).'),
            ('nca_ecc_1_2018::0005', 'NCA 2-1-1 — develop & maintain inventory of all information assets (hardware, software, data).'),
            (f'{NP}::0309', 'NIST CM-8 — develop & document a system component inventory that accurately reflects the system.'),
        ],
        'excluded': [
            ('cis_controls_v8::0007', 'CIS 5.1 = inventory of ACCOUNTS — belongs to SD-03.01, not asset inventory.'),
            ('cis_controls_v8::0025', 'CIS 15.1 = inventory of SERVICE PROVIDERS — belongs to SD-08.03.'),
            (f'{NP}::0310', 'CM-8(1) = keeping the inventory CURRENT — atomic concept "maintain currency" (AI-02).'),
            ('essential_cybersecurity_controls_ecc_2_2024::0035', 'ECC 2-1-1 = governance-level asset-management REQUIREMENT (different abstraction) — AI-09.'),
        ],
        'differences': 'All three require a complete, accurate, documented inventory of technology/information assets. Same purpose, USACM type (ART-REQ), and SDT sub-domain (SD-02.01).',
        'decision': 'CANONICALIZE',
        'decision_confidence': 0.9,
        'requires_human_review': 0,
        'decision_rationale': 'Three independent sources express the identical requirement to hold and maintain an asset inventory; unified into one SecureGuide artifact with source mappings.',
        'canonical': {
            'title_en': 'Enterprise Asset Inventory',
            'definition_short_en': 'This requirement establishes and maintains an accurate, current inventory of all enterprise information and technology assets that can store, process, or transmit organizational data.',
            'definition_full_en': 'This artifact requires the organization to build and maintain a complete, accurate inventory of information and technology assets — including end-user devices, servers, network devices, and IoT — recording enough detail to identify and govern each asset. It applies across all in-scope environments. The minimum expected outcome is a documented, regularly reconciled asset register. Verification is by inspecting the register and reconciling it against discovered assets.',
            'objective_en': 'Ensure every in-scope asset is known so it can be secured, monitored, and governed.',
            'type': 'ART-REQ', 'abstraction_level': 'ABS-CTR',
            'primary_domain': 'SD-02', 'sub_domain': 'SD-02.01', 'obligation_level': 'OBL-MND',
            'classification_confidence': 0.9,
            'classification_rationale': 'Core asset-inventory requirement shared by CIS 1.1, NCA 2-1-1, and NIST CM-8; single SDT sub-domain SD-02.01.',
            'verification_method_note': 'Inspect the asset register; reconcile against automated discovery.',
            'missing_fields': ['requirement_type'],
        },
        'source_mappings': [
            ('cis_controls_v8::0000', 'DIRECT', None),
            ('nca_ecc_1_2018::0005', 'DIRECT', None),
            (f'{NP}::0309', 'DIRECT', None),
        ],
    },
    {
        'candidate_group_id': 'AI-02',
        'concept_name': 'Maintain Asset Inventory Currency',
        'expected_sub_domain': 'SD-02.01',
        'members': [
            (f'{NP}::0310', 'CM-8(1) — update the inventory as part of component installs, removals, and updates.'),
            (f'{NP}::0311', 'CM-8(2) — maintain the currency, completeness, accuracy, and availability of the inventory.'),
        ],
        'excluded': [
            ('cis_controls_v8::0000', 'CIS 1.1 = ESTABLISH the inventory — the base requirement (AI-01), not the currency mechanism.'),
        ],
        'differences': 'Both CM-8 enhancements address keeping an existing inventory up to date and accurate — a control mechanism distinct from establishing the inventory.',
        'decision': 'CANONICALIZE',
        'decision_confidence': 0.85,
        'requires_human_review': 0,
        'decision_rationale': 'CM-8(1) and CM-8(2) are the same atomic idea (keep the inventory current & accurate); merged and related to AI-01 (REL-SPL).',
        'canonical': {
            'title_en': 'Asset Inventory Currency Maintenance',
            'definition_short_en': 'This control keeps the asset inventory current and accurate by updating it whenever assets are added, removed, or changed.',
            'definition_full_en': 'This artifact requires that the asset inventory be updated as part of every component installation, removal, and system change, and that its completeness, accuracy, and availability be maintained over time. It applies wherever an asset inventory is kept. The minimum expected outcome is an inventory that reflects the current asset estate with no stale or missing entries. Verification is by sampling recent asset changes and confirming corresponding inventory updates.',
            'objective_en': 'Keep the asset inventory an accurate, current reflection of the real environment.',
            'type': 'ART-CTR', 'abstraction_level': 'ABS-CTR',
            'primary_domain': 'SD-02', 'sub_domain': 'SD-02.01', 'obligation_level': 'OBL-MND',
            'classification_confidence': 0.85,
            'classification_rationale': 'Both sources are NIST CM-8 enhancements about inventory currency/accuracy; one SecureGuide control in SD-02.01, related to AI-01.',
            'verification_method_note': 'Sample recent asset changes; confirm inventory updated.',
            'missing_fields': ['control_nature', 'control_function', 'testability'],
        },
        'source_mappings': [
            (f'{NP}::0310', 'DIRECT', None),
            (f'{NP}::0311', 'DIRECT', None),
        ],
    },
    {
        'candidate_group_id': 'AI-03',
        'concept_name': 'Asset Ownership / Accountability in Inventory',
        'expected_sub_domain': 'SD-02.01',
        'members': [
            (f'{NP}::0313', 'CM-8(4) — record the individuals responsible/accountable for administering each component.'),
        ],
        'excluded': [
            ('essential_cybersecurity_controls_ecc_2_2024::0039', 'ECC 2-1-5 = classification/labeling of assets — different concept (AI-07).'),
        ],
        'differences': 'Assigning an accountable owner to each asset is distinct from merely listing assets; single source, borderline whether it is an attribute of AI-01.',
        'decision': 'CANONICALIZE',
        'decision_confidence': 0.6,
        'requires_human_review': 1,
        'decision_rationale': 'Single source (CM-8(4)); could be an attribute of AI-01 rather than a standalone artifact — routed to human review (confidence 0.6).',
        'canonical': {
            'title_en': 'Asset Ownership Accountability',
            'definition_short_en': 'This control records, for each asset in the inventory, the individual responsible and accountable for administering it.',
            'definition_full_en': 'This artifact requires the asset inventory to identify, for each component, the person or role accountable for its administration, so that ownership is unambiguous. It applies to every inventoried asset. The minimum expected outcome is an owner recorded against each asset. Verification is by sampling inventory entries for a named accountable owner.',
            'objective_en': 'Ensure every asset has a clearly accountable owner.',
            'type': 'ART-CTR', 'abstraction_level': 'ABS-CTR',
            'primary_domain': 'SD-02', 'sub_domain': 'SD-02.01', 'obligation_level': 'OBL-REC',
            'classification_confidence': 0.6,
            'classification_rationale': 'CM-8(4) owner accountability; kept in SD-02.01 but low confidence on standalone-vs-attribute — human review.',
            'verification_method_note': 'Sample inventory entries for a named owner.',
            'missing_fields': ['control_nature', 'control_function', 'testability'],
        },
        'source_mappings': [
            (f'{NP}::0313', 'DIRECT', None),
        ],
    },
    {
        'candidate_group_id': 'AI-04',
        'concept_name': 'Asset Inventory Content & Central Repository',
        'expected_sub_domain': 'SD-02.01',
        'members': [
            (f'{NP}::0315', 'CM-8(6) — include assessed configurations and approved deviations in the inventory.'),
            (f'{NP}::0316', 'CM-8(7) — provide a centralized repository for the inventory.'),
        ],
        'excluded': [],
        'differences': 'These specify inventory CONTENT (config data) and STORAGE (central repository); they enhance AI-01 but are not the same requirement, and are two different sub-ideas.',
        'decision': 'RELATE_ONLY',
        'decision_confidence': 0.7,
        'requires_human_review': 1,
        'decision_rationale': 'CM-8(6) and CM-8(7) are implementation enhancements that specify/support AI-01; they are related (REL-SPL/REL-SUP), not merged, and are not equivalent to each other — kept for catalog-level relationships after promotion.',
        'canonical': None,
        'source_mappings': [
            (f'{NP}::0315', 'INDIRECT', 'Enhancement specifying inventory content; relates to AI-01, not a merge.'),
            (f'{NP}::0316', 'INDIRECT', 'Enhancement specifying a central repository; relates to AI-01, not a merge.'),
        ],
    },
    {
        'candidate_group_id': 'AI-05',
        'concept_name': 'Detect & Remediate Unauthorized Assets',
        'expected_sub_domain': 'SD-02.01',
        'members': [
            ('cis_controls_v8::0001', 'CIS 1.2 — ensure a process exists to address unauthorized assets weekly.'),
        ],
        'excluded': [
            ('cis_controls_v8::0000', 'CIS 1.1 = maintain the inventory (AI-01); detection of unknown assets is a distinct control.'),
        ],
        'differences': 'Discovering and remediating unauthorized/unknown assets is a detective/corrective control, distinct from maintaining the inventory list.',
        'decision': 'CANONICALIZE',
        'decision_confidence': 0.8,
        'requires_human_review': 0,
        'decision_rationale': 'Single, clearly distinct control from one source; normalized into its own SecureGuide artifact in SD-02.01.',
        'canonical': {
            'title_en': 'Unauthorized Asset Detection',
            'definition_short_en': 'This control ensures a recurring process detects and addresses assets connected to the environment that are not in the approved inventory.',
            'definition_full_en': 'This artifact requires a regular (at least weekly) process to detect assets present in the environment but absent from the approved inventory, and to remediate them (remove, quarantine, or add with approval). It applies to all in-scope networks and environments. The minimum expected outcome is a scheduled unauthorized-asset review with recorded remediation. Verification is by reviewing detection runs and remediation records.',
            'objective_en': 'Prevent unknown or unauthorized assets from operating undetected.',
            'type': 'ART-CTR', 'abstraction_level': 'ABS-CTR',
            'primary_domain': 'SD-02', 'sub_domain': 'SD-02.01', 'obligation_level': 'OBL-MND',
            'classification_confidence': 0.8,
            'classification_rationale': 'CIS 1.2 detective/corrective control for unauthorized assets; SD-02.01.',
            'verification_method_note': 'Review detection runs and remediation records.',
            'missing_fields': ['control_nature', 'control_function', 'testability'],
        },
        'source_mappings': [
            ('cis_controls_v8::0001', 'DIRECT', None),
        ],
    },
    {
        'candidate_group_id': 'AI-06',
        'concept_name': 'Software Inventory',
        'expected_sub_domain': 'SD-02.02',
        'members': [
            ('cis_controls_v8::0002', 'CIS 2.1 — establish & maintain a detailed inventory of all licensed software on enterprise assets.'),
        ],
        'excluded': [
            ('cis_controls_v8::0003', 'CIS 2.2 = only supported software may be used — a software-currency control, not the inventory (relate, not merge).'),
            ('nca_ecc_1_2018::0005', 'NCA 2-1-1 folds software into the information-asset inventory (AI-01); the dedicated software inventory is kept separate per SDT SD-02.02.'),
        ],
        'differences': 'Software (licensed applications) inventory is a distinct SDT sub-domain (SD-02.02) and MUST NOT be merged with general/hardware asset inventory (SD-02.01).',
        'decision': 'CANONICALIZE',
        'decision_confidence': 0.88,
        'requires_human_review': 0,
        'decision_rationale': 'Distinct, well-scoped software-inventory requirement; kept separate from hardware/asset inventory as required.',
        'canonical': {
            'title_en': 'Software Inventory',
            'definition_short_en': 'This requirement establishes and maintains a detailed inventory of all licensed software installed on enterprise assets.',
            'definition_full_en': 'This artifact requires the organization to maintain an accurate, current inventory of licensed software installed across enterprise assets, including title, version, and license coverage. It applies to all managed endpoints and servers. The minimum expected outcome is a documented software inventory reconciled against installed software. Verification is by comparing the inventory with automated software discovery.',
            'objective_en': 'Know all software present so it can be licensed, supported, and secured.',
            'type': 'ART-REQ', 'abstraction_level': 'ABS-CTR',
            'primary_domain': 'SD-02', 'sub_domain': 'SD-02.02', 'obligation_level': 'OBL-MND',
            'classification_confidence': 0.88,
            'classification_rationale': 'CIS 2.1 software inventory; SDT SD-02.02 (Software & License Management), distinct from SD-02.01.',
            'verification_method_note': 'Compare inventory with automated software discovery.',
            'missing_fields': ['requirement_type'],
        },
        'source_mappings': [
            ('cis_controls_v8::0002', 'DIRECT', None),
        ],
    },
    {
        'candidate_group_id': 'AI-07',
        'concept_name': 'Asset Classification & Labeling',
        'expected_sub_domain': 'SD-02.03',
        'members': [
            ('nca_ecc_1_2018::0006', 'NCA 2-1-2 — classify information assets by criticality and sensitivity per an approved policy.'),
            ('essential_cybersecurity_controls_ecc_2_2024::0039', 'ECC 2-1-5 — assets shall be classified, labeled, and handled per requirements.'),
        ],
        'excluded': [
            ('cis_controls_v8::0000', 'CIS 1.1 = inventory (AI-01); classification is a distinct concept and MUST NOT be merged with inventory.'),
        ],
        'differences': 'Classifying and labeling assets by sensitivity is a distinct requirement (SD-02.03), separate from inventorying them (SD-02.01).',
        'decision': 'CANONICALIZE',
        'decision_confidence': 0.82,
        'requires_human_review': 0,
        'decision_rationale': 'Two sources express the same classify-and-label requirement; unified in SD-02.03, kept separate from inventory.',
        'canonical': {
            'title_en': 'Asset Classification & Labeling',
            'definition_short_en': 'This requirement classifies and labels information and technology assets by criticality and sensitivity according to an approved classification scheme.',
            'definition_full_en': 'This artifact requires assets to be classified by criticality and sensitivity and labeled accordingly, so that protection is applied proportionate to value. It applies to all information and technology assets. The minimum expected outcome is a classified, labeled asset set governed by an approved scheme. Verification is by sampling assets for correct classification and labels.',
            'objective_en': 'Apply protection proportionate to each asset\'s sensitivity and criticality.',
            'type': 'ART-REQ', 'abstraction_level': 'ABS-POL',
            'primary_domain': 'SD-02', 'sub_domain': 'SD-02.03', 'obligation_level': 'OBL-MND',
            'classification_confidence': 0.82,
            'classification_rationale': 'NCA 2-1-2 and ECC 2-1-5 both require asset classification/labeling; SDT SD-02.03 (Data Classification & Ownership).',
            'verification_method_note': 'Sample assets for correct classification and labels.',
            'missing_fields': ['requirement_type'],
        },
        'source_mappings': [
            ('nca_ecc_1_2018::0006', 'DIRECT', None),
            ('essential_cybersecurity_controls_ecc_2_2024::0039', 'DIRECT', None),
        ],
    },
    {
        'candidate_group_id': 'AI-08',
        'concept_name': 'Acceptable Use of Assets',
        'expected_sub_domain': 'SD-08.05',
        'members': [
            ('essential_cybersecurity_controls_ecc_2_2024::0037', 'ECC 2-1-3 — acceptable-use policy for assets identified, documented, approved, communicated.'),
            ('essential_cybersecurity_controls_ecc_2_2024::0038', 'ECC 2-1-4 — the acceptable-use policy is implemented.'),
        ],
        'excluded': [
            ('cis_controls_v8::0000', 'CIS 1.1 = inventory; acceptable-use policy MUST NOT be merged with an inventory requirement.'),
        ],
        'differences': '2-1-3 DEFINES the acceptable-use policy (a policy artifact); 2-1-4 IMPLEMENTS it (a procedure). Requirement/policy vs implementation must not be merged.',
        'decision': 'EQUIVALENCE_GROUP',
        'decision_confidence': 0.8,
        'requires_human_review': 0,
        'decision_rationale': 'Same subject (acceptable use) but different lifecycle stages (define vs implement); grouped with canonical = the policy (2-1-3), implementation (2-1-4) related via REL-IMP — not merged.',
        'canonical': {
            'title_en': 'Acceptable Use of Assets Policy',
            'definition_short_en': 'This policy defines the acceptable use of information and technology assets and is documented, approved, and communicated to users.',
            'definition_full_en': 'This artifact establishes an approved policy governing how users may use organizational information and technology assets, including prohibited actions and user responsibilities, and requires it to be communicated. It applies to all asset users. The minimum expected outcome is an approved, communicated acceptable-use policy. Verification is by confirming approval records and user acknowledgement.',
            'objective_en': 'Set clear, approved rules for how assets may be used.',
            'type': 'ART-POL', 'abstraction_level': 'ABS-POL',
            'primary_domain': 'SD-08', 'sub_domain': 'SD-08.05', 'obligation_level': 'OBL-MND',
            'classification_confidence': 0.8,
            'classification_rationale': 'Acceptable-use policy; SDT SD-08.05 (Acceptable Use & Professional Conduct), not asset inventory.',
            'verification_method_note': 'Confirm approval records and user acknowledgement.',
            'missing_fields': ['effective_date'],
        },
        'source_mappings': [
            ('essential_cybersecurity_controls_ecc_2_2024::0037', 'DIRECT', None),
            ('essential_cybersecurity_controls_ecc_2_2024::0038', 'INDIRECT', 'Implementation of the policy (REL-IMP), not an equivalent restatement.'),
        ],
    },
    {
        'candidate_group_id': 'AI-09',
        'concept_name': 'Asset Management Governance Lifecycle',
        'expected_sub_domain': 'SD-02.01',
        'members': [
            ('essential_cybersecurity_controls_ecc_2_2024::0035', 'ECC 2-1-1 — asset-management requirements identified, documented, approved.'),
            ('essential_cybersecurity_controls_ecc_2_2024::0036', 'ECC 2-1-2 — asset-management requirements implemented.'),
            ('essential_cybersecurity_controls_ecc_2_2024::0040', 'ECC 2-1-6 — asset-management requirements periodically reviewed.'),
        ],
        'excluded': [
            ('cis_controls_v8::0000', 'CIS 1.1 = concrete inventory control (ABS-CTR); the ECC items are governance-level (ABS-GOV) — different abstraction, not merged.'),
        ],
        'differences': 'These are define / implement / review lifecycle stages of the governance requirement for asset management; define (requirement) vs implement (procedure) must not be merged.',
        'decision': 'EQUIVALENCE_GROUP',
        'decision_confidence': 0.75,
        'requires_human_review': 1,
        'decision_rationale': 'Governance lifecycle of one requirement; canonical = the requirement (2-1-1), with implement (2-1-2, REL-IMP) and review (2-1-6, REL-VER) kept separate. Human review to confirm scope vs the concrete inventory control.',
        'canonical': {
            'title_en': 'Asset Management Program Requirements',
            'definition_short_en': 'This requirement mandates that cybersecurity requirements for managing information and technology assets be identified, documented, and approved.',
            'definition_full_en': 'This artifact requires the organization to define, document, and approve the cybersecurity requirements governing management of its information and technology assets, providing the governance basis for concrete asset controls (inventory, classification, disposal). It applies organization-wide. The minimum expected outcome is an approved asset-management requirements set. Verification is by confirming documented, approved requirements.',
            'objective_en': 'Establish approved governance for how assets are managed.',
            'type': 'ART-REQ', 'abstraction_level': 'ABS-GOV',
            'primary_domain': 'SD-02', 'sub_domain': 'SD-02.01', 'obligation_level': 'OBL-MND',
            'classification_confidence': 0.75,
            'classification_rationale': 'ECC 2-1-1 governance requirement for asset management; SD-02.01. Implement/review stages related, not merged.',
            'verification_method_note': 'Confirm documented, approved asset-management requirements.',
            'missing_fields': ['requirement_type'],
        },
        'source_mappings': [
            ('essential_cybersecurity_controls_ecc_2_2024::0035', 'DIRECT', None),
            ('essential_cybersecurity_controls_ecc_2_2024::0036', 'INDIRECT', 'Implementation stage (REL-IMP) of 2-1-1, not an equivalent restatement.'),
            ('essential_cybersecurity_controls_ecc_2_2024::0040', 'INDIRECT', 'Review stage (REL-VER) of 2-1-1, not an equivalent restatement.'),
        ],
    },
    {
        'candidate_group_id': 'AI-10',
        'concept_name': 'Secure Disposal / Information Deletion',
        'expected_sub_domain': 'SD-02.05',
        'members': [
            ('iso_27002_2022::0007', 'ISO 8.10 — information stored in systems/devices/media should be deleted when no longer required.'),
        ],
        'excluded': [
            ('essential_cybersecurity_controls_ecc_2_2024::0039', 'ECC 2-1-5 = classification/labeling (AI-07); disposal is a distinct lifecycle stage.'),
        ],
        'differences': 'Secure disposal / deletion of information at end of life is a distinct requirement (SD-02.05 Privacy, Retention & Disposal), separate from inventory or classification.',
        'decision': 'CANONICALIZE',
        'decision_confidence': 0.8,
        'requires_human_review': 0,
        'decision_rationale': 'Single, clearly scoped disposal requirement from ISO 8.10; normalized into SD-02.05.',
        'canonical': {
            'title_en': 'Secure Information Disposal',
            'definition_short_en': 'This requirement ensures information held in systems, devices, or media is securely deleted when it is no longer required.',
            'definition_full_en': 'This artifact requires that information no longer needed be securely deleted or destroyed from systems, devices, and storage media so it cannot be recovered by unauthorized parties. It applies to all storage that holds organizational information. The minimum expected outcome is a defined, applied secure-disposal process. Verification is by reviewing disposal records and sampling decommissioned media.',
            'objective_en': 'Prevent recovery of information from assets and media at end of life.',
            'type': 'ART-REQ', 'abstraction_level': 'ABS-POL',
            'primary_domain': 'SD-02', 'sub_domain': 'SD-02.05', 'obligation_level': 'OBL-MND',
            'classification_confidence': 0.8,
            'classification_rationale': 'ISO 8.10 information deletion; SDT SD-02.05 (Privacy, Retention & Disposal).',
            'verification_method_note': 'Review disposal records; sample decommissioned media.',
            'missing_fields': ['requirement_type'],
        },
        'source_mappings': [
            ('iso_27002_2022::0007', 'DIRECT', None),
        ],
    },
]

# Notable excluded near-misses surfaced by broad keyword search but NOT asset-inventory.
UNCLASSIFIED = [
    ('cis_controls_v8::0007', 'Account inventory (CIS 5.1)', 'Belongs to SD-03.01 Identity Lifecycle, not asset inventory.'),
    ('cis_controls_v8::0025', 'Service provider inventory (CIS 15.1)', 'Belongs to SD-08.03 Supplier & Third-Party.'),
    ('cis_controls_v8::0004', 'Data management process (CIS 3.1)', 'Data classification/retention → SD-02.03/05, not asset inventory.'),
    ('cis_controls_v8::0003', 'Only supported software (CIS 2.2)', 'Software currency/support → relate to AI-06 Software Inventory, not merge.'),
    ('~250 items', 'Controls mentioning "enterprise assets" only as scope', 'e.g. MFA/anti-malware/backup "on enterprise assets" — the asset noun is scope, not the subject; excluded from asset-inventory grouping.'),
]


def load_valid(conn):
    return {
        'type': {r[0] for r in conn.execute('SELECT code FROM lk_artifact_type')},
        'abs': {r[0] for r in conn.execute('SELECT code FROM lk_abstraction_level')},
        'dom': {r[0] for r in conn.execute('SELECT code FROM lk_sdt_domain')},
        'sub': {r[0] for r in conn.execute('SELECT code FROM lk_sdt_subdomain')},
        'obl': {r[0] for r in conn.execute('SELECT code FROM lk_obligation_level')},
        'strength': {'DIRECT', 'INDIRECT', 'PARTIAL', 'INFORMATIVE'},
    }


def validate_canonical(v, c):
    e = []
    if c['type'] not in v['type']:
        e.append(f"type {c['type']} not in USACM")
    if c['abstraction_level'] not in v['abs']:
        e.append(f"abstraction_level {c['abstraction_level']} invalid")
    if c['primary_domain'] not in v['dom']:
        e.append(f"primary_domain {c['primary_domain']} not in SDT")
    if c['sub_domain'] not in v['sub']:
        e.append(f"sub_domain {c['sub_domain']} not in SDT")
    elif c['sub_domain'][:5] != c['primary_domain']:
        e.append(f"sub_domain {c['sub_domain']} not in {c['primary_domain']}")
    if c['obligation_level'] not in v['obl']:
        e.append(f"obligation_level {c['obligation_level']} invalid")
    if not (0 <= c['classification_confidence'] <= 1):
        e.append("confidence out of range")
    if not c.get('title_en'):
        e.append("title_en required")
    return e


def validate_mappings(v, g):
    e = []
    for rid, strength, rationale in g['source_mappings']:
        if strength not in v['strength']:
            e.append(f"{rid}: bad mapping_strength {strength}")
        elif strength != 'DIRECT' and not rationale:
            e.append(f"{rid}: {strength} needs rationale")
    return e


def lineage(conn, rid, strength, rationale):
    r = conn.execute("SELECT source_document, source_version, source_section, source_file FROM raw_artifacts WHERE id=?", (rid,)).fetchone()
    if not r:
        return {'raw_id': rid, 'error': 'raw not found', 'mapping_strength': strength}
    return {'raw_id': rid, 'source_document': r[0], 'source_version': r[1],
            'source_section': r[2], 'source_file': r[3], 'mapping_strength': strength, 'rationale': rationale}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', default=os.path.join(ROOT, 'pilot.db'))
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()
    if not os.path.exists(args.db):
        print(f"DB not found: {args.db}. Run: python scripts/ingest_raw.py --db {os.path.basename(args.db)}")
        sys.exit(1)
    conn = sqlite3.connect(args.db)
    conn.execute("PRAGMA foreign_keys = ON;")
    n_raw = conn.execute("SELECT COUNT(*) FROM raw_artifacts").fetchone()[0]
    if n_raw == 0:
        print("raw_artifacts is empty. Run ingest_raw.py first.")
        sys.exit(1)
    v = load_valid(conn)
    os.makedirs(OUT, exist_ok=True)

    # verify all referenced raw ids exist
    all_ids = {rid for g in GROUPS for rid, _ in g['members']}
    missing = [rid for rid in all_ids if not conn.execute("SELECT 1 FROM raw_artifacts WHERE id=?", (rid,)).fetchone()]
    if missing:
        print("MISSING raw ids:", missing)
        sys.exit(1)

    index = []
    dist = {}
    errors = []
    applied = 0
    for g in GROUPS:
        errs = validate_mappings(v, g)
        if g['canonical']:
            errs += validate_canonical(v, g['canonical'])
        if errs:
            errors.append((g['candidate_group_id'], errs))
        packet = {
            'candidate_group_id': g['candidate_group_id'],
            'concept_name': g['concept_name'],
            'expected_sub_domain': g['expected_sub_domain'],
            'member_raw_ids': [m[0] for m in g['members']],
            'excluded_raw_ids': [x[0] for x in g['excluded']],
            'member_reasons': {m[0]: m[1] for m in g['members']},
            'exclusion_reasons': {x[0]: x[1] for x in g['excluded']},
            'differences': g['differences'],
            'decision': g['decision'],
            'decision_confidence': g['decision_confidence'],
            'requires_human_review': g['requires_human_review'],
            'decision_rationale': g['decision_rationale'],
            'canonical_artifact': g['canonical'],
            'source_mappings': [lineage(conn, rid, s, rat) for rid, s, rat in g['source_mappings']],
            'validation': 'OK' if not errs else errs,
        }
        io.open(os.path.join(OUT, f"{g['candidate_group_id']}.json"), 'w', encoding='utf-8').write(
            json.dumps(packet, ensure_ascii=False, indent=2))
        index.append({'id': g['candidate_group_id'], 'concept': g['concept_name'],
                      'sub_domain': g['expected_sub_domain'], 'members': len(g['members']),
                      'excluded': len(g['excluded']), 'decision': g['decision'],
                      'confidence': g['decision_confidence'], 'requires_human_review': g['requires_human_review']})
        dist[g['decision']] = dist.get(g['decision'], 0) + 1

        # apply canonicals to staging
        if args.apply and g['canonical'] and not errs:
            c = g['canonical']
            grp = f"EG-AI-{g['candidate_group_id']}"
            stg = f"STG-CANON-{g['candidate_group_id']}"
            status = 'NEEDS_REVIEW' if (g['requires_human_review'] or c['classification_confidence'] <= 0.70) else 'READY'
            maps = packet['source_mappings']
            conn.execute("INSERT OR IGNORE INTO equivalence_groups (id,label,concept_domain) VALUES (?,?,?)",
                         (grp, c['title_en'], c['primary_domain']))
            conn.execute("""INSERT INTO staging_artifacts
                (id,title_en,definition_short_en,definition_full_en,objective_en,
                 proposed_type,proposed_abstraction_level,proposed_primary_domain,proposed_sub_domain,
                 proposed_obligation_level,classification_confidence,classification_rationale,
                 requires_human_review,proposed_mappings_json,canonical_group_id,merge_action,
                 curation_status,quality_score)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET
                 title_en=excluded.title_en,definition_short_en=excluded.definition_short_en,
                 definition_full_en=excluded.definition_full_en,objective_en=excluded.objective_en,
                 proposed_type=excluded.proposed_type,proposed_abstraction_level=excluded.proposed_abstraction_level,
                 proposed_primary_domain=excluded.proposed_primary_domain,proposed_sub_domain=excluded.proposed_sub_domain,
                 proposed_obligation_level=excluded.proposed_obligation_level,
                 classification_confidence=excluded.classification_confidence,
                 classification_rationale=excluded.classification_rationale,
                 requires_human_review=excluded.requires_human_review,
                 proposed_mappings_json=excluded.proposed_mappings_json,canonical_group_id=excluded.canonical_group_id,
                 merge_action=excluded.merge_action,curation_status=excluded.curation_status,
                 quality_score=excluded.quality_score,updated_at=datetime('now')""",
                (stg, c['title_en'], c['definition_short_en'], c['definition_full_en'], c['objective_en'],
                 c['type'], c['abstraction_level'], c['primary_domain'], c['sub_domain'], c['obligation_level'],
                 c['classification_confidence'], c['classification_rationale'],
                 1 if status == 'NEEDS_REVIEW' else 0, json.dumps(maps, ensure_ascii=False),
                 grp, g['decision'], status, 90))
            applied += 1

    io.open(os.path.join(OUT, 'index.json'), 'w', encoding='utf-8').write(json.dumps(index, ensure_ascii=False, indent=2))
    io.open(os.path.join(OUT, 'unclassified.json'), 'w', encoding='utf-8').write(
        json.dumps([{'raw_id': r, 'label': l, 'reason': why} for r, l, why in UNCLASSIFIED], ensure_ascii=False, indent=2))
    if args.apply:
        conn.commit()

    print("=" * 66)
    print("ASSET INVENTORY PILOT")
    print("=" * 66)
    print(f"atomic groups: {len(GROUPS)} | members: {sum(len(g['members']) for g in GROUPS)} "
          f"| excluded near-misses: {sum(len(g['excluded']) for g in GROUPS)}")
    print(f"decision distribution: {dist}")
    print(f"validation errors: {len(errors)}")
    for gid, errs in errors:
        print("  -", gid, errs)
    print(f"canonicals {'APPLIED to staging' if args.apply else 'validated (dry-run)'}: {applied}")
    print(f"catalog writes: 0 (security_artifacts untouched) | raw writes: 0")
    print(f"outputs in: {OUT}")
    if errors:
        sys.exit(1)


if __name__ == '__main__':
    main()
