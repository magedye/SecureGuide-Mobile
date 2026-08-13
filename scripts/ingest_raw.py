# -*- coding: utf-8 -*-
"""
ingest_raw.py — Idempotent ingestion of Raw_Catalogs into SecureGuide.

Reads every JSON file under SecureGuide_Mobile_Docs/Raw_Catalogs/, recognises the
`{extraction_metadata, artifacts[]}` envelope, and populates `source_catalogs`
and `raw_artifacts` — preserving full lineage (source document/version/section,
the source raw_artifact_id, original content, extracted elements, source file,
and a content hash). Never writes to `security_artifacts`.

Idempotent: re-running does not duplicate. Each raw row has a deterministic id
(`<catalog>::<index>`); rows are skipped when unchanged, updated when the source
content hash changes, inserted when new.

Usage:
    python scripts/ingest_raw.py [--db PATH] [--catalogs-dir PATH] [--reset]
"""
import argparse
import hashlib
import io
import json
import os
import re
import sqlite3
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MIG = os.path.join(ROOT, 'migrations')
import glob as _glob
MIGRATIONS = [os.path.basename(p) for p in sorted(_glob.glob(os.path.join(MIG, '*.sql')))]
DEFAULT_DB = os.path.join(ROOT, 'secureguide.db')
DEFAULT_CATALOGS = os.path.join(ROOT, 'SecureGuide_Mobile_Docs', 'Raw_Catalogs')

CATALOG_SOURCE_TYPES = {'FRAMEWORK', 'STANDARD', 'THREAT_INTEL', 'GUIDELINE',
                        'POLICY_TEMPLATE', 'REGULATION', 'DOCUMENT', 'SYSTEM', 'TOOL'}


def slug(s):
    return re.sub(r'[^a-z0-9]+', '_', (s or '').lower()).strip('_')


def ensure_schema(conn):
    """Apply migrations 001..005 if the schema is not present yet."""
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='raw_artifacts'").fetchone()
    if exists:
        return False
    for fn in MIGRATIONS:
        conn.executescript(io.open(os.path.join(MIG, fn), encoding='utf-8').read())
    conn.commit()
    return True


def as_json(v):
    return None if v is None else json.dumps(v, ensure_ascii=False)


def flag(v, default=0):
    if v is None:
        return default
    return 1 if v else 0


def catalog_source_type(artifacts):
    counts = {}
    for a in artifacts:
        st = (a.get('source_metadata') or {}).get('source_type')
        if st:
            counts[st] = counts.get(st, 0) + 1
    if not counts:
        return None
    top = max(counts, key=counts.get)
    return top if top in CATALOG_SOURCE_TYPES else None


def upsert_catalog(conn, cat_id, name, source_type, version, url, authority, pub_date, source_file):
    conn.execute(
        """INSERT INTO source_catalogs (id, name, source_type, version, source_url, issuing_authority, publication_date)
           VALUES (?,?,?,?,?,?,?)
           ON CONFLICT(id) DO UPDATE SET name=excluded.name, source_type=excluded.source_type,
             version=excluded.version, source_url=excluded.source_url,
             issuing_authority=excluded.issuing_authority, publication_date=excluded.publication_date""",
        (cat_id, name, source_type, version, url, authority, pub_date))


