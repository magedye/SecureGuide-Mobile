# -*- coding: utf-8 -*-
"""Validate migration 020 exception state-machine invariants."""
import argparse
import glob
import io
import os
import sqlite3
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
fails = []


def check(name, condition):
    print(('PASS' if condition else 'FAIL'), '-', name)
    if not condition:
        fails.append(name)


def expect_error(name, fn, text):
    try:
        fn()
    except sqlite3.Error as exc:
        check(name, text.lower() in str(exc).lower())
    else:
        check(name, False)


def build():
    c = sqlite3.connect(':memory:')
    c.row_factory = sqlite3.Row
    for path in sorted(glob.glob(os.path.join(ROOT, 'migrations', '*.sql'))):
        c.executescript(io.open(path, encoding='utf-8').read())
    c.execute('PRAGMA foreign_keys=ON')
    c.execute("""INSERT INTO security_artifacts(
      id,type,title_en,definition_short_en,primary_domain,sub_domain,
      abstraction_level,source,source_type,obligation_level,requirement_type,
      granularity_level,source_document)
      VALUES ('A','ART-REQ','A','A requirement','SD-01','SD-01.02',
      'ABS-POL','SRC-STD','STANDARD','OBL-MND','RQT-STD','GRN-DETAILED','test')""")
    c.execute("INSERT INTO enterprise_profiles(id,name) VALUES ('P','Profile')")
    c.execute("INSERT INTO profile_artifacts(id,profile_id,artifact_id) VALUES ('PA','P','A')")
    return c


conn = build()
check('migration 020 recorded', conn.execute(
    "SELECT 1 FROM schema_migrations WHERE version='020'").fetchone() is not None)
expect_error('direct non-empty profile exception status rejected', lambda: conn.execute(
    "UPDATE profile_artifacts SET exception_status='EXC-DEFERRED' WHERE id='PA'"), 'approved active exception')
expect_error('approved exception requires expiry', lambda: conn.execute("""
    INSERT INTO profile_exceptions(id,profile_artifact_id,exception_status,justification,
      workflow_status,approved_by,approval_date)
    VALUES ('BAD','PA','EXC-DEFERRED','later','APPROVED','CISO','2026-01-01')
"""), 'expiry')

conn.execute("""INSERT INTO profile_exceptions(
  id,profile_artifact_id,exception_status,justification,workflow_status)
  VALUES ('EX','PA','EXC-DEFERRED','scheduled','DRAFT')""")
conn.execute("UPDATE profile_exceptions SET workflow_status='SUBMITTED' WHERE id='EX'")
conn.execute("UPDATE profile_exceptions SET workflow_status='DRAFT' WHERE id='EX'")
check('return to draft is audited as UPDATED', conn.execute(
    "SELECT COUNT(*) FROM profile_exception_events WHERE exception_id='EX' AND event_type='UPDATED'").fetchone()[0] == 1)
conn.execute("""UPDATE profile_exceptions SET workflow_status='APPROVED',
  approved_by='CISO',approval_date='2026-01-01',expiry_date='2027-01-01' WHERE id='EX'""")
check('approval activates matching profile state', conn.execute(
    "SELECT exception_status||':'||active_exception_id FROM profile_artifacts WHERE id='PA'").fetchone()[0] == 'EXC-DEFERRED:EX')
expect_error('approved exception cannot return to draft', lambda: conn.execute(
    "UPDATE profile_exceptions SET workflow_status='DRAFT' WHERE id='EX'"), 'invalid exception workflow transition')
expect_error('closing requires closure actor and date', lambda: conn.execute(
    "UPDATE profile_exceptions SET workflow_status='CLOSED' WHERE id='EX'"), 'closed_by')
conn.execute("""UPDATE profile_exceptions SET workflow_status='CLOSED',
  closed_by='CISO',closed_at='2026-07-14',closure_note='implemented' WHERE id='EX'""")
check('terminal closure clears profile current state', conn.execute(
    "SELECT exception_status||':'||COALESCE(active_exception_id,'NULL') FROM profile_artifacts WHERE id='PA'").fetchone()[0] == 'EXC-NONE:NULL')
expect_error('terminal workflow cannot reopen', lambda: conn.execute(
    "UPDATE profile_exceptions SET workflow_status='DRAFT' WHERE id='EX'"), 'terminal')
check('no exception governance issues after valid lifecycle', conn.execute(
    "SELECT COUNT(*) FROM v_exception_governance_issues").fetchone()[0] == 0)
check('fresh integrity', conn.execute('PRAGMA integrity_check').fetchone()[0] == 'ok')
check('fresh foreign keys', not conn.execute('PRAGMA foreign_key_check').fetchall())
conn.close()

parser = argparse.ArgumentParser()
parser.add_argument('--db', default=os.path.join(ROOT, 'catalog_work.db'))
args = parser.parse_args()
db = sqlite3.connect(args.db)
check('work database has migration 020', db.execute(
    "SELECT 1 FROM schema_migrations WHERE version='020'").fetchone() is not None)
check('work database has no exception governance issues', db.execute(
    "SELECT COUNT(*) FROM v_exception_governance_issues").fetchone()[0] == 0)
check('work database integrity', db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok')
check('work database foreign keys', not db.execute('PRAGMA foreign_key_check').fetchall())
db.close()

if fails:
    print('SCHEMA 020 VALIDATION FAILED:', fails)
    sys.exit(1)
print('ALL SCHEMA 020 CHECKS PASSED.')
