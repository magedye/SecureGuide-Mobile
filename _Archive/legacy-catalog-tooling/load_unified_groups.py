# -*- coding: utf-8 -*-
"""Validate and apply the committed unified equivalence decision file.

The loader is fail-closed and semantically idempotent. It never regenerates its
input from ignored agent output, never deletes source/raw rows, restores each
staging row's native lineage before regrouping, and routes every group member to
human review. Re-running with the same JSON produces the same staged content.
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
import _promote_common as C

DEFAULT_INPUT = os.path.join(ROOT, 'consolidation', 'unified', 'equivalence.json')
BATCHES = ('AMANI-IMPORT', 'CURATED-IMPORT')
VALID_DOMAINS = {'SD-01', 'SD-02', 'SD-03', 'SD-04', 'SD-05', 'SD-06', 'SD-07', 'SD-08'}
VALID_METHODS = {'AI_CONSERVATIVE', 'EXACT_MATCH', 'AI_CONSERVATIVE+EXACT_MATCH', 'MANUAL'}
VALID_REVIEW = {'AIR-HUMAN-REVIEW'}

OLD_NOTE = re.compile(
    r"\s*\[(?:canonical of [^\]]+|duplicate in [^\]]+|unified-group [^\]]+)\]",
    flags=re.IGNORECASE,
)


def load_groups(path):
    with io.open(path, encoding='utf-8') as handle:
        groups = json.load(handle)
    if not isinstance(groups, list):
        raise ValueError('equivalence input must be a JSON array')
    return groups


def parse_maps(row):
    if not row['proposed_mappings_json']:
        return []
    maps = json.loads(row['proposed_mappings_json'])
    if not isinstance(maps, list):
        raise ValueError(f"{row['id']}: proposed_mappings_json is not an array")
    return maps


def native_maps(row):
    maps = parse_maps(row)
    own = [mapping for mapping in maps if mapping.get('raw_id') == row['raw_artifact_id']]
    return own or maps


def union_maps(members, staged):
    merged, seen = [], set()
    for member in members:
        for mapping in native_maps(staged[member]):
            key = (mapping.get('raw_id'), mapping.get('source_document'))
            if key not in seen:
                merged.append(mapping)
                seen.add(key)
    return merged


def clean_note(value):
    return OLD_NOTE.sub('', value or '').strip()


def append_group_note(value, group_id, role, members):
    base = clean_note(value)
    marker = f"[unified-group {group_id}; role={role}; members={members}; review-required]"
    return f"{base} {marker}".strip()


def require_governance_schema(conn):
    columns = {row[1] for row in conn.execute('PRAGMA table_info(equivalence_groups)')}
    required = {
        'decision_method', 'decision_confidence', 'decision_rationale',
        'ai_review_status', 'requires_human_review', 'reviewed_by', 'reviewed_at',
    }
    missing = sorted(required - columns)
    if missing:
        raise ValueError(
            'migration 017 must be applied before loading groups; missing columns: '
            + ', '.join(missing)
        )


def validate_groups(groups, staged):
    errors = []
    seen_members = set()
    seen_group_ids = set()
    valid = []
    for index, group in enumerate(groups):
        group_id = group.get('id')
        members = group.get('members') or []
        canonical = group.get('canonical')
        rationale = (group.get('rationale') or '').strip()
        conflicts = group.get('classification_conflicts') or {}
        prefix = group_id or f'group[{index}]'

        if not group_id or group_id in seen_group_ids:
            errors.append(f'{prefix}: missing or duplicate stable id')
            continue
        seen_group_ids.add(group_id)
        if len(members) < 2:
            errors.append(f'{prefix}: fewer than two members')
        if canonical not in members:
            errors.append(f'{prefix}: canonical is not a member')
        if group.get('decision') != 'CANONICALIZE':
            errors.append(f'{prefix}: decision must be CANONICALIZE')
        if group.get('decision_method') not in VALID_METHODS:
            errors.append(f'{prefix}: invalid decision_method')
        confidence = group.get('decision_confidence')
        if confidence is not None and (not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1):
            errors.append(f'{prefix}: invalid decision_confidence')
        if not rationale:
            errors.append(f'{prefix}: decision rationale is required')
        if group.get('ai_review_status') not in VALID_REVIEW or group.get('requires_human_review') is not True:
            errors.append(f'{prefix}: equivalence decision must require human review')

        unknown = [member for member in members if member not in staged]
        overlap = [member for member in members if member in seen_members]
        if unknown:
            errors.append(f'{prefix}: unknown members {unknown[:3]}')
        if overlap:
            errors.append(f'{prefix}: members already grouped {overlap[:3]}')
        if unknown or overlap:
            continue
        seen_members.update(members)

        values = {
            'types': sorted({staged[m]['proposed_type'] for m in members}),
            'abstraction_levels': sorted({staged[m]['proposed_abstraction_level'] for m in members}),
            'primary_domains': sorted({staged[m]['proposed_primary_domain'] for m in members}),
            'sub_domains': sorted({staged[m]['proposed_sub_domain'] for m in members}),
        }
        for label, distinct in values.items():
            distinct = [value for value in distinct if value]
            declared = sorted(conflicts.get(label) or [])
            if len(distinct) > 1 and declared != distinct:
                errors.append(f'{prefix}: undeclared {label} conflict {distinct}')
            if len(distinct) <= 1 and declared:
                errors.append(f'{prefix}: spurious {label} conflict declaration')
        if staged[canonical]['proposed_primary_domain'] not in VALID_DOMAINS:
            errors.append(f'{prefix}: canonical has invalid primary domain')
        try:
            maps = union_maps(members, staged)
            if not maps:
                errors.append(f'{prefix}: group has no lineage mappings')
            for mapping in maps:
                if not mapping.get('raw_id') or not mapping.get('source_document'):
                    errors.append(f'{prefix}: incomplete lineage mapping')
                if mapping.get('mapping_strength') not in {'DIRECT', 'INDIRECT', 'PARTIAL', 'INFORMATIVE'}:
                    errors.append(f'{prefix}: invalid mapping strength')
                if mapping.get('mapping_strength') != 'DIRECT' and not mapping.get('rationale'):
                    errors.append(f'{prefix}: non-DIRECT mapping lacks rationale')
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f'{prefix}: {exc}')
        valid.append(group)
    return valid, errors


def semantic_snapshot(conn):
    rows = conn.execute(
        "SELECT id,canonical_group_id,merge_action,curation_status,requires_human_review,"
        "ready_for_promotion,final_review_status,proposed_mappings_json,review_notes,content_hash "
        "FROM staging_artifacts WHERE batch_id IN (?,?) ORDER BY id", BATCHES).fetchall()
    groups = conn.execute(
        "SELECT id,label,concept_domain,decision_method,decision_confidence,decision_rationale,"
        "ai_review_status,requires_human_review,reviewed_by,reviewed_at "
        "FROM equivalence_groups WHERE id IN (SELECT canonical_group_id FROM staging_artifacts "
        "WHERE batch_id IN (?,?) AND canonical_group_id IS NOT NULL) ORDER BY id", BATCHES).fetchall()
    return json.dumps([tuple(row) for row in rows] + [tuple(row) for row in groups],
                      ensure_ascii=False, sort_keys=True)


def apply_groups(conn, groups, staged):
    desired_ids = {group['id'] for group in groups}
    old_ids = {row['canonical_group_id'] for row in staged.values() if row['canonical_group_id']}
    target_ids = {member for group in groups for member in group['members']}

    unsafe = [staged[member]['id'] for member in target_ids
              if staged[member]['final_review_status'] or staged[member]['ready_for_promotion'] != 0
              or staged[member]['promoted_artifact_id']]
    if unsafe:
        raise ValueError(f'cannot regroup approved/ready/promoted rows: {unsafe[:3]}')

    conn.execute('BEGIN IMMEDIATE')
    try:
        # Reset the scoped staging pool to native lineage and remove old generated notes.
        for row in staged.values():
            maps = json.dumps(native_maps(row), ensure_ascii=False)
            conn.execute(
                "UPDATE staging_artifacts SET canonical_group_id=NULL,merge_action=NULL,"
                "proposed_mappings_json=?,review_notes=? WHERE id=?",
                (maps, clean_note(row['review_notes']), row['id']),
            )

        for group in groups:
            group_id = group['id']
            canonical = group['canonical']
            members = group['members']
            canonical_row = staged[canonical]
            label = (canonical_row['title_en'] or group_id)[:120]
            conn.execute(
                "INSERT INTO equivalence_groups "
                "(id,label,concept_domain,decision_method,decision_confidence,decision_rationale,"
                "ai_review_status,requires_human_review,reviewed_by,reviewed_at) "
                "VALUES (?,?,?,?,?,?,?,?,NULL,NULL) "
                "ON CONFLICT(id) DO UPDATE SET label=excluded.label,concept_domain=excluded.concept_domain,"
                "decision_method=excluded.decision_method,decision_confidence=excluded.decision_confidence,"
                "decision_rationale=excluded.decision_rationale,ai_review_status=excluded.ai_review_status,"
                "requires_human_review=excluded.requires_human_review,reviewed_by=NULL,reviewed_at=NULL",
                (group_id, label, canonical_row['proposed_primary_domain'],
                 group['decision_method'], group.get('decision_confidence'), group['rationale'],
                 group['ai_review_status'], 1),
            )
            merged_maps = json.dumps(union_maps(members, staged), ensure_ascii=False)
            for member in members:
                role = 'CANONICALIZE' if member == canonical else 'EQUIVALENCE_GROUP'
                note_role = 'canonical' if member == canonical else 'member'
                mappings = merged_maps if member == canonical else json.dumps(native_maps(staged[member]), ensure_ascii=False)
                conn.execute(
                    "UPDATE staging_artifacts SET canonical_group_id=?,merge_action=?,"
                    "proposed_mappings_json=?,curation_status='NEEDS_REVIEW',requires_human_review=1,"
                    "ready_for_promotion=0,final_review_status=NULL,review_notes=? WHERE id=?",
                    (group_id, role, mappings,
                     append_group_note(staged[member]['review_notes'], group_id, note_role, len(members)), member),
                )

        # Remove only stale group headers formerly used by this staging scope.
        for group_id in sorted(old_ids - desired_ids):
            conn.execute(
                "DELETE FROM equivalence_groups WHERE id=? "
                "AND NOT EXISTS (SELECT 1 FROM staging_artifacts WHERE canonical_group_id=?) "
                "AND NOT EXISTS (SELECT 1 FROM equivalence_group_members WHERE group_id=?)",
                (group_id, group_id, group_id),
            )

        # Hash every row whose group/mapping content may have changed.
        touched = set(staged) if old_ids else target_ids
        for artifact_id in touched:
            row = conn.execute('SELECT * FROM staging_artifacts WHERE id=?', (artifact_id,)).fetchone()
            conn.execute('UPDATE staging_artifacts SET content_hash=? WHERE id=?',
                         (C.content_hash(row), artifact_id))
        conn.execute('COMMIT')
    except Exception:
        conn.execute('ROLLBACK')
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', default=os.path.join(ROOT, 'catalog_work.db'))
    parser.add_argument('--input', default=DEFAULT_INPUT)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()

    groups = load_groups(args.input)
    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    conn.isolation_level = None
    conn.execute('PRAGMA foreign_keys=ON')
    require_governance_schema(conn)
    staged = {row['id']: row for row in conn.execute(
        "SELECT * FROM staging_artifacts WHERE batch_id IN (?,?)", BATCHES)}
    valid_groups, errors = validate_groups(groups, staged)
    if errors:
        print(f'INVALID: {len(errors)} error(s)')
        for error in errors[:25]:
            print(' -', error)
        sys.exit(1)

    duplicates = sum(len(group['members']) - 1 for group in valid_groups)
    print(f"VALID: groups={len(valid_groups)} duplicates={duplicates} input={args.input}")
    if not args.apply:
        print('DRY RUN: pass --apply to update the working database.')
        return

    before = semantic_snapshot(conn)
    apply_groups(conn, valid_groups, staged)
    after = semantic_snapshot(conn)
    print(f"APPLIED: groups={len(valid_groups)} duplicates={duplicates} semantic_changed={before != after}")


if __name__ == '__main__':
    main()