def ingest_file(conn, path, stats):
    fname = os.path.basename(path)
    with io.open(path, encoding='utf-8') as source:
        data = json.load(source)
    meta = data.get('extraction_metadata', {}) if isinstance(data, dict) else {}
    artifacts = data.get('artifacts', []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
    # A recovered source snapshot may retain its original catalog identity even
    # when the recovery filename is deliberately explicit.
    cat_id = meta.get('source_catalog_id') or slug(fname.replace('.json', ''))
    cat_name = meta.get('source_document') or fname
    # per-file metadata sample (rich variant carries url/authority/date)
    sm0 = (artifacts[0].get('source_metadata') if artifacts else {}) or {}
    upsert_catalog(conn, cat_id, cat_name, catalog_source_type(artifacts),
                   sm0.get('source_version'), sm0.get('source_url'),
                   sm0.get('issuing_authority'), sm0.get('publication_date'), fname)

    declared = meta.get('total_artifacts')
    n = len(artifacts)
    stats['files'].append({'file': fname, 'catalog_id': cat_id, 'count': n,
                           'declared': declared, 'match': (declared is None or declared == n)})

    for i, art in enumerate(artifacts):
        sm = art.get('source_metadata') or {}
        oc = art.get('original_content') or {}
        ee = art.get('extracted_elements') or {}
        cs = art.get('classification_status') or {}
        qf = art.get('quality_flags') or {}
        raw_id = f"{cat_id}::{i:04d}"
        raw_json = json.dumps(art, ensure_ascii=False, sort_keys=True)
        chash = hashlib.sha256(raw_json.encode('utf-8')).hexdigest()

        row = (
            raw_id, cat_id, art.get('raw_artifact_id'),
            sm.get('source_document') or cat_name, sm.get('source_type'),
            sm.get('source_section'), sm.get('source_version'), sm.get('source_url'),
            ee.get('title_draft'), ee.get('description_draft'),
            oc.get('raw_text_en'), oc.get('raw_text_ar'),
            oc.get('original_heading'), oc.get('context_paragraph'),
            as_json(ee.get('keywords')), as_json(ee.get('entities_mentioned')),
            cs.get('usacm_type_assigned'), cs.get('sdt_domain_assigned'), cs.get('sdt_subdomain_assigned'),
            flag(cs.get('requires_classification'), 1), flag(qf.get('needs_human_review'), 0),
            flag(qf.get('is_ambiguous'), 0), qf.get('ambiguity_reason'),
            raw_json, fname, chash,
        )
        existing = conn.execute("SELECT content_hash FROM raw_artifacts WHERE id=?", (raw_id,)).fetchone()
        if existing is None:
            conn.execute(
                """INSERT INTO raw_artifacts
                   (id, source_catalog_id, external_raw_id, source_document, source_type,
                    source_section, source_version, source_url, title_draft, description_draft,
                    raw_text_en, raw_text_ar, original_heading, context_paragraph,
                    keywords_json, entities_mentioned_json, usacm_type_assigned,
                    sdt_domain_assigned, sdt_subdomain_assigned, requires_classification,
                    needs_human_review, is_ambiguous, ambiguity_reason, raw_json, source_file, content_hash)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", row)
            stats['inserted'] += 1
        elif existing[0] != chash:
            conn.execute(
                """UPDATE raw_artifacts SET source_catalog_id=?, external_raw_id=?, source_document=?,
                     source_type=?, source_section=?, source_version=?, source_url=?, title_draft=?,
                     description_draft=?, raw_text_en=?, raw_text_ar=?, original_heading=?,
                     context_paragraph=?, keywords_json=?, entities_mentioned_json=?, usacm_type_assigned=?,
                     sdt_domain_assigned=?, sdt_subdomain_assigned=?, requires_classification=?,
                     needs_human_review=?, is_ambiguous=?, ambiguity_reason=?, raw_json=?, source_file=?, content_hash=?
                   WHERE id=?""", row[1:] + (raw_id,))
            stats['updated'] += 1
        else:
            stats['unchanged'] += 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', default=DEFAULT_DB)
    ap.add_argument('--catalogs-dir', default=DEFAULT_CATALOGS)
    ap.add_argument('--reset', action='store_true', help='delete the DB file and rebuild from scratch')
    args = ap.parse_args()

    if args.reset and os.path.exists(args.db):
        os.remove(args.db)

    conn = sqlite3.connect(args.db)
    conn.execute("PRAGMA foreign_keys = ON;")
    created = ensure_schema(conn)

    files = sorted(f for f in os.listdir(args.catalogs_dir) if f.endswith('.json'))
    stats = {'files': [], 'inserted': 0, 'updated': 0, 'unchanged': 0}
    for f in files:
        ingest_file(conn, os.path.join(args.catalogs_dir, f), stats)
    conn.commit()

    # -------- validation summary --------
    total_raw = conn.execute("SELECT COUNT(*) FROM raw_artifacts").fetchone()[0]
    total_cat = conn.execute("SELECT COUNT(*) FROM source_catalogs").fetchone()[0]
    sec_count = conn.execute("SELECT COUNT(*) FROM security_artifacts").fetchone()[0]
    with_lineage = conn.execute(
        "SELECT COUNT(*) FROM raw_artifacts WHERE source_document IS NOT NULL AND source_file IS NOT NULL AND content_hash IS NOT NULL").fetchone()[0]

    print("=" * 68)
    print(f"INGEST SUMMARY  (db: {args.db}{'  [schema created]' if created else ''})")
    print("=" * 68)
    print(f"Catalog files read : {len(files)}")
    print(f"source_catalogs    : {total_cat}")
    print(f"raw inserted/updated/unchanged : {stats['inserted']} / {stats['updated']} / {stats['unchanged']}")
    print(f"raw_artifacts total: {total_raw}")
    print(f"lineage complete   : {with_lineage}/{total_raw}")
    print(f"security_artifacts : {sec_count}  (must be 0 — ingest never writes the catalog)")
    print("-" * 68)
    print(f"{'file':52} {'rows':>5} {'decl':>5} ok")
    mism = 0
    for fr in stats['files']:
        good = 'Y' if fr['match'] else 'N'
        if not fr['match']:
            mism += 1
        print(f"{fr['file'][:52]:52} {fr['count']:>5} {str(fr['declared']):>5}  {good}")
    print("-" * 68)

    problems = []
    if sec_count != 0:
        problems.append("security_artifacts is not empty!")
    if mism:
        problems.append(f"{mism} file(s) have count != declared total_artifacts")
    if with_lineage != total_raw:
        problems.append(f"{total_raw - with_lineage} rows missing lineage fields")
    EXPECTED = 2798
    if total_raw != EXPECTED:
        print(f"NOTE: raw total {total_raw} != expected {EXPECTED} (informational).")
    if problems:
        print("VALIDATION ISSUES:")
        for p in problems:
            print("  -", p)
        sys.exit(1)
    print(f"OK: {total_raw} raw artifacts ingested with full lineage; catalog untouched.")
    print("Next: run  python scripts/batch_process.py --limit 30")


if __name__ == '__main__':
    main()
