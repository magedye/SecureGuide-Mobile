# -*- coding: utf-8 -*-
"""Validate migration 018 and fail-closed fallback publication governance."""
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

MIGRATIONS = sorted(glob.glob(os.path.join(ROOT, 'migrations', '*.sql')))
fails = []


def check(name, condition):
    print(('PASS' if condition else 'FAIL'), '-', name)
    if not condition:
        fails.append(name)


def build_fresh():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    for path in MIGRATIONS:
        conn.executescript(io.open(path, encoding='utf-8').read())
    conn.execute('PRAGMA foreign_keys=ON')
    return conn


def base_row(**updates):
    row = {
        'ready_for_promotion': 1,
        'final_review_status': 'APPROVED',
        'curation_status': 'APPROVED',
        'requires_human_review': 0,
        'classification_confidence': 0.95,
        'title_en': 'Fallback governance test',
        'definition_short_en': 'Maintain one governed classification.',
        'proposed_type': 'ART-REQ',
        'proposed_abstraction_level': 'ABS-CTR',
        'proposed_primary_domain': 'SD-01',
        'proposed_sub_domain': 'SD-01.02',
        'proposed_obligation_level': 'OBL-MND',
        'proposed_requirement_type': 'RQT-STD',
        'proposed_mappings_json': json.dumps([
            {'raw_id': 'raw-1', 'source_document': 'test', 'mapping_strength': 'DIRECT'}
        ]),
        'promotion_blockers': None,
    }
    updates.setdefault('proposed_priority', None)
    updates.setdefault('proposed_threats_json', None)
    row.update(updates)
    return row


def migration_and_gate_tests(conn):
    check('migration 018 recorded', conn.execute(
        "SELECT 1 FROM schema_migrations WHERE version='018'").fetchone() is not None)
    count = conn.execute('SELECT COUNT(*) FROM classification_fallback_policy').fetchone()[0]
    check('fallback policy covers 28 governed dimensions', count == 28)

    strict = {r[0] for r in conn.execute(
        "SELECT dimension FROM classification_fallback_policy WHERE fallback_mode='NONE'")}
    check('type and SDT dimensions explicitly forbid fallbacks',
          {'artifact_type', 'primary_domain', 'sub_domain'} <= strict)
    check('type/domain/sub-domain lookup tables contain no fallback rows', conn.execute("""
        SELECT COUNT(*) FROM (
          SELECT code FROM lk_artifact_type
          UNION ALL SELECT code FROM lk_sdt_domain
          UNION ALL SELECT code FROM lk_sdt_subdomain
        ) WHERE code LIKE '%-NA' OR code LIKE '%-UNKNOWN' OR code LIKE '%-MULTI'
    """).fetchone()[0] == 0)

    bad_policy = []
    for p in conn.execute("""SELECT dimension, lookup_table, not_applicable_code,
                                    unknown_code, multi_code
                               FROM classification_fallback_policy
                              WHERE fallback_mode='TRIPLE'"""):
        table_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (p['lookup_table'],)).fetchone()
        if not table_exists:
            bad_policy.append((p['dimension'], 'missing table'))
            continue
        actual = {r[0] for r in conn.execute(f"SELECT code FROM {p['lookup_table']}")}
        if not {p['not_applicable_code'], p['unknown_code'], p['multi_code']} <= actual:
            bad_policy.append((p['dimension'], 'missing code'))
    check(f'every triple policy names a real lookup table and three codes ({bad_policy})', not bad_policy)

    valid = C.load_valid(conn)
    check('clean real-valued row remains promotable', not C.promotion_blockers(base_row(), valid))

    cases = [
        ('ABS-UNKNOWN blocked', {'proposed_abstraction_level': 'ABS-UNKNOWN'}, 'abstraction_level'),
        ('OBL-MULTI blocked', {'proposed_obligation_level': 'OBL-MULTI'}, 'obligation_level'),
        ('RQT-NA is structural and blocked on ART-REQ', {'proposed_requirement_type': 'RQT-NA'}, 'structural N/A'),
        ('RQT-UNKNOWN blocked', {'proposed_requirement_type': 'RQT-UNKNOWN'}, 'human review'),
        ('PRI-NA blocked', {'proposed_priority': 'PRI-NA'}, 'priority'),
        ('PRI-UNKNOWN blocked', {'proposed_priority': 'PRI-UNKNOWN'}, 'priority'),
        ('PRI-MULTI blocked', {'proposed_priority': 'PRI-MULTI'}, 'priority'),
        ('THR-UNKNOWN blocked', {'proposed_threats_json': json.dumps(['THR-UNKNOWN'])}, 'human review'),
        ('THR-MULTI must normalize', {'proposed_threats_json': json.dumps(['THR-MULTI'])}, 'normalized child rows'),
    ]
    for name, update, text in cases:
        blockers = C.promotion_blockers(base_row(**update), valid)
        check(name, any(text in b for b in blockers))

    control = base_row(
        proposed_type='ART-CTR', proposed_requirement_type=None,
        proposed_control_nature='NAT-UNKNOWN', proposed_control_function='FUN-PRE',
        proposed_testability='TST-MAN')
    check('NAT-UNKNOWN blocked on control', any('human review' in b for b in C.promotion_blockers(control, valid)))
    control['proposed_control_nature'] = 'NAT-TEC'
    control['proposed_testability'] = 'TST-NA'
    check('native TST-NA remains publishable', not C.promotion_blockers(control, valid))
    control['proposed_testability'] = 'TST-MULTI'
    check('TST-MULTI blocked', any('human review' in b for b in C.promotion_blockers(control, valid)))

    check('THR-NA remains publishable', not C.promotion_blockers(
        base_row(proposed_threats_json=json.dumps(['THR-NA'])), valid))
    check('multiple real threats use normalized rows without marker', not C.promotion_blockers(
        base_row(proposed_threats_json=json.dumps(['THR-PHISHING', 'THR-RANSOMWARE'])), valid))


