# -*- coding: utf-8 -*-
"""Consolidated conformance gate for SADP v1.0. Builds a fresh migrated DB, then
asserts the policy's structural guarantees at the reference level (fallback
vocabulary and disposition, threat dimension, visibility) and at the promotion
level (every mandatory classification present; review-only fallbacks rejected).
See docs/SADP_v1.0.md / SADP_CONFORMANCE.md."""
import io
import json
import os
import subprocess
import sqlite3
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SCRATCH = os.environ.get('SG_SCRATCH', ROOT)
DB = os.path.join(SCRATCH, 'sadp_gate.db')
PLANDIR = os.path.join(ROOT, 'consolidation', 'promotion')
PY = sys.executable
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import _promote_common as C
from build_fallbacks import TARGETS, SUFFIX
fails = []


def run(*a):
    return subprocess.run([PY] + list(a), cwd=ROOT, capture_output=True, text=True,
                          encoding='utf-8', errors='replace')


def check(n, c):
    print(("PASS" if c else "FAIL"), "-", n)
    if not c:
        fails.append(n)


if os.path.exists(DB):
    os.remove(DB)
run('scripts/ingest_raw.py', '--db', DB)
conn = sqlite3.connect(DB); conn.row_factory = sqlite3.Row
conn.execute("PRAGMA foreign_keys=ON")


def codes(lk):
    return {r[0] for r in conn.execute(f"SELECT code FROM {lk}")}


print("# §2.3 universal fallbacks present in every targeted list")
for table, prefix, suffixes in TARGETS:
    have = codes(table)
    missing = [prefix + s for s in suffixes if (prefix + s) not in have]
    check(f"{table}: fallbacks {[prefix + s for s in suffixes]}", not missing)

policy_count = conn.execute("SELECT COUNT(*) FROM classification_fallback_policy").fetchone()[0]
check("migration 018 fallback disposition covers 28 dimensions", policy_count == 28)
strict = {r[0] for r in conn.execute(
    "SELECT dimension FROM classification_fallback_policy WHERE fallback_mode='NONE'")}
check("artifact type + SDT explicitly have no fallbacks",
      {'artifact_type', 'primary_domain', 'sub_domain'} <= strict)

print("# §2.4/§3.1 threat dimension")
thr = codes('lk_threat')
check("lk_threat has NA/UNKNOWN/MULTI", {'THR-NA', 'THR-UNKNOWN', 'THR-MULTI'} <= thr)
check("lk_threat has >=20 canonical threats", len(thr) >= 23)
check("artifact_threats table exists", conn.execute("SELECT 1 FROM sqlite_master WHERE name='artifact_threats'").fetchone() is not None)
alias = conn.execute("SELECT COUNT(*) FROM amani_threat_alias").fetchone()[0]
bad_alias = conn.execute("SELECT COUNT(*) FROM amani_threat_alias WHERE threat_code NOT IN (SELECT code FROM lk_threat)").fetchone()[0]
check("amani_threat_alias non-empty + all FK valid", alias > 0 and bad_alias == 0)

print("# §2.5 UI visibility config")
vis = {r[0] for r in conn.execute("SELECT dimension FROM classification_visibility")}
check("visibility seeded for all core dimensions (>=21)", len(vis) >= 21 and 'threat' in vis and 'priority' in vis)

valid = C.load_valid(conn)
base = {'ready_for_promotion': 1, 'final_review_status': 'APPROVED', 'curation_status': 'APPROVED',
        'requires_human_review': 0, 'classification_confidence': 0.9, 'title_en': 'T',
        'definition_short_en': 'd', 'proposed_type': 'ART-REQ', 'proposed_abstraction_level': 'ABS-CTR',
        'proposed_primary_domain': 'SD-02', 'proposed_sub_domain': 'SD-02.01',
        'proposed_obligation_level': 'OBL-MND', 'proposed_requirement_type': 'RQT-STD',
        'proposed_mappings_json': json.dumps([{'raw_id': 'x', 'source_document': 'CIS', 'mapping_strength': 'DIRECT'}]),
        'promotion_blockers': None}
check("clean row promotable", not C.promotion_blockers(dict(base), valid))
check("bad threat rejected", any('threat' in b for b in C.promotion_blockers({**base, 'proposed_threats_json': json.dumps(['THR-BOGUS'])}, valid)))
check("bad platform rejected", any('platform' in b for b in C.promotion_blockers({**base, 'proposed_platforms_json': json.dumps(['nope'])}, valid)))
check("ABS-UNKNOWN rejected before SQLite", any('not publishable' in b for b in C.promotion_blockers({**base, 'proposed_abstraction_level': 'ABS-UNKNOWN'}, valid)))
check("RQT-NA rejected as structural N/A on ART-REQ", any('structural N/A' in b for b in C.promotion_blockers({**base, 'proposed_requirement_type': 'RQT-NA'}, valid)))
check("PRI-MULTI rejected before SQLite", any('not publishable' in b for b in C.promotion_blockers({**base, 'proposed_priority': 'PRI-MULTI'}, valid)))
check("THR-UNKNOWN rejected before SQLite", any('not publishable' in b for b in C.promotion_blockers({**base, 'proposed_threats_json': json.dumps(['THR-UNKNOWN'])}, valid)))
check("THR-MULTI requires normalized child rows", any('normalized child rows' in b for b in C.promotion_blockers({**base, 'proposed_threats_json': json.dumps(['THR-MULTI'])}, valid)))
check("THR-NA remains valid", not C.promotion_blockers({**base, 'proposed_threats_json': json.dumps(['THR-NA'])}, valid))
conn.close()

print("# promotion invariants (pilot -> promote)")
run('scripts/pilot_asset_inventory.py', '--db', DB, '--apply')
run('scripts/final_review.py', '--db', DB)
run('scripts/review_asset_inventory.py', '--db', DB)
run('scripts/promote.py', 'plan', '--db', DB, '--batch', 'SADP')
run('scripts/promote.py', 'apply', '--db', DB, '--plan', os.path.join(PLANDIR, 'plan-SADP.json'))
conn = sqlite3.connect(DB)
n = conn.execute("SELECT COUNT(*) FROM security_artifacts").fetchone()[0]
check("promoted some artifacts", n > 0)
check("§2.2/§3.1 every artifact has >=1 threat",
      conn.execute("SELECT COUNT(*) FROM security_artifacts WHERE id NOT IN (SELECT artifact_id FROM artifact_threats)").fetchone()[0] == 0)
check("approved threats contain no UNKNOWN/MULTI marker",
      conn.execute("SELECT COUNT(*) FROM artifact_threats WHERE threat_code IN ('THR-UNKNOWN','THR-MULTI')").fetchone()[0] == 0)
MANDATORY = ['primary_domain', 'sub_domain', 'type', 'abstraction_level', 'source', 'obligation_level',
             'exception_status', 'granularity_level', 'implementation_status', 'verification_status',
             'effectiveness', 'priority', 'priority_weight', 'review_frequency']
nulls = {col: conn.execute(f"SELECT COUNT(*) FROM security_artifacts WHERE {col} IS NULL").fetchone()[0] for col in MANDATORY}
check(f"§2.2 no NULL in mandatory classification columns ({[k for k, v in nulls.items() if v]})",
      all(v == 0 for v in nulls.values()))
check("integrity ok", conn.execute("PRAGMA integrity_check").fetchone()[0] == 'ok')
conn.close()
os.remove(DB)

print()
if fails:
    print("SADP CONFORMANCE FAILED:", fails); sys.exit(1)
print("ALL SADP CONFORMANCE CHECKS PASSED.")
