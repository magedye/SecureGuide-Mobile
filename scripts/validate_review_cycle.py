# -*- coding: utf-8 -*-
"""End-to-end acceptance test for review_cycle.py."""
import glob
import io
import os
import sqlite3
import subprocess
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
fails = []


def check(name, condition):
    print(('PASS' if condition else 'FAIL'), '-', name)
    if not condition:
        fails.append(name)


with tempfile.TemporaryDirectory(prefix='secureguide-review-') as tmp:
    db = os.path.join(tmp, 'review.db')
    conn = sqlite3.connect(db)
    for path in sorted(glob.glob(os.path.join(ROOT, 'migrations', '*.sql'))):
        conn.executescript(io.open(path, encoding='utf-8').read())
    conn.execute("""INSERT INTO security_artifacts(
        id,type,title_en,definition_short_en,primary_domain,sub_domain,
        abstraction_level,source,source_type,obligation_level,requirement_type,
        granularity_level,publication_status,source_document,scoring_weight)
        VALUES ('A','ART-REQ','A','A requirement','SD-01','SD-01.02',
                'ABS-POL','SRC-STD','STANDARD','OBL-MND','RQT-STD',
                'GRN-DETAILED','APPROVED','review-test',10)""")
    conn.execute("INSERT INTO enterprise_profiles(id,name) VALUES ('P1','Profile')")
    conn.execute("""INSERT INTO profile_artifacts(
        id,profile_id,artifact_id,implementation_status,verification_status,effectiveness)
        VALUES ('PA1','P1','A','STS-FULL','VER-PASS','EFF-HIGH')""")
    conn.commit()
    conn.close()

    start = subprocess.run([sys.executable, os.path.join(ROOT, 'scripts', 'review_cycle.py'),
                            '--db', db, 'start', '--id', 'RC1', '--profile', 'P1',
                            '--title', 'Baseline', '--reviewer', 'Auditor'],
                           cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
    check('review cycle start succeeds', start.returncode == 0)
    complete = subprocess.run([sys.executable, os.path.join(ROOT, 'scripts', 'review_cycle.py'),
                               '--db', db, 'complete', '--id', 'RC1'],
                              cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
    check('review cycle completion succeeds', complete.returncode == 0)

    conn = sqlite3.connect(db)
    check('cycle completed', conn.execute(
        "SELECT status FROM profile_review_cycles WHERE id='RC1'").fetchone()[0] == 'COMPLETED')
    check('one profile artifact snapshotted', conn.execute(
        "SELECT COUNT(*) FROM profile_review_cycle_items WHERE cycle_id='RC1'").fetchone()[0] == 1)
    check('all nine governed metrics captured', conn.execute(
        "SELECT COUNT(*) FROM profile_review_metrics WHERE cycle_id='RC1'").fetchone()[0] == 9)
    check('metric formula version explicit', conn.execute(
        "SELECT COUNT(*) FROM profile_review_metrics WHERE formula_version<>'profile-score-v1'").fetchone()[0] == 0)
    check('review DB integrity', conn.execute('PRAGMA integrity_check').fetchone()[0] == 'ok')
    conn.close()

if fails:
    print('REVIEW CYCLE VALIDATION FAILED:', fails)
    sys.exit(1)
print('ALL REVIEW CYCLE CHECKS PASSED.')
