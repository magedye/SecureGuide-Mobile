# -*- coding: utf-8 -*-
"""Create, list, and complete immutable enterprise-profile review cycles."""
import argparse
import json
import os
import sqlite3
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import scoring as S


def connect(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    return conn


def cmd_start(args):
    conn = connect(args.db)
    if not conn.execute("SELECT 1 FROM enterprise_profiles WHERE id=?", (args.profile,)).fetchone():
        raise SystemExit(f'profile not found: {args.profile}')
    conn.execute("""INSERT INTO profile_review_cycles(
        id,profile_id,title,review_type,status,reviewer,scoring_policy_id,started_at,notes)
        VALUES (?,?,?,?,?,?,?,COALESCE(?,datetime('now')),?)""", (
        args.id, args.profile, args.title, args.review_type, 'IN_PROGRESS',
        args.reviewer, args.policy, args.started_at, args.notes))
    conn.commit()
    print(f'STARTED review cycle {args.id} for profile {args.profile}')


def cmd_list(args):
    conn = connect(args.db)
    sql = """SELECT id,profile_id,title,review_type,status,reviewer,started_at,completed_at
               FROM profile_review_cycles"""
    params = []
    if args.profile:
        sql += ' WHERE profile_id=?'
        params.append(args.profile)
    sql += ' ORDER BY created_at DESC,id'
    print(json.dumps([dict(r) for r in conn.execute(sql, params)], ensure_ascii=False, indent=2))


def cmd_complete(args):
    conn = connect(args.db)
    cycle = conn.execute("SELECT * FROM profile_review_cycles WHERE id=?", (args.id,)).fetchone()
    if not cycle:
        raise SystemExit(f'review cycle not found: {args.id}')
    if cycle['status'] == 'COMPLETED':
        raise SystemExit(f'review cycle already completed: {args.id}')
    reviewer = args.reviewer or cycle['reviewer']
    if not reviewer:
        raise SystemExit('reviewer is required to complete a review cycle')

    controls = S.controls_from_catalog(conn, cycle['profile_id'])
    policy = S.load_policy(conn)
    settings = {'view_tier': 'full', 'platforms': []}
    score = S.score(controls, settings, policy)
    rows = conn.execute("""SELECT pa.id AS profile_artifact_id, pa.artifact_id,
                                  pa.implementation_status,pa.verification_status,
                                  pa.effectiveness,pa.exception_status,
                                  COALESCE(pa.priority_override,a.priority) AS effective_priority,
                                  pa.active_exception_id,
                                  (SELECT score FROM profile_assessments x
                                    WHERE x.profile_artifact_id=pa.id
                                    ORDER BY assessment_date DESC,id DESC LIMIT 1) AS assessment_score,
                                  (SELECT COUNT(*) FROM profile_evidence e
                                    WHERE e.profile_artifact_id=pa.id) AS evidence_count
                             FROM profile_artifacts pa
                             JOIN security_artifacts a ON a.id=pa.artifact_id
                            WHERE pa.profile_id=? AND a.is_active=1
                            ORDER BY pa.id""", (cycle['profile_id'],)).fetchall()

    applicable = [c for c in controls if S.is_included(c, settings) and not c.get('excluded')]
    implemented_count = sum(1 for c in applicable
                            if c.get('user_status') == S.IMPLEMENTED
                            and c.get('exception_type') not in ('accepted_risk', 'deferred'))
    exception_count = sum(1 for c in controls if c.get('exception_type'))
    metrics = {
        'OVERALL_SCORE': (score['overall'], 'SCORE'),
        'ASSESSMENT_COVERAGE': (score['assessment_coverage'], 'PERCENT'),
        'VERIFICATION_COVERAGE': (score['verification_coverage'], 'PERCENT'),
        'EFFECTIVENESS_KNOWN': (score['effectiveness_known'], 'PERCENT'),
        'CRITICAL_REMAINING': (score['remaining_critical_risk'], 'COUNT'),
        'APPLICABLE_COUNT': (score['total_controls'], 'COUNT'),
        'IMPLEMENTED_COUNT': (implemented_count, 'COUNT'),
        'VERIFIED_COUNT': (score['verified_pass'], 'COUNT'),
        'EXCEPTION_COUNT': (exception_count, 'COUNT'),
    }

    try:
        conn.execute('BEGIN')
        conn.execute("DELETE FROM profile_review_metrics WHERE cycle_id=?", (args.id,))
        conn.execute("DELETE FROM profile_review_cycle_items WHERE cycle_id=?", (args.id,))
        for r in rows:
            # All selected profile artifacts are snapshotted, including N/A and
            # unavailable items, so later diffs preserve the governance decision.
            conn.execute("""INSERT INTO profile_review_cycle_items(
                cycle_id,profile_artifact_id,implementation_status,verification_status,
                effectiveness,exception_status,effective_priority,assessment_score,
                evidence_count,active_exception_id)
                VALUES (?,?,?,?,?,?,?,?,?,?)""", (
                args.id, r['profile_artifact_id'], r['implementation_status'],
                r['verification_status'], r['effectiveness'], r['exception_status'],
                r['effective_priority'], r['assessment_score'], r['evidence_count'],
                r['active_exception_id']))
        for code, (value, unit) in metrics.items():
            conn.execute("INSERT INTO profile_review_metrics VALUES (?,?,?,?,?)",
                         (args.id, code, value, unit, score['formula_version']))
        conn.execute("""UPDATE profile_review_cycles
                           SET status='COMPLETED',reviewer=?,completed_at=datetime('now'),
                               updated_at=datetime('now') WHERE id=?""", (reviewer, args.id))
        conn.execute('COMMIT')
    except Exception:
        conn.execute('ROLLBACK')
        raise
    print(json.dumps({'cycle_id': args.id, 'profile_id': cycle['profile_id'],
                      'snapshot_items': len(rows), 'metrics': metrics,
                      'formula_version': score['formula_version']},
                     ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', default=os.path.join(ROOT, 'catalog_work.db'))
    sub = parser.add_subparsers(dest='command', required=True)

    start = sub.add_parser('start')
    start.add_argument('--id', required=True)
    start.add_argument('--profile', required=True)
    start.add_argument('--title', required=True)
    start.add_argument('--review-type', default='PERIODIC',
                       choices=['PERIODIC','AD_HOC','AUDIT','POST_INCIDENT','BASELINE'])
    start.add_argument('--reviewer')
    start.add_argument('--policy', default='default')
    start.add_argument('--started-at')
    start.add_argument('--notes')
    start.set_defaults(func=cmd_start)

    ls = sub.add_parser('list')
    ls.add_argument('--profile')
    ls.set_defaults(func=cmd_list)

    complete = sub.add_parser('complete')
    complete.add_argument('--id', required=True)
    complete.add_argument('--reviewer')
    complete.set_defaults(func=cmd_complete)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
