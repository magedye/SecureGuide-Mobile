# -*- coding: utf-8 -*-
"""
agent_consolidate.py — Agent-led consolidation WITHOUT embeddings.

Deterministic candidate grouping (this script) + agent decision & canonical
drafting (done by a human/AI reviewing the emitted packets). No cosine, no
model, no threshold tuning.

Pipeline:
    group  : scan ALL raw_artifacts by concept seeds (title/keywords/source/
             context) -> cross-source candidate groups -> review packets
             (JSON per concept + index.csv). canonical_draft is left empty for
             the agent to fill per AUTHORING_POLICY + CONSOLIDATION_POLICY.
    apply  : ingest an agent-decided packet (one of the 6 CONSOLIDATION_POLICY
             decisions + a canonical draft) into staging_artifacts +
             equivalence_groups, validated against USACM/SDT, preserving source
             lineage as proposed_mappings_json. Never deletes raw, never writes
             security_artifacts.

Usage:
    python scripts/agent_consolidate.py group [--db PATH] [--focus KEY] [--out DIR] [--min-size 2]
    python scripts/agent_consolidate.py apply <packet.json> [--db PATH] [--apply]
"""
import argparse
import csv
import io
import json
import os
import re
import sqlite3
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DEFAULT_DB = os.path.join(ROOT, 'secureguide.db')
DEFAULT_OUT = os.path.join(ROOT, 'consolidation')

# Concept seeds: deterministic grouping signals. Each item may match several.
SEEDS = [
    ('asset_inventory', 'Asset Inventory', 'SD-02.01',
     r'\b(asset inventor|inventory of (enterprise )?assets?|hardware inventor|inventory of .{0,20}assets?)\b'),
    ('software_inventory', 'Software & License Inventory', 'SD-02.02',
     r'\b(software inventor|inventory of software|license manage|authorized software|unauthorized software)\b'),
    ('data_encryption', 'Data Protection & Encryption', 'SD-02.04',
     r'\b(encrypt|cryptograph|data at rest|data in transit|key management)\b'),
    ('identity_lifecycle', 'Identity Lifecycle', 'SD-03.01',
     r'\b(identity lifecycle|account provisioning|joiner mover leaver|deprovision|account manage)\b'),
    ('mfa_auth', 'Authentication & Credentials', 'SD-03.02',
     r'\b(multi-?factor|\bmfa\b|two-?factor|authentication|credential|password polic|default password)\b'),
    ('access_control', 'Authorization & Access Control', 'SD-03.03',
     r'\b(access control|authoriz|\brbac\b|least privilege access|need-to-know|permission)\b'),
    ('privileged_access', 'Privileged Access', 'SD-03.04',
     r'\b(privileged access|administrative privilege|admin account|least privilege|privileged account)\b'),
    ('network_security', 'Network Security', 'SD-04.01',
     r'\b(firewall|network segment|network security control|communications security|boundary defense)\b'),
    ('hardening', 'Secure Configuration / Hardening', 'SD-04.03',
     r'\b(harden|secure configuration|configuration standard|baseline configuration|benchmark)\b'),
    ('cloud_security', 'Cloud & Virtual Platform', 'SD-04.04',
     r'\b(cloud security|virtual platform|workload protection|container security|kubernetes)\b'),
    ('app_sec_testing', 'Application & API Security Testing', 'SD-05.02',
     r'\b(application security test|api security|\bdast\b|\bsast\b|penetration test.{0,15}app|owasp)\b'),
    ('logging_monitoring', 'Logging & Security Monitoring', 'SD-06.01',
     r'\b(logging|audit log|log manage|security monitor|\bsiem\b|event log|log review)\b'),
    ('vulnerability_mgmt', 'Vulnerability & Patch Management', 'SD-06.03',
     r'\b(vulnerability manage|patch manage|vulnerability scan|remediat.{0,15}vulnerab|missing patch)\b'),
    ('threat_intel', 'Threat Intelligence & IoCs', 'SD-06.05',
     r'\b(threat intelligence|indicator of compromise|\bioc\b|\bttp\b|adversary technique)\b'),
    ('incident_response', 'Incident Response', 'SD-07.01',
     r'\b(incident response|incident manage|security incident|incident handling)\b'),
    ('backup_recovery', 'Backup & Restore', 'SD-07.03',
     r'\b(backup|restore|recovery point|data recovery)\b'),
    ('awareness_training', 'Awareness & Training', 'SD-08.01',
     r'\b(security awareness|awareness training|security training|phishing simulation|security culture)\b'),
    ('third_party', 'Supplier & Third-Party', 'SD-08.03',
     r'\b(third-?party|supplier|vendor risk|outsourc|service provider security)\b'),
]
SEED_MAP = {k: (label, sd, rx) for (k, label, sd, rx) in SEEDS}

