# -*- coding: utf-8 -*-
"""Load the AI-classified curated controls into staging_artifacts as reviewable,
SADP-conformant candidates (batch CURATED-IMPORT, all NEEDS_REVIEW). Merges the
per-batch result files into consolidation/curated/classifications.json, validates
every enum against the DB lookup lists (invalid values are dropped/nulled and the
row is flagged in review_notes — never silently kept), attaches a DIRECT lineage
mapping to the curated source, and computes content_hash from the stored row.
Idempotent. NEVER promotes and NEVER writes tags."""
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

CURATED = os.path.join(ROOT, 'consolidation', 'curated')
RESULTS = os.path.join(CURATED, 'results')
MERGED = os.path.join(CURATED, 'classifications.json')
SOURCE_DOC = 'SecureGuide Curated Controls v1'
BATCH = 'CURATED-IMPORT'


def merge_results():
    recs = []
    for p in sorted(glob.glob(os.path.join(RESULTS, 'batch_*.json'))):
        try:
            recs.extend(json.load(io.open(p, encoding='utf-8')))
        except Exception as e:
            print(f"  WARN: skipping unreadable {os.path.basename(p)}: {e}")
    io.open(MERGED, 'w', encoding='utf-8', newline='\n').write(json.dumps(recs, ensure_ascii=False, indent=2))
    return recs


def stg_id(raw_id):
    return 'STG-CURATED-' + raw_id.rsplit('::', 1)[-1]


def load(conn, recs, valid, apply):
    raw_meta = {r[0]: r[1] for r in conn.execute(
        "SELECT id, source_section FROM raw_artifacts WHERE source_catalog_id='securekit_curated_controls'")}
    stats = {'ok': 0, 'fixups': 0, 'missing_raw': 0}
    for rec in recs:
        rid = rec.get('raw_id')
        if rid not in raw_meta:
            stats['missing_raw'] += 1
            continue
        notes = []

        def keep(field, key, allow_null=True):
            v = rec.get(field)
            if v in valid[key]:
                return v
            if v not in (None, ''):
                notes.append(f"invalid {field}={v}")
                stats_fixup()
            return None

        def stats_fixup():
            stats['fixups'] += 1

        typ = keep('proposed_type', 'type')
        abs_ = keep('proposed_abstraction_level', 'abs')
        dom = keep('proposed_primary_domain', 'dom')
        sub = rec.get('proposed_sub_domain')
        if sub not in valid['sub'] or (dom and sub and sub[:5] != dom):
            if sub not in (None, ''):
                notes.append(f"invalid/mismatched sub_domain={sub}")
                stats['fixups'] += 1
            sub = None
        obl = keep('proposed_obligation_level', 'obl')
        # type-conditional dims (respect frozen schema CHECKs)
        rqt = keep('proposed_requirement_type', 'rqt') if typ == 'ART-REQ' else None
        if typ in ('ART-CTR', 'ART-CTE'):
            nat = keep('proposed_control_nature', 'nat')
            fun = keep('proposed_control_function', 'fun')
            tst = keep('proposed_testability', 'tst')
            if not (nat and fun and tst):
                notes.append('control control_* incomplete for CTR/CTE (needs review)')
        else:
            nat = fun = tst = None
        # threats -> validated THR-* list
        threats = []
        for t in (rec.get('proposed_threats') or []):
            code = t.get('threat_code') if isinstance(t, dict) else t
            if code in valid['threat'] and code not in threats:
                threats.append(code)
            elif code not in (None, ''):
                notes.append(f"dropped threat {code}")
        threats_json = json.dumps([{'threat_code': t} for t in threats], ensure_ascii=False) if threats else None
        pr = rec.get('proposed_priority')
        if pr not in valid['priority']:
            if pr not in (None, ''):
                notes.append(f"invalid priority {pr}")
            pr = 'PRI-MEDIUM'
        if rec.get('needs_split'):
            notes.append('classifier flagged needs_split')

        maps = [{'raw_id': rid, 'source_document': SOURCE_DOC, 'source_version': '1',
                 'source_section': raw_meta[rid], 'mapping_strength': 'DIRECT', 'rationale': None}]
        conf = rec.get('classification_confidence')
        review = 1  # every curated import is human-reviewed before promotion

        row = {
            'id': stg_id(rid), 'batch_id': BATCH, 'raw_artifact_id': rid,
            'title_en': rec.get('title_en'), 'definition_short_en': rec.get('definition_short_en'),
            'definition_full_en': rec.get('definition_short_en'), 'objective_en': rec.get('definition_short_en'),
            'proposed_type': typ, 'proposed_abstraction_level': abs_,
            'proposed_primary_domain': dom, 'proposed_sub_domain': sub, 'proposed_obligation_level': obl,
            'proposed_requirement_type': rqt, 'proposed_control_nature': nat,
            'proposed_control_function': fun, 'proposed_testability': tst,
            'classification_confidence': conf,
            'classification_rationale': rec.get('classification_rationale'),
            'requires_human_review': review,
            'proposed_mappings_json': json.dumps(maps, ensure_ascii=False),
            'proposed_threats_json': threats_json, 'proposed_priority': pr,
            'curation_status': 'NEEDS_REVIEW', 'ready_for_promotion': 0,
            'review_notes': ('; '.join(notes) if notes else None),
        }
        if apply:
            cols = list(row)
            conn.execute(
                f"INSERT OR REPLACE INTO staging_artifacts ({','.join(cols)}, content_hash, created_at, updated_at) "
                f"VALUES ({','.join('?' for _ in cols)}, NULL, datetime('now'), datetime('now'))",
                [row[c] for c in cols])
        stats['ok'] += 1
        if notes:
            stats['fixups'] += 0  # already counted per-issue
    if apply:
        # recompute content_hash from the stored rows (float-affinity safe)
        for r in conn.execute(f"SELECT * FROM staging_artifacts WHERE batch_id='{BATCH}'").fetchall():
            conn.execute("UPDATE staging_artifacts SET content_hash=? WHERE id=?", (C.content_hash(r), r['id']))
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', default=os.path.join(ROOT, 'catalog_work.db'))
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()

    recs = merge_results()
    print(f"merged {len(recs)} classifications -> {MERGED}")
    if not os.path.exists(args.db):
        print(f"DB not found: {args.db}"); sys.exit(1)
    conn = sqlite3.connect(args.db); conn.row_factory = sqlite3.Row
    conn.isolation_level = None
    conn.execute("PRAGMA foreign_keys=ON")
    valid = C.load_valid(conn)
    if args.apply:
        conn.execute("INSERT OR IGNORE INTO curation_batches (id, name, status, item_count, notes) VALUES (?,?,?,?,?)",
                     (BATCH, 'Curated controls (AI-classified)', 'PROCESSING', len(recs), 'load_curated_staging.py'))
        conn.execute("BEGIN")
    stats = load(conn, recs, valid, args.apply)
    if args.apply:
        conn.execute("COMMIT"); conn.commit()
    print(f"loaded={stats['ok']} enum-fixups={stats['fixups']} missing-raw={stats['missing_raw']} "
          f"{'(APPLIED)' if args.apply else '(DRY RUN)'}")


if __name__ == '__main__':
    main()
