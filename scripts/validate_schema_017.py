# -*- coding: utf-8 -*-
"""Validate migration 017 and its fail-closed equivalence review constraints."""
import glob
import io
import os
import sqlite3
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MIGRATIONS = sorted(glob.glob(os.path.join(ROOT, 'migrations', '*.sql')))
conn = sqlite3.connect(':memory:')
conn.execute('PRAGMA foreign_keys=ON')
for path in MIGRATIONS:
    conn.executescript(io.open(path, encoding='utf-8').read())

failures = []


def must_fail(label, statement, params=()):
    try:
        conn.execute(statement, params)
        failures.append(f'{label}: unexpectedly passed')
    except sqlite3.IntegrityError:
        pass


columns = {row[1] for row in conn.execute('PRAGMA table_info(equivalence_groups)')}
required = {
    'decision_method', 'decision_confidence', 'decision_rationale',
    'ai_review_status', 'requires_human_review', 'reviewed_by', 'reviewed_at',
}
if required - columns:
    failures.append(f'missing columns: {sorted(required - columns)}')

conn.execute(
    "INSERT INTO equivalence_groups "
    "(id,label,decision_method,decision_confidence,decision_rationale,ai_review_status,requires_human_review) "
    "VALUES ('EQG-TEST','Test','EXACT_MATCH',0.95,'Exact normalized definition',"
    "'AIR-HUMAN-REVIEW',1)"
)
must_fail('invalid decision method',
          "INSERT INTO equivalence_groups (id,label,decision_method) VALUES ('BAD-METHOD','x','MAGIC')")
must_fail('invalid confidence',
          "INSERT INTO equivalence_groups (id,label,decision_confidence) VALUES ('BAD-CONF','x',1.2)")
must_fail('invalid AI review status',
          "INSERT INTO equivalence_groups (id,label,ai_review_status) VALUES ('BAD-AIR','x','PENDING')")
must_fail('invalid review flag',
          "INSERT INTO equivalence_groups (id,label,requires_human_review) VALUES ('BAD-FLAG','x',2)")

if conn.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
    failures.append('integrity_check failed')
if conn.execute('PRAGMA foreign_key_check').fetchall():
    failures.append('foreign_key_check failed')
if not conn.execute("SELECT 1 FROM schema_migrations WHERE version='017'").fetchone():
    failures.append('migration 017 not recorded')

if failures:
    print('VALIDATION FAILED:')
    for failure in failures:
        print(' -', failure)
    sys.exit(1)
print('All migration 017 checks PASSED.')
