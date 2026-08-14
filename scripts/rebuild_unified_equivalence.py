# -*- coding: utf-8 -*-
"""Rebuild the committed unified equivalence decision file deterministically.

The conservative AI groups are retained, then augmented with a global exact
short-definition pass. Exact matching deliberately ignores the proposed SDT
sub-domain so classification errors cannot hide byte-for-byte duplicate ideas.
Source rows are never deleted; every resulting group is routed to human review.
"""
import argparse
import hashlib
import io
import json
import os
import re
import sys
import tempfile
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT)

from secureguide.catalog_curation import load_curation_candidates

DEFAULT_EQUIVALENCE = os.path.join(ROOT, 'consolidation', 'unified', 'equivalence.json')


def normalize_text(value):
    return re.sub(r'\s+', ' ', (value or '').strip().lower())


class UnionFind:
    def __init__(self, values):
        self.parent = {v: v for v in values}

    def find(self, value):
        parent = self.parent[value]
        if parent != value:
            self.parent[value] = self.find(parent)
        return self.parent[value]

    def union(self, left, right):
        a, b = self.find(left), self.find(right)
        if a != b:
            self.parent[max(a, b)] = min(a, b)


def legacy_group_id(group, index):
    return group.get('id') or f"EQG-{group.get('sub_domain')}-{index:03d}"


def canonical_rank(row):
    title = (row.get('title_en') or '').strip()
    title_quality = 0 if re.fullmatch(r'[\d.\- ]+(?:\([^)]*\))?', title) else 1
    return (
        1 if row.get('source_catalog_id') == 'securekit_curated_controls' else 0,
        title_quality,
        len((row.get('definition_full_en') or '').strip()),
        row.get('classification_confidence') if row.get('classification_confidence') is not None else -1,
        row['candidate_id'],
    )


def choose_canonical(component, rows, old_groups):
    old_canonicals = {g['canonical'] for g in old_groups if g.get('canonical') in component}
    candidates = old_canonicals or set(component)
    return max(candidates, key=lambda artifact_id: canonical_rank(rows[artifact_id]))


def conflict_values(component, rows, field):
    values = sorted({rows[artifact_id].get(field) for artifact_id in component
                     if rows[artifact_id].get(field)})
    return values if len(values) > 1 else []


def stable_exact_id(component):
    digest = hashlib.sha256('\n'.join(sorted(component)).encode('utf-8')).hexdigest()[:16].upper()
    return f'EQG-EXACT-{digest}'


