# -*- coding: utf-8 -*-
"""Block the unified candidate pool by SDT sub-domain for semantic AI review.

This is intentionally not the complete duplicate detector: the deterministic
global exact-definition pass in rebuild_unified_equivalence.py runs afterwards
and ignores proposed SDT classification so misclassification cannot hide exact
duplicates. Emits one review block per sub-domain with at least two artifacts.
"""
import argparse
import io
import json
import os
import sqlite3

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
BLOCK_DIR = os.path.join(ROOT, 'consolidation', 'unified', 'blocks')
BATCHES = ('AMANI-IMPORT', 'CURATED-IMPORT')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', default=os.path.join(ROOT, 'catalog_work.db'))
    args = ap.parse_args()

    conn = sqlite3.connect(args.db); conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, batch_id, proposed_sub_domain, proposed_type, title_en, definition_short_en "
        "FROM staging_artifacts WHERE batch_id IN (?,?) ORDER BY proposed_sub_domain, id", BATCHES).fetchall()

    blocks = {}
    no_sub = 0
    for r in rows:
        sub = r['proposed_sub_domain']
        if not sub:
            no_sub += 1
            continue
        blocks.setdefault(sub, []).append({
            'staging_id': r['id'],
            'source': 'amani' if r['batch_id'] == 'AMANI-IMPORT' else 'curated',
            'type': r['proposed_type'], 'title': r['title_en'],
            'definition': r['definition_short_en'],
        })

    os.makedirs(BLOCK_DIR, exist_ok=True)
    written, skipped = 0, 0
    manifest = []
    for sub in sorted(blocks):
        items = blocks[sub]
        srcs = {i['source'] for i in items}
        if len(items) < 2:
            skipped += 1
            continue
        io.open(os.path.join(BLOCK_DIR, f"{sub}.json"), 'w', encoding='utf-8', newline='\n').write(
            json.dumps(items, ensure_ascii=False, indent=2))
        written += 1
        manifest.append({'sub_domain': sub, 'count': len(items),
                         'amani': sum(1 for i in items if i['source'] == 'amani'),
                         'curated': sum(1 for i in items if i['source'] == 'curated'),
                         'cross_source': len(srcs) == 2})
    io.open(os.path.join(BLOCK_DIR, '_manifest.json'), 'w', encoding='utf-8', newline='\n').write(
        json.dumps(manifest, ensure_ascii=False, indent=2))
    cross = sum(1 for m in manifest if m['cross_source'])
    print(f"blocks written: {written} ({cross} cross-source) | singletons skipped: {skipped} | "
          f"rows without sub_domain: {no_sub} | total blocked: {sum(m['count'] for m in manifest)}")
    print(f"-> {BLOCK_DIR}")


if __name__ == '__main__':
    main()