def audit_database(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    print(f'# database audit: {path}')
    check('database has migration 018', conn.execute(
        "SELECT 1 FROM schema_migrations WHERE version='018'").fetchone() is not None)

    field_dimension = {
        'abstraction_level': 'abstraction_level',
        'source': 'obligation_source',
        'obligation_level': 'obligation_level',
        'granularity_level': 'granularity_level',
        'priority': 'priority',
        'control_nature': 'control_nature',
        'control_function': 'control_function',
        'requirement_type': 'requirement_type',
        'testability': 'testability',
        'effectiveness': 'effectiveness',
        'exception_status': 'exception_status',
        'review_frequency': 'review_frequency',
    }
    for field, dimension in field_dimension.items():
        codes = [r[0] for r in conn.execute("""
            SELECT code FROM v_nonpublishable_fallback_codes WHERE dimension=?
        """, (dimension,))]
        if not codes:
            continue
        placeholders = ','.join('?' for _ in codes)
        count = conn.execute(
            f"SELECT COUNT(*) FROM security_artifacts WHERE {field} IN ({placeholders})", codes).fetchone()[0]
        check(f'catalog has no nonpublishable fallback in {field}', count == 0)

    bad_threats = conn.execute("""
        SELECT COUNT(*) FROM artifact_threats
         WHERE threat_code IN (
           SELECT code FROM v_nonpublishable_fallback_codes WHERE dimension='threat'
         )
    """).fetchone()[0]
    check('catalog threat rows contain neither THR-UNKNOWN nor THR-MULTI', bad_threats == 0)
    check('framework mappings use real strength values', conn.execute("""
        SELECT COUNT(*) FROM framework_mappings WHERE mapping_strength IN ('NA','UNKNOWN','MULTI')
    """).fetchone()[0] == 0)
    check('SQLite integrity_check', conn.execute('PRAGMA integrity_check').fetchone()[0] == 'ok')
    check('SQLite foreign_key_check', not conn.execute('PRAGMA foreign_key_check').fetchall())
    conn.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', default=os.path.join(ROOT, 'catalog_work.db'))
    args = parser.parse_args()

    fresh = build_fresh()
    migration_and_gate_tests(fresh)
    fresh.close()
    if args.db:
        audit_database(os.path.abspath(args.db))

    if fails:
        print('FALLBACK GOVERNANCE VALIDATION FAILED:', fails)
        sys.exit(1)
    print('ALL FALLBACK GOVERNANCE CHECKS PASSED.')


if __name__ == '__main__':
    main()
