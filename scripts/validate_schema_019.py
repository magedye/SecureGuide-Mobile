# -*- coding: utf-8 -*-
"""Validate migration 019 operational governance and extensibility."""
import argparse
import glob
import io
import os
import sqlite3
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MIGRATIONS = sorted(glob.glob(os.path.join(ROOT, 'migrations', '*.sql')))
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


def fresh_db():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    for path in MIGRATIONS:
        conn.executescript(io.open(path, encoding='utf-8').read())
    conn.execute('PRAGMA foreign_keys=ON')
    return conn


def add_artifact(conn, aid, title, publication='DRAFT'):
    conn.execute("""INSERT INTO security_artifacts (
        id,type,title_en,definition_short_en,primary_domain,sub_domain,
        abstraction_level,source,source_type,obligation_level,requirement_type,
        granularity_level,publication_status,source_document
    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
        aid, 'ART-REQ', title, f'{title} requirement', 'SD-01', 'SD-01.02',
        'ABS-POL', 'SRC-STD', 'STANDARD', 'OBL-MND', 'RQT-STD',
        'GRN-DETAILED', publication, 'validation-source'))


def structural_tests(conn):
    check('migration 019 recorded', conn.execute(
        "SELECT 1 FROM schema_migrations WHERE version='019'").fetchone() is not None)
    expected = {'artifact_localizations', 'profile_exception_events',
                'profile_review_cycles', 'profile_review_cycle_items', 'profile_review_metrics'}
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    check('all migration 019 tables exist', expected <= tables)

    for aid in ('A', 'B', 'C'):
        add_artifact(conn, aid, f'Artifact {aid}')
    check('new artifacts receive a primary English localization', conn.execute(
        "SELECT COUNT(*) FROM artifact_localizations WHERE locale='en' AND is_primary=1").fetchone()[0] == 3)
    conn.execute("UPDATE security_artifacts SET title_en='Artifact A revised' WHERE id='A'")
    loc = conn.execute("SELECT title,content_review_status FROM artifact_localizations WHERE artifact_id='A' AND locale='en'").fetchone()
    check('canonical content update synchronizes localization and reopens review',
          loc['title'] == 'Artifact A revised' and loc['content_review_status'] == 'NEEDS_REVIEW')

    conn.execute("INSERT INTO artifact_relationships(source_id,target_id,relation_type) VALUES ('A','B','REL-DEP')")
    conn.execute("INSERT INTO artifact_relationships(source_id,target_id,relation_type) VALUES ('B','C','REL-DEP')")
    expect_error('REL-DEP self dependency rejected', lambda: conn.execute(
        "INSERT INTO artifact_relationships(source_id,target_id,relation_type) VALUES ('A','A','REL-DEP')"), 'self-dependency')
    expect_error('REL-DEP transitive cycle rejected', lambda: conn.execute(
        "INSERT INTO artifact_relationships(source_id,target_id,relation_type) VALUES ('C','A','REL-DEP')"), 'cycle')
    conn.execute("UPDATE security_artifacts SET publication_status='APPROVED' WHERE id='A'")
    check('approved-to-unapproved dependency appears as governance warning', conn.execute(
        "SELECT COUNT(*) FROM v_dependency_governance_issues WHERE source_id='A' AND target_id='B'").fetchone()[0] == 1)

    conn.execute("INSERT INTO enterprise_profiles(id,name) VALUES ('P1','Profile 1')")
    conn.execute("INSERT INTO enterprise_profiles(id,name) VALUES ('P2','Profile 2')")
    conn.execute("INSERT INTO profile_artifacts(id,profile_id,artifact_id) VALUES ('PA1','P1','A')")
    conn.execute("INSERT INTO profile_artifacts(id,profile_id,artifact_id) VALUES ('PA2','P2','B')")

    expect_error('approved risk acceptance requires risk_accepted_by', lambda: conn.execute("""
        INSERT INTO profile_exceptions(id,profile_artifact_id,exception_status,justification,
          workflow_status,approved_by,approval_date,expiry_date)
        VALUES ('EX-BAD','PA1','EXC-RISK-ACCEPTED','temporary','APPROVED','CISO','2026-01-01','2027-01-01')
    """), 'risk_accepted_by')
    conn.execute("""INSERT INTO profile_exceptions(
        id,profile_artifact_id,exception_status,justification,workflow_status)
        VALUES ('EX1','PA1','EXC-RISK-ACCEPTED','legacy replacement','DRAFT')""")
    conn.execute("""UPDATE profile_exceptions SET workflow_status='APPROVED',
        approved_by='CISO',approval_date='2026-01-01',expiry_date='2027-01-01',
        risk_accepted_by='Risk Owner' WHERE id='EX1'""")
    pa = conn.execute("SELECT exception_status,active_exception_id FROM profile_artifacts WHERE id='PA1'").fetchone()
    check('approved exception synchronizes current profile state',
          pa['exception_status'] == 'EXC-RISK-ACCEPTED' and pa['active_exception_id'] == 'EX1')
    check('exception workflow is append-only audited', conn.execute(
        "SELECT COUNT(*) FROM profile_exception_events WHERE exception_id='EX1'").fetchone()[0] == 2)
    conn.execute("UPDATE profile_exceptions SET workflow_status='CLOSED',closed_by='CISO',closed_at='2026-06-01',closure_note='replaced' WHERE id='EX1'")
    pa = conn.execute("SELECT exception_status,active_exception_id FROM profile_artifacts WHERE id='PA1'").fetchone()
    check('closing exception clears active profile exception',
          pa['exception_status'] == 'EXC-NONE' and pa['active_exception_id'] is None)

    conn.execute("""INSERT INTO profile_review_cycles(
        id,profile_id,title,review_type,status,started_at,scoring_policy_id)
        VALUES ('RC1','P1','Quarterly review','PERIODIC','IN_PROGRESS','2026-07-01','default')""")
    conn.execute("""INSERT INTO profile_review_cycle_items(
        cycle_id,profile_artifact_id,implementation_status,verification_status,
        effectiveness,exception_status,effective_priority,evidence_count)
        VALUES ('RC1','PA1','STS-PARTIAL','VER-NOT-VERIFIED','EFF-UNKNOWN','EXC-NONE','PRI-MEDIUM',0)""")
    expect_error('review cycle rejects artifact from another profile', lambda: conn.execute("""
        INSERT INTO profile_review_cycle_items(
          cycle_id,profile_artifact_id,implementation_status,verification_status,
          effectiveness,exception_status,effective_priority,evidence_count)
        VALUES ('RC1','PA2','STS-NOT-APPLIED','VER-NOT-VERIFIED','EFF-UNKNOWN','EXC-NONE','PRI-MEDIUM',0)
    """), 'same profile')
    conn.execute("INSERT INTO profile_review_metrics VALUES ('RC1','APPLICABLE_COUNT',1,'COUNT','profile-score-v1')")
    conn.execute("UPDATE profile_review_cycles SET status='COMPLETED',reviewer='Auditor',completed_at='2026-07-14' WHERE id='RC1'")
    expect_error('completed review cycle is immutable', lambda: conn.execute(
        "UPDATE profile_review_cycles SET notes='changed' WHERE id='RC1'"), 'immutable')
    expect_error('completed review snapshot item is immutable', lambda: conn.execute(
        "DELETE FROM profile_review_cycle_items WHERE cycle_id='RC1' AND profile_artifact_id='PA1'"), 'immutable')

    check('fresh schema integrity', conn.execute('PRAGMA integrity_check').fetchone()[0] == 'ok')
    check('fresh schema foreign keys', not conn.execute('PRAGMA foreign_key_check').fetchall())


def audit_database(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    print(f'# database audit: {path}')
    check('work database has migration 019', conn.execute(
        "SELECT 1 FROM schema_migrations WHERE version='019'").fetchone() is not None)
    missing_en = conn.execute("""SELECT COUNT(*) FROM security_artifacts a
        WHERE NOT EXISTS (SELECT 1 FROM artifact_localizations l
                           WHERE l.artifact_id=a.id AND l.locale='en' AND l.is_primary=1)""").fetchone()[0]
    check('every catalog artifact has primary English localization', missing_en == 0)
    check('at most one primary localization per artifact', conn.execute("""
        SELECT COUNT(*) FROM (
          SELECT artifact_id FROM artifact_localizations WHERE is_primary=1
          GROUP BY artifact_id HAVING COUNT(*)>1
        )
    """).fetchone()[0] == 0)
    cycles = conn.execute("""WITH RECURSIVE reach(origin,node) AS (
        SELECT source_id,target_id FROM artifact_relationships WHERE relation_type='REL-DEP'
        UNION
        SELECT reach.origin,r.target_id FROM reach
        JOIN artifact_relationships r ON r.source_id=reach.node
        WHERE r.relation_type='REL-DEP'
      ) SELECT COUNT(*) FROM reach WHERE origin=node""").fetchone()[0]
    check('stored REL-DEP graph is acyclic', cycles == 0)
    inconsistent = conn.execute("""SELECT COUNT(*) FROM profile_artifacts pa
        LEFT JOIN profile_exceptions pe ON pe.id=pa.active_exception_id
       WHERE pa.active_exception_id IS NOT NULL
         AND (pe.id IS NULL OR pe.workflow_status<>'APPROVED'
              OR pe.exception_status<>pa.exception_status)""").fetchone()[0]
    check('active exceptions agree with profile state', inconsistent == 0)
    check('database integrity', conn.execute('PRAGMA integrity_check').fetchone()[0] == 'ok')
    check('database foreign keys', not conn.execute('PRAGMA foreign_key_check').fetchall())
    conn.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', default=os.path.join(ROOT, 'catalog_work.db'))
    args = parser.parse_args()
    conn = fresh_db()
    structural_tests(conn)
    conn.close()
    audit_database(os.path.abspath(args.db))
    if fails:
        print('SCHEMA 019 VALIDATION FAILED:', fails)
        sys.exit(1)
    print('ALL SCHEMA 019 CHECKS PASSED.')


if __name__ == '__main__':
    main()
