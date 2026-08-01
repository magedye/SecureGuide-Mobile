# -*- coding: utf-8 -*-
"""Fail-closed gate for the unified, non-destructive staging library."""
import argparse
import hashlib
import io
import json
import os
import re
import sqlite3
import sys
from collections import Counter, defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DEFAULT_DB = os.path.join(ROOT, 'catalog_work.db')
DEFAULT_EQUIVALENCE = os.path.join(ROOT, 'consolidation', 'unified', 'equivalence.json')
DEFAULT_DIST = os.path.join(ROOT, 'consolidation', 'unified', 'UNIFIED_DISTRIBUTION.md')
DEFAULT_PRODUCTION = os.path.join(ROOT, 'catalog.db')
DEFAULT_BASELINE = os.path.join(ROOT, 'consolidation', 'unified', 'production_baseline.json')
BATCHES = ('AMANI-IMPORT', 'CURATED-IMPORT')


def normalized(value):
    return re.sub(r'\s+', ' ', (value or '').strip().lower())


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest().upper()


def load_json(path):
    with io.open(path, encoding='utf-8') as handle:
        return json.load(handle)


def group_map_pairs(row):
    mappings = json.loads(row['proposed_mappings_json']) if row['proposed_mappings_json'] else []
    return {(mapping.get('raw_id'), mapping.get('source_document')) for mapping in mappings}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', default=DEFAULT_DB)
    parser.add_argument('--equivalence', default=DEFAULT_EQUIVALENCE)
    parser.add_argument('--distribution', default=DEFAULT_DIST)
    parser.add_argument('--production-db', default=DEFAULT_PRODUCTION)
    parser.add_argument('--production-baseline', default=DEFAULT_BASELINE)
    parser.add_argument('--skip-production', action='store_true')
    args = parser.parse_args()

    failures = []

    def check(name, condition, detail=''):
        print(('PASS' if condition else 'FAIL'), '-', name, detail)
        if not condition:
            failures.append(name)

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    rows = conn.execute(
        "SELECT * FROM staging_artifacts WHERE batch_id IN (?,?) ORDER BY id", BATCHES).fetchall()
    by_id = {row['id']: row for row in rows}
    decisions = load_json(args.equivalence)

    print('# candidate pool')
    check('1467 unified candidates', len(rows) == 1467, f'actual={len(rows)}')
    check('706 amani candidates', sum(row['batch_id'] == 'AMANI-IMPORT' for row in rows) == 706)
    check('761 curated candidates', sum(row['batch_id'] == 'CURATED-IMPORT' for row in rows) == 761)
    check('nothing approved', all(not row['final_review_status'] for row in rows))
    check('nothing ready for promotion', all(row['ready_for_promotion'] == 0 for row in rows))

    print('# committed decision file versus database')
    decision_by_id = {}
    json_members = set()
    json_errors = []
    for decision in decisions:
        group_id = decision.get('id')
        members = decision.get('members') or []
        if not group_id or group_id in decision_by_id:
            json_errors.append(f'missing/duplicate group id {group_id}')
            continue
        if len(members) < 2 or decision.get('canonical') not in members:
            json_errors.append(f'malformed group {group_id}')
        overlap = json_members.intersection(members)
        if overlap:
            json_errors.append(f'overlapping members {sorted(overlap)[:3]}')
        json_members.update(members)
        if not decision.get('rationale'):
            json_errors.append(f'missing rationale {group_id}')
        if decision.get('ai_review_status') != 'AIR-HUMAN-REVIEW' or decision.get('requires_human_review') is not True:
            json_errors.append(f'group not review-gated {group_id}')
        decision_by_id[group_id] = decision
    check('decision JSON is well formed and non-empty', bool(decisions) and not json_errors,
          f'groups={len(decisions)} errors={json_errors[:2]}')

    db_groups = defaultdict(list)
    for row in rows:
        if row['canonical_group_id']:
            db_groups[row['canonical_group_id']].append(row)
    mismatches = []
    for group_id, decision in decision_by_id.items():
        members = db_groups.get(group_id, [])
        ids = {row['id'] for row in members}
        canonical = [row['id'] for row in members if row['merge_action'] == 'CANONICALIZE']
        if ids != set(decision['members']) or canonical != [decision['canonical']]:
            mismatches.append(group_id)
    check('database groups exactly match committed JSON',
          set(db_groups) == set(decision_by_id) and not mismatches,
          f'db={len(db_groups)} json={len(decision_by_id)} mismatches={mismatches[:3]}')

    review_bad = [row['id'] for members in db_groups.values() for row in members
                  if row['curation_status'] != 'NEEDS_REVIEW'
                  or row['requires_human_review'] != 1
                  or row['ready_for_promotion'] != 0]
    check('every equivalence member is in human review', not review_bad, str(review_bad[:3]))

    metadata_bad = []
    for group_id, decision in decision_by_id.items():
        header = conn.execute(
            "SELECT * FROM equivalence_groups WHERE id=?", (group_id,)).fetchone()
        if not header or header['decision_rationale'] != decision['rationale'] \
                or header['decision_method'] != decision['decision_method'] \
                or header['ai_review_status'] != 'AIR-HUMAN-REVIEW' \
                or header['requires_human_review'] != 1:
            metadata_bad.append(group_id)
    check('group rationale and review metadata persisted', not metadata_bad, str(metadata_bad[:3]))

    lineage_bad = []
    for group_id, members in db_groups.items():
        canonical = next(row for row in members if row['merge_action'] == 'CANONICALIZE')
        canonical_pairs = group_map_pairs(canonical)
        canonical_raw_ids = {pair[0] for pair in canonical_pairs}
        required_raw_ids = {member['raw_artifact_id'] for member in members}
        if not required_raw_ids.issubset(canonical_raw_ids):
            lineage_bad.append(group_id)
    check('canonical carries every member raw-lineage id', not lineage_bad, str(lineage_bad[:3]))

    print('# exact-match coverage and classification conflicts')
    exact_sets = defaultdict(list)
    for row in rows:
        key = normalized(row['definition_short_en'])
        if len(key) >= 30:
            exact_sets[key].append(row)
    missed_exact = []
    conflicting_exact = 0
    for key, members in exact_sets.items():
        if len(members) < 2:
            continue
        identities = {row['canonical_group_id'] or row['id'] for row in members}
        if len(identities) != 1:
            missed_exact.append(key)
        if len({row['proposed_sub_domain'] for row in members}) > 1:
            conflicting_exact += 1
    check('all global exact short-definition sets are unified', not missed_exact,
          f'missed={len(missed_exact)}')
    print(f'INFO - exact sets with SDT conflicts routed to review: {conflicting_exact}')

    print('# SQLite and production isolation')
    check('SQLite integrity', conn.execute('PRAGMA integrity_check').fetchone()[0] == 'ok')
    fk_errors = conn.execute('PRAGMA foreign_key_check').fetchall()
    check('SQLite foreign keys', not fk_errors, str([tuple(row) for row in fk_errors[:3]]))
    if not args.skip_production:
        baseline = load_json(args.production_baseline)
        production_exists = os.path.exists(args.production_db)
        check('production database exists', production_exists)
        if production_exists:
            actual_hash = file_sha256(args.production_db)
            check('production database byte hash unchanged',
                  actual_hash == baseline['sha256'].upper(), actual_hash)
            prod = sqlite3.connect(args.production_db)
            prod.row_factory = sqlite3.Row
            artifacts = prod.execute('SELECT COUNT(*) FROM security_artifacts').fetchone()[0]
            tags = prod.execute('SELECT COUNT(*) FROM artifact_tags').fetchone()[0]
            publication = {row['publication_status']: row['n'] for row in prod.execute(
                'SELECT publication_status,COUNT(*) n FROM security_artifacts GROUP BY publication_status')}
            check('production artifact count unchanged', artifacts == baseline['security_artifacts'], str(artifacts))
            check('production publication state unchanged', publication == baseline['publication_status'], str(publication))
            check('production SQLite integrity', prod.execute('PRAGMA integrity_check').fetchone()[0] == 'ok')
            check('production foreign keys', not prod.execute('PRAGMA foreign_key_check').fetchall())
            prod.close()

    duplicate_count = sum(len(members) - 1 for members in db_groups.values())
    grouped_rows = sum(len(members) for members in db_groups.values())
    unified_rows = [row for row in rows
                    if not row['canonical_group_id'] or row['merge_action'] == 'CANONICALIZE']
    cross_source = sum(1 for members in db_groups.values()
                       if len({row['batch_id'] for row in members}) > 1)
    domain_counts = Counter(row['proposed_primary_domain'] for row in unified_rows)
    type_counts = Counter(row['proposed_type'] for row in unified_rows)
    status_counts = Counter(row['curation_status'] for row in rows)
    histogram = Counter(len(members) for members in db_groups.values())

    report = [
        '# Unified Security Artifact Library — amani + curated', '',
        f"Pool: **{len(rows)}** candidates (706 amani + 761 curated) on `catalog_work.db`.",
        '', '## Review state', '',
        f"- NEEDS_REVIEW: **{status_counts.get('NEEDS_REVIEW', 0)}**",
        f"- CLASSIFIED (not grouped): **{status_counts.get('CLASSIFIED', 0)}**",
        '- Approved or ready for promotion: **0**',
        '', '## Non-destructive equivalence projection', '',
        f'- Equivalence groups: **{len(db_groups)}**',
        f'- Cross-source groups: **{cross_source}**',
        f'- Source rows participating in a group: **{grouped_rows}**',
        f'- Duplicate source rows folded logically: **{duplicate_count}**',
        f'- **Unified artifact projection (canonicals + standalone): {len(unified_rows)}**',
        f'- Logical deduplication rate: **{round(100 * duplicate_count / len(rows), 1)}%**',
        '', 'All source and raw rows remain preserved. Every equivalence decision requires human review.',
        '', '## Unified projection by USACM type', '',
        '| type | count |', '|---|---:|',
    ]
    report += [f'| {key} | {value} |' for key, value in sorted(type_counts.items())]
    report += ['', '## Unified projection by SDT domain', '', '| domain | count |', '|---|---:|']
    report += [f'| {key} | {value} |' for key, value in sorted(domain_counts.items())]
    report += ['', '## Group size histogram', '', '| members | groups |', '|---:|---:|']
    report += [f'| {key} | {value} |' for key, value in sorted(histogram.items())]
    report += ['', '## Validation', '',
               f'- Global exact-definition sets left outside one group: **{len(missed_exact)}**',
               f'- Exact-definition sets with conflicting SDT classifications: **{conflicting_exact}** (human review required)',
               '- Production database: verified against committed SHA-256 baseline' if not args.skip_production
               else '- Production database: check skipped by explicit option']

    with io.open(args.distribution, 'w', encoding='utf-8', newline='\n') as handle:
        handle.write('\n'.join(report) + '\n')
    print(f'WROTE -> {args.distribution}')
    print(f'groups={len(db_groups)} duplicates={duplicate_count} unified={len(unified_rows)} controls={type_counts.get("ART-CTR", 0)}')

    if failures:
        print('UNIFIED LIBRARY VALIDATION FAILED:', failures)
        sys.exit(1)
    print('ALL UNIFIED-LIBRARY CHECKS PASSED.')


if __name__ == '__main__':
    main()