def rebuild(input_path):
    """Discover exact duplicate candidates across every pinned source.

    Detection consumes the same all-source candidate loader as the release
    build.  The decision file remains authoritative for actual merges; this
    function never merges based on similarity alone.
    """
    rows = load_curation_candidates()
    staged_rows = [rows[key] for key in sorted(rows)]
    if not rows:
        raise SystemExit('No unified staging rows found.')

    with io.open(input_path, encoding='utf-8') as handle:
        base_groups = json.load(handle)
    if not isinstance(base_groups, list):
        raise SystemExit('Equivalence input must be a JSON array.')

    union = UnionFind(rows)
    normalized_groups = []
    seen_members = set()
    for index, raw_group in enumerate(base_groups):
        group = dict(raw_group)
        group['id'] = legacy_group_id(group, index)
        members = group.get('members') or []
        canonical = group.get('canonical')
        if len(members) < 2 or canonical not in members:
            raise SystemExit(f"Invalid base group {group['id']}")
        unknown = [member for member in members if member not in rows]
        overlap = [member for member in members if member in seen_members]
        if unknown or overlap:
            raise SystemExit(f"Invalid base group {group['id']}: unknown={unknown}, overlap={overlap}")
        seen_members.update(members)
        for member in members[1:]:
            union.union(members[0], member)
        normalized_groups.append(group)

    exact_sets = defaultdict(list)
    for row in staged_rows:
        key = normalize_text(row.get('definition_short_en'))
        if len(key) >= 30:
            exact_sets[key].append(row['candidate_id'])
    exact_sets = {key: members for key, members in exact_sets.items() if len(members) > 1}
    for members in exact_sets.values():
        for member in members[1:]:
            union.union(members[0], member)

    components = defaultdict(list)
    for artifact_id in rows:
        components[union.find(artifact_id)].append(artifact_id)
    components = [sorted(members) for members in components.values() if len(members) > 1]

    old_by_member = {}
    for group in normalized_groups:
        for member in group['members']:
            old_by_member[member] = group

    rebuilt = []
    for component in components:
        old_groups_by_id = {}
        for member in component:
            old = old_by_member.get(member)
            if old:
                old_groups_by_id[old['id']] = old
        old_groups = list(old_groups_by_id.values())
        exact_keys = sorted({normalize_text(rows[m]['definition_short_en']) for m in component
                             if len(normalize_text(rows[m]['definition_short_en'])) >= 30
                             and len(exact_sets.get(normalize_text(rows[m]['definition_short_en']), [])) > 1})
        unchanged = (len(old_groups) == 1 and set(old_groups[0]['members']) == set(component))
        if unchanged:
            group_id = old_groups[0]['id']
            canonical = old_groups[0]['canonical']
            rationale = old_groups[0].get('rationale') or 'Conservative AI equivalence decision.'
            method = old_groups[0].get('decision_method') or 'AI_CONSERVATIVE'
            confidence = old_groups[0].get('decision_confidence')
        else:
            group_id = min((g['id'] for g in old_groups), default=stable_exact_id(component))
            canonical = choose_canonical(component, rows, old_groups)
            method = 'AI_CONSERVATIVE+EXACT_MATCH' if old_groups else 'EXACT_MATCH'
            confidence = 0.95
            prior = [g.get('rationale') for g in old_groups if g.get('rationale')]
            rationale = (
                f"Global exact-match consolidation: {len(component)} source rows share an identical "
                f"normalized short definition across {len({rows[m]['proposed_sub_domain'] for m in component})} "
                "proposed SDT sub-domain(s). The canonical is provisional pending human review."
            )
            if prior:
                rationale += ' Prior AI rationale: ' + ' | '.join(dict.fromkeys(prior))

        conflicts = {}
        for label, field in (
                ('types', 'type'),
                ('abstraction_levels', 'abstraction_level'),
                ('primary_domains', 'primary_domain'),
                ('sub_domains', 'sub_domain')):
            values = conflict_values(component, rows, field)
            if values:
                conflicts[label] = values

        rebuilt.append({
            'id': group_id,
            'members': component,
            'canonical': canonical,
            'decision': 'CANONICALIZE',
            'decision_method': method,
            'decision_confidence': confidence,
            'rationale': rationale,
            'ai_review_status': 'AIR-HUMAN-REVIEW',
            'requires_human_review': True,
            'sub_domain': rows[canonical]['sub_domain'],
            'classification_conflicts': conflicts,
            'exact_match_keys': len(exact_keys),
        })

    rebuilt.sort(key=lambda group: (group['sub_domain'] or '', group['id']))
    duplicate_count = sum(len(group['members']) - 1 for group in rebuilt)
    cross_source = sum(1 for group in rebuilt
                       if len({rows[m]['source_catalog_id'] for m in group['members']}) > 1)
    stats = {
        'groups': len(rebuilt),
        'duplicates': duplicate_count,
        'unified_size': len(rows) - duplicate_count,
        'cross_source_groups': cross_source,
        'exact_text_sets': len(exact_sets),
    }
    return rebuilt, stats


def atomic_write(path, payload):
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(prefix='.equivalence-', suffix='.json', dir=directory)
    os.close(fd)
    try:
        with io.open(temp_path, 'w', encoding='utf-8', newline='\n') as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write('\n')
        os.replace(temp_path, path)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', default=DEFAULT_EQUIVALENCE)
    parser.add_argument('--output', default=DEFAULT_EQUIVALENCE)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()

    groups, stats = rebuild(args.input)
    print(json.dumps(stats, ensure_ascii=False, sort_keys=True))
    if args.write:
        atomic_write(args.output, groups)
        print(f"WROTE -> {args.output}")
    else:
        print('DRY RUN: pass --write to persist the rebuilt decision file.')


if __name__ == '__main__':
    main()
