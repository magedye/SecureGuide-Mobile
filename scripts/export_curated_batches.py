# -*- coding: utf-8 -*-
"""Export the curated raw controls into fixed-size batch files that the
classification agents read. Each batch file is a JSON array of
{raw_id, title, text}. Deterministic (ordered by raw id)."""
import argparse
import io
import json
import os
import sqlite3

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
BATCH_DIR = os.path.join(ROOT, 'consolidation', 'curated', 'batches')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', default=os.path.join(ROOT, 'catalog_work.db'))
    ap.add_argument('--size', type=int, default=25)
    args = ap.parse_args()

    conn = sqlite3.connect(args.db)
    rows = conn.execute(
        "SELECT id, title_draft, raw_text_en FROM raw_artifacts "
        "WHERE source_catalog_id='securekit_curated_controls' ORDER BY id").fetchall()
    os.makedirs(BATCH_DIR, exist_ok=True)
    n = 0
    for i in range(0, len(rows), args.size):
        chunk = [{'raw_id': r[0], 'title': r[1], 'text': r[2]} for r in rows[i:i + args.size]]
        path = os.path.join(BATCH_DIR, f"batch_{n:02d}.json")
        io.open(path, 'w', encoding='utf-8', newline='\n').write(json.dumps(chunk, ensure_ascii=False, indent=2))
        n += 1
    print(f"exported {len(rows)} controls into {n} batches of {args.size} -> {BATCH_DIR}")


if __name__ == '__main__':
    main()