VALID_TYPES = {'ART-REQ', 'ART-OBJ', 'ART-PRI', 'ART-POL', 'ART-STD', 'ART-CTR', 'ART-CTE',
               'ART-PRO', 'ART-PRC', 'ART-PRG', 'ART-PLN', 'ART-TSK', 'ART-CFG', 'ART-RUL',
               'ART-EVD', 'ART-MET', 'ART-EXC', 'ART-RSK', 'ART-AST', 'ART-THR', 'ART-VUL', 'ART-OWN'}
DECISIONS = {'CANONICALIZE', 'EQUIVALENCE_GROUP', 'CROSSWALK_ONLY', 'RELATE_ONLY',
             'KEEP_SEPARATE', 'DEPRECATE_DERIVED'}
STRENGTHS = {'DIRECT', 'INDIRECT', 'PARTIAL', 'INFORMATIVE'}


def connect(db):
    if not os.path.exists(db):
        print(f"DB not found: {db}. Run ingest_raw.py first.")
        sys.exit(1)
    c = sqlite3.connect(db)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON;")
    return c


def valid_set(conn, table, col='code'):
    return {r[0] for r in conn.execute(f"SELECT {col} FROM {table}")}


def trim(text, n=45):
    if not text:
        return None
    return ' '.join(re.sub(r'\s+', ' ', text).strip().split()[:n])


def search_text(r):
    return ' '.join(filter(None, [r['title_draft'], r['description_draft'],
                                  r['raw_text_en'], r['context_paragraph']])).lower()


# ----------------------------- group ---------------------------------------
def cmd_group(args):
    conn = connect(args.db)
    os.makedirs(args.out, exist_ok=True)
    raws = conn.execute("SELECT * FROM raw_artifacts").fetchall()
    seeds = [args.focus] if args.focus else [k for (k, *_ ) in SEEDS]
    index_rows = []
    for key in seeds:
        if key not in SEED_MAP:
            print(f"unknown --focus '{key}'. options: {', '.join(SEED_MAP)}")
            sys.exit(1)
        label, sub_domain, rx = SEED_MAP[key]
        pat = re.compile(rx)
        members = []
        for r in raws:
            if pat.search(search_text(r)):
                members.append({
                    'raw_id': r['id'],
                    'external_raw_id': r['external_raw_id'],
                    'source_document': r['source_document'],
                    'source_version': r['source_version'],
                    'source_section': r['source_section'],
                    'title_draft': r['title_draft'],
                    'description': trim(r['description_draft'] or r['raw_text_en'], 45),
                    'keywords': json.loads(r['keywords_json']) if r['keywords_json'] else None,
                })
        if len(members) < args.min_size:
            continue
        sources = sorted({m['source_document'] for m in members if m['source_document']})
        packet = {
            'group_id': f"GRP-{key}",
            'concept': label,
            'expected_sub_domain': sub_domain,
            'member_count': len(members),
            'source_coverage': sources,
            'instructions': ("Decide per CONSOLIDATION_POLICY.md: one of "
                             "CANONICALIZE | EQUIVALENCE_GROUP | CROSSWALK_ONLY | RELATE_ONLY | "
                             "KEEP_SEPARATE | DEPRECATE_DERIVED. If merging, author an English "
                             "canonical per AUTHORING_POLICY.md and set mapping_strength per source. "
                             "Do NOT invent USACM/SDT values. Do NOT delete raw records."),
            'members': members,
            'decision': None,
            'canonical': None,   # agent fills: title_en, definition_*_en, objective_en,
                                 # type, primary_domain, sub_domain, obligation_level,
                                 # classification_confidence, classification_rationale,
                                 # sources:[{raw_id, mapping_strength, rationale?}]
        }
        path = os.path.join(args.out, f"{key}.json")
        io.open(path, 'w', encoding='utf-8').write(json.dumps(packet, ensure_ascii=False, indent=2))
        index_rows.append((packet['group_id'], label, sub_domain, len(members), len(sources), '; '.join(sources)))

    # index.csv
    idx = os.path.join(args.out, 'index.csv')
    with io.open(idx, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['group_id', 'concept', 'expected_sub_domain', 'members', 'source_count', 'sources'])
        w.writerows(index_rows)

    print("=" * 66)
    print(f"CANDIDATE GROUPS  (out: {args.out})")
    print("=" * 66)
    print(f"{'group':26} {'sub':9} {'members':>7} {'sources':>7}")
    for gid, label, sd, mc, sc, _ in index_rows:
        print(f"{gid:26} {sd:9} {mc:>7} {sc:>7}")
    print("-" * 66)
    print(f"{len(index_rows)} groups written. Review a packet, fill decision + canonical,")
    print("then:  python scripts/agent_consolidate.py apply consolidation/<key>.json --apply")


