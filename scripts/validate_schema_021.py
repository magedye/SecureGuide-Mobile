# -*- coding: utf-8 -*-
"""Validate migration 021 operational workflow invariants and read models."""

import argparse
import os
import sqlite3
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from secureguide.database import apply_migrations, connect


failures = []


def check(name, condition):
    print(("PASS" if condition else "FAIL"), "-", name)
    if not condition:
        failures.append(name)


def expect_error(name, callback, expected):
    try:
        callback()
    except sqlite3.Error as exc:
        check(name, expected.lower() in str(exc).lower())
    else:
        check(name, False)


def seed_artifact(conn, artifact_id, domain, sub_domain):
    conn.execute(
        """INSERT INTO security_artifacts(
               id,type,title_en,definition_short_en,primary_domain,sub_domain,
               abstraction_level,source,source_type,obligation_level,requirement_type,
               granularity_level,publication_status,source_document,
               ai_review_status,requires_human_review)
           VALUES (?,?,?, ?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            artifact_id,
            "ART-REQ",
            artifact_id,
            "Test requirement",
            domain,
            sub_domain,
            "ABS-POL",
            "SRC-STD",
            "STANDARD",
            "OBL-MND",
            "RQT-STD",
            "GRN-DETAILED",
            "APPROVED",
            "schema-021-test",
            "AIR-HUMAN-APPROVED",
            0,
        ),
    )


with tempfile.TemporaryDirectory() as temp_dir:
    fresh_path = os.path.join(temp_dir, "schema021.db")
    applied = apply_migrations(fresh_path, os.path.join(ROOT, "migrations"))
    conn = connect(fresh_path)
    check("fresh build applies migration 021", "021" in applied)
    check("fresh build applies migration 022", "022" in applied)
    check(
        "active profile singleton exists",
        conn.execute("SELECT COUNT(*) FROM application_state WHERE singleton_id=1").fetchone()[0]
        == 1,
    )
    seed_artifact(conn, "A1", "SD-01", "SD-01.02")
    seed_artifact(conn, "A2", "SD-06", "SD-06.01")
    conn.execute("INSERT INTO enterprise_profiles(id,name) VALUES ('P1','Profile 1')")
    conn.execute("INSERT INTO enterprise_profiles(id,name) VALUES ('P2','Profile 2')")
    conn.execute("UPDATE application_state SET active_profile_id='P1' WHERE singleton_id=1")
    check(
        "active context resolves profile",
        conn.execute("SELECT profile_id FROM v_active_profile_context").fetchone()[0] == "P1",
    )
    conn.execute(
        "INSERT INTO profile_artifacts(id,profile_id,artifact_id) VALUES ('PA1','P1','A1')"
    )
    conn.execute(
        "INSERT INTO profile_artifacts(id,profile_id,artifact_id) VALUES ('PA2','P1','A2')"
    )
    conn.execute(
        "INSERT INTO profile_artifacts(id,profile_id,artifact_id) VALUES ('PB2','P2','A2')"
    )
    conn.execute("INSERT INTO templates(id,name,version) VALUES ('T','Template','1.0')")
    conn.execute(
        """INSERT INTO template_items(id,template_id,artifact_id,inclusion_status)
           VALUES ('TI','T','A1','MANDATORY')"""
    )
    conn.execute(
        """INSERT INTO profile_templates(
               id,profile_id,template_id,template_version,applied_by)
           VALUES ('PT','P1','T','1.0','tester')"""
    )
    expect_error(
        "template origin must match artifact",
        lambda: conn.execute(
            """INSERT INTO profile_artifact_origins(
                   id,profile_artifact_id,origin_type,template_item_id,selected_by,
                   profile_template_id)
               VALUES ('O','PA2','TEMPLATE','TI','tester','PT')"""
        ),
        "must match",
    )
    conn.execute(
        """INSERT INTO profile_assessments(
               id,profile_artifact_id,assessor_name,implementation_status,
               verification_status,effectiveness,exception_status)
           VALUES ('AS1','PA1','tester','STS-FULL','VER-PASS','EFF-HIGH','EXC-NONE')"""
    )
    expect_error(
        "assessment snapshot is immutable",
        lambda: conn.execute("UPDATE profile_assessments SET comments='rewrite' WHERE id='AS1'"),
        "immutable",
    )
    expect_error(
        "evidence cannot point across profile artifacts",
        lambda: conn.execute(
            """INSERT INTO profile_evidence(
                   id,profile_artifact_id,assessment_id,evidence_type,description,collected_by)
               VALUES ('E1','PB2','AS1','REPORT','cross boundary','tester')"""
        ),
        "same profile artifact",
    )
    expect_error(
        "evidence SHA-256 metadata is constrained",
        lambda: conn.execute(
            """INSERT INTO profile_evidence(
                   id,profile_artifact_id,evidence_type,description,collected_by,content_hash)
               VALUES ('E2','PA1','REPORT','bad hash','tester','not-a-hash')"""
        ),
        "check constraint",
    )
    conn.execute(
        """INSERT INTO profile_exceptions(
               id,profile_artifact_id,exception_status,justification,workflow_status,
               approved_by,approval_date,expiry_date)
           VALUES ('EX-NA','PA1','EXC-NOT-APPLICABLE','outside scope','APPROVED',
                   'owner','2026-01-01','2027-01-01')"""
    )
    conn.execute(
        """INSERT INTO profile_exceptions(
               id,profile_artifact_id,exception_status,justification,workflow_status,
               approved_by,approval_date,expiry_date)
           VALUES ('EX-DEF','PA2','EXC-DEFERRED','scheduled','APPROVED',
                   'owner','2026-01-01','2027-01-01')"""
    )
    gaps = [row[0] for row in conn.execute(
        "SELECT artifact_id FROM v_gap_analysis WHERE profile_id='P1' ORDER BY artifact_id"
    )]
    check("N/A leaves gaps while deferred remains a gap", gaps == ["A2"])
    counts = conn.execute(
        "SELECT total_items,applicable_items,open_gaps FROM v_profile_dashboard WHERE profile_id='P1'"
    ).fetchone()
    check("dashboard denominator follows exception policy", tuple(counts) == (2, 1, 1))
    check(
        "fresh evidence integrity view is clean",
        conn.execute("SELECT COUNT(*) FROM v_profile_evidence_integrity_issues").fetchone()[0]
        == 0,
    )
    check("fresh integrity", conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok")
    check("fresh foreign keys", not conn.execute("PRAGMA foreign_key_check").fetchall())
    conn.close()


parser = argparse.ArgumentParser()
parser.add_argument("--db", default=os.path.join(ROOT, "catalog_work.db"))
args = parser.parse_args()
db = connect(args.db)
check(
    "work database has migration 021",
    db.execute("SELECT 1 FROM schema_migrations WHERE version='021'").fetchone() is not None,
)
check(
    "work database has migration 022",
    db.execute("SELECT 1 FROM schema_migrations WHERE version='022'").fetchone() is not None,
)
check(
    "work database has one application-state row",
    db.execute("SELECT COUNT(*) FROM application_state").fetchone()[0] == 1,
)
check(
    "work database has no evidence integrity issues",
    db.execute("SELECT COUNT(*) FROM v_profile_evidence_integrity_issues").fetchone()[0] == 0,
)
check(
    "work database has no selection-origin governance issues",
    db.execute("SELECT COUNT(*) FROM v_profile_origin_governance_issues").fetchone()[0] == 0,
)
check("work database integrity", db.execute("PRAGMA integrity_check").fetchone()[0] == "ok")
check("work database foreign keys", not db.execute("PRAGMA foreign_key_check").fetchall())
db.close()

if failures:
    print("SCHEMA 021 VALIDATION FAILED:", failures)
    sys.exit(1)
print("ALL SCHEMA 021/022 CHECKS PASSED.")
