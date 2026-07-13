# -*- coding: utf-8 -*-
"""Apply the AI-decided equivalence groups onto the unified staging pool
(catalog_work.db). Mirrors agent_consolidate.apply's staging-level consolidation:
creates an equivalence_groups header per group and stamps each member staging row
with canonical_group_id + merge_action (CANONICALIZE for the canonical,
EQUIVALENCE_GROUP for the rest). The canonical's proposed_mappings_json is unioned
across all members so it carries dual (amani + curated) lineage. Non-destructive
(duplicates are flagged, never deleted); everything stays NEEDS_REVIEW; never
promotes. Idempotent."""
import argparse
import glob
import io
import json
import os
import sqlite3
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import _promote_common as C

UNIFIED = os.path.join(ROOT, 'consolidation', 'unified')
RESULTS = os.path.join(UNIFIED, 'results')
MERGED = os.path.join(UNIFIED, 'equivalence.json')
BATCHES = ('AMANI-IMPORT', 'CURATED-IMPORT')


def merge_results():
    groups = []
    for p in sorted(glob.glob(os.path.join(RESULTS, '*.json'))):
        sub = os.path.basename(p)[:-5]
        try:
            for g in (json.load(io.open(p, encoding='utf-8')) or []):
                g['sub_domain'] = sub
                groups.append(g)
        except Exception as e:
            print(f"  WARN: unreadable {os.path.basename(p)}: {e}")
    io.open(MERGED, 'w', encoding='utf-8', newline='\n').write(json.dumps(groups, ensure_ascii=False, indent=2))
    return groups


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', default=os.path.join(ROOT, 'catalog_work.db'))
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()

    groups = merge_results()
    print(f"merged {len(groups)} groups -> {MERGED}")

    conn = sqlite3.connect(args.db); conn.row_factory = sqlite3.Row
    conn.isolation_level = None
    conn.execute("PRAGMA foreign_keys=ON")
    staged = {r['id']: r for r in conn.execute(
        "SELECT id, batch_id, proposed_primary_domain, proposed_mappings_json, title_en "
        "FROM staging_artifacts WHERE batch_id IN (?,?)", BATCHES)}

    # ---- validate groups (fail-loud) ----
    seen, errors, valid_groups = set(), [], []
    for i, g in enumerate(groups):
        members = g.get('members') or []
        canon = g.get('canonical')
        gid = f"EQG-{g['sub_domain']}-{i:03d}"
        if len(members) < 2:
            errors.append(f"{gid}: <2 members"); continue
        if canon not in members:
            errors.append(f"{gid}: canonical not in members"); continue
        bad = [m for m in members if m not in staged]
        if bad:
            errors.append(f"{gid}: unknown members {bad[:3]}"); continue
        dup = [m for m in members if m in seen]
        if dup:
            errors.append(f"{gid}: members already grouped {dup[:3]}"); continue
        seen.update(members)
        valid_groups.append((gid, g, members, canon))
    print(f"valid groups: {len(valid_groups)} | rejected: {len(errors)}")
    for e in errors[:10]:
        print("  -", e)
    if not args.apply:
        dups = sum(len(m) - 1 for _, _, m, _ in valid_groups)
        print(f"DRY RUN: would create {len(valid_groups)} groups, collapse {dups} duplicates.")
        return

    conn.execute("BEGIN")
    touched = set()
    for gid, g, members, canon in valid_groups:
        pri = staged[canon]['proposed_primary_domain']
        pri = pri if pri in ('SD-01', 'SD-02', 'SD-03', 'SD-04', 'SD-05', 'SD-06', 'SD-07', 'SD-08') else None
        label = (staged[canon]['title_en'] or gid)[:120]
        conn.execute("INSERT OR IGNORE INTO equivalence_groups (id, label, concept_domain) VALUES (?,?,?)",
                     (gid, label, pri))
        # union lineage across members -> canonical (dual amani+curated provenance)
        merged_maps, seen_raw = [], set()
        for m in members:
            for mp in (json.loads(staged[m]['proposed_mappings_json']) if staged[m]['proposed_mappings_json'] else []):
                k = (mp.get('raw_id'), mp.get('source_document'))
                if k not in seen_raw:
                    merged_maps.append(mp); seen_raw.add(k)
        for m in members:
            role = 'CANONICALIZE' if m == canon else 'EQUIVALENCE_GROUP'
            if m == canon:
                conn.execute("UPDATE staging_artifacts SET canonical_group_id=?, merge_action=?, "
                             "proposed_mappings_json=?, review_notes=COALESCE(review_notes,'')||? WHERE id=?",
                             (gid, role, json.dumps(merged_maps, ensure_ascii=False),
                              f" [canonical of {gid}: {len(members)} members]", m))
            else:
                conn.execute("UPDATE staging_artifacts SET canonical_group_id=?, merge_action=?, "
                             "review_notes=COALESCE(review_notes,'')||? WHERE id=?",
                             (gid, role, f" [duplicate in {gid} -> canonical {canon}]", m))
            touched.add(m)
    # recompute content_hash for touched rows (mappings/merge_action are hashed)
    for m in touched:
        r = conn.execute("SELECT * FROM staging_artifacts WHERE id=?", (m,)).fetchone()
        conn.execute("UPDATE staging_artifacts SET content_hash=? WHERE id=?", (C.content_hash(r), m))
    conn.execute("COMMIT"); conn.commit()

    dups = sum(len(m) - 1 for _, _, m, _ in valid_groups)
    print(f"APPLIED: {len(valid_groups)} equivalence groups, {len(touched)} rows stamped, {dups} duplicates collapsed.")


if __name__ == '__main__':
    main()