# ----------------------------- apply ---------------------------------------
def validate_canonical(conn, c):
    errs = []
    types = valid_set(conn, 'lk_artifact_type')
    doms = valid_set(conn, 'lk_sdt_domain')
    subs = valid_set(conn, 'lk_sdt_subdomain')
    if c.get('type') not in types:
        errs.append(f"type '{c.get('type')}' not in USACM")
    if c.get('primary_domain') not in doms:
        errs.append(f"primary_domain '{c.get('primary_domain')}' not in SDT")
    sd = c.get('sub_domain')
    if sd not in subs:
        errs.append(f"sub_domain '{sd}' not in SDT")
    elif c.get('primary_domain') and sd[:5] != c['primary_domain']:
        errs.append(f"sub_domain '{sd}' does not belong to '{c['primary_domain']}'")
    conf = c.get('classification_confidence')
    if conf is not None and not (0 <= conf <= 1):
        errs.append("classification_confidence out of [0,1]")
    if not c.get('title_en'):
        errs.append("title_en required")
    for s in c.get('sources', []):
        ms = s.get('mapping_strength')
        if ms not in STRENGTHS:
            errs.append(f"source {s.get('raw_id')}: bad mapping_strength '{ms}'")
        elif ms != 'DIRECT' and not s.get('rationale'):
            errs.append(f"source {s.get('raw_id')}: {ms} mapping needs rationale")
    return errs


def cmd_apply(args):
    conn = connect(args.db)
    packet = json.load(io.open(args.packet, encoding='utf-8'))
    decision = packet.get('decision')
    if decision not in DECISIONS:
        print(f"packet.decision must be one of {sorted(DECISIONS)} (got {decision!r}).")
        sys.exit(1)

    print(f"group {packet['group_id']} — decision {decision} — {packet['member_count']} members "
          f"across {len(packet.get('source_coverage', []))} sources")

    if decision in ('KEEP_SEPARATE', 'CROSSWALK_ONLY', 'RELATE_ONLY', 'DEPRECATE_DERIVED'):
        print(f"decision '{decision}': no canonical staging row is created here.")
        print("  CROSSWALK_ONLY/RELATE_ONLY/DEPRECATE_DERIVED are applied on the catalog")
        print("  (framework_mappings / artifact_relationships / publication_status) AFTER promotion.")
        print("  KEEP_SEPARATE requires no action. Recorded as a review note only.")
        return

    c = packet.get('canonical')
    if not c:
        print("decision requires a 'canonical' object (title_en, definitions, type, domain, sub_domain, sources).")
        sys.exit(1)
    errs = validate_canonical(conn, c)
    if errs:
        print("VALIDATION FAILED (nothing written):")
        for e in errs:
            print("  -", e)
        sys.exit(1)

    # Build the canonical staging row + lineage. No catalog write, no raw delete.
    gid = packet['group_id']
    grp_id = f"EG-{gid}"
    stg_id = f"STG-CANON-{gid}"
    conf = c.get('classification_confidence')
    status = 'NEEDS_REVIEW' if (conf is not None and conf <= 0.70) else 'READY'
    needs_review = 1 if status == 'NEEDS_REVIEW' else 0
    mappings = [{'source_document': None, 'raw_id': s['raw_id'],
                 'mapping_strength': s['mapping_strength'], 'rationale': s.get('rationale')}
                for s in c.get('sources', [])]

    print(f"  -> equivalence_group {grp_id}")
    print(f"  -> canonical staging  {stg_id}  ({c['type']} / {c['sub_domain']}, conf={conf}, status={status})")
    print(f"  -> {len(mappings)} source mappings preserved in proposed_mappings_json")
    if not args.apply:
        print("DRY RUN — re-run with --apply to write to staging.")
        return

    conn.execute("INSERT OR IGNORE INTO equivalence_groups (id, label, concept_domain) VALUES (?,?,?)",
                 (grp_id, c.get('title_en') or packet['concept'], c['primary_domain']))
    conn.execute("""
        INSERT INTO staging_artifacts
          (id, title_en, definition_short_en, definition_full_en, objective_en, canonical_statement,
           proposed_type, proposed_primary_domain, proposed_sub_domain, proposed_obligation_level,
           classification_confidence, classification_rationale, requires_human_review,
           proposed_mappings_json, canonical_group_id, merge_action, curation_status, quality_score)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(id) DO UPDATE SET
          title_en=excluded.title_en, definition_short_en=excluded.definition_short_en,
          definition_full_en=excluded.definition_full_en, objective_en=excluded.objective_en,
          proposed_type=excluded.proposed_type, proposed_primary_domain=excluded.proposed_primary_domain,
          proposed_sub_domain=excluded.proposed_sub_domain, proposed_obligation_level=excluded.proposed_obligation_level,
          classification_confidence=excluded.classification_confidence,
          classification_rationale=excluded.classification_rationale,
          requires_human_review=excluded.requires_human_review,
          proposed_mappings_json=excluded.proposed_mappings_json, canonical_group_id=excluded.canonical_group_id,
          merge_action=excluded.merge_action, curation_status=excluded.curation_status,
          quality_score=excluded.quality_score, updated_at=datetime('now')""",
        (stg_id, c.get('title_en'), c.get('definition_short_en'), c.get('definition_full_en'),
         c.get('objective_en'), c.get('canonical_statement'), c['type'], c['primary_domain'],
         c['sub_domain'], c.get('obligation_level'), conf, c.get('classification_rationale'),
         needs_review, json.dumps(mappings, ensure_ascii=False), grp_id, decision, status,
         c.get('quality_score', 80)))
    conn.commit()
    print(f"APPLIED to staging. raw untouched; security_artifacts untouched. Status: {status}.")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    g = sub.add_parser('group')
    g.add_argument('--db', default=DEFAULT_DB)
    g.add_argument('--out', default=DEFAULT_OUT)
    g.add_argument('--focus', help='one seed key (e.g. asset_inventory)')
    g.add_argument('--min-size', type=int, default=2)
    a = sub.add_parser('apply')
    a.add_argument('packet')
    a.add_argument('--db', default=DEFAULT_DB)
    a.add_argument('--apply', action='store_true')
    args = ap.parse_args()
    if args.cmd == 'group':
        cmd_group(args)
    else:
        cmd_apply(args)


if __name__ == '__main__':
    main()
