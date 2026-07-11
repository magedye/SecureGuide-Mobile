# -*- coding: utf-8 -*-
"""
validate_pilot.py — automated acceptance tests for the Asset Inventory Pilot.

Rebuilds a fresh DB, runs ingest + pilot apply twice, and asserts:
  1. idempotency (ingest & pilot re-run add nothing)
  2. raw_artifacts unchanged
  3. security_artifacts untouched (catalog never written)
  4. USACM/SDT validity of every canonical (type/domain/sub-domain + belongs-to)
  5. lineage completeness (each canonical has >=1 valid source mapping)
  6. rejection of invalid canonicals (bad sub-domain fails validation)
"""
import os
import subprocess
import sqlite3
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB = os.path.join(ROOT, 'pilot_test.db')
PY = sys.executable
fails = []


def run(*a):
    r = subprocess.run([PY] + list(a), cwd=ROOT, capture_output=True)
    return r.returncode, r.stdout.decode('utf-8', 'replace'), r.stderr.decode('utf-8', 'replace')


def check(name, cond):
    print(("PASS" if cond else "FAIL"), "-", name)
    if not cond:
        fails.append(name)


if os.path.exists(DB):
    os.remove(DB)

print("# rebuild + ingest x2")
run('scripts/ingest_raw.py', '--db', DB)
rc, out, err = run('scripts/ingest_raw.py', '--db', DB)
c = sqlite3.connect(DB)
raw_before = c.execute("SELECT COUNT(*) FROM raw_artifacts").fetchone()[0]
check("ingest idempotent: raw == 2798", raw_before == 2798)
check("ingest run2 no inserts", "0 / 0 / 2798" in out)

print("# pilot apply x2")
rc1, o1, e1 = run('scripts/pilot_asset_inventory.py', '--db', DB, '--apply')
canon1 = c.execute("SELECT COUNT(*) FROM staging_artifacts WHERE id LIKE 'STG-CANON-AI-%'").fetchone()[0]
rc2, o2, e2 = run('scripts/pilot_asset_inventory.py', '--db', DB, '--apply')
canon2 = c.execute("SELECT COUNT(*) FROM staging_artifacts WHERE id LIKE 'STG-CANON-AI-%'").fetchone()[0]
check("pilot exit 0", rc1 == 0 and rc2 == 0)
check("pilot produced 9 canonicals", canon1 == 9)
check("pilot idempotent (no duplicate canonicals)", canon1 == canon2 == 9)

print("# invariants")
raw_after = c.execute("SELECT COUNT(*) FROM raw_artifacts").fetchone()[0]
check("2. raw_artifacts unchanged", raw_after == raw_before == 2798)
check("3. security_artifacts untouched (==0)", c.execute("SELECT COUNT(*) FROM security_artifacts").fetchone()[0] == 0)

# 4. USACM/SDT validity + belongs-to for every canonical
types = {r[0] for r in c.execute("SELECT code FROM lk_artifact_type")}
doms = {r[0] for r in c.execute("SELECT code FROM lk_sdt_domain")}
subs = {r[0] for r in c.execute("SELECT code FROM lk_sdt_subdomain")}
bad = []
import json
for r in c.execute("SELECT id, proposed_type, proposed_primary_domain, proposed_sub_domain, proposed_mappings_json FROM staging_artifacts WHERE id LIKE 'STG-CANON-AI-%'"):
    if r[1] not in types or r[2] not in doms or r[3] not in subs or r[3][:5] != r[2]:
        bad.append((r[0], 'invalid USACM/SDT'))
    maps = json.loads(r[4]) if r[4] else []
    if not maps or any('raw_id' not in m or not m.get('source_document') for m in maps):
        bad.append((r[0], 'incomplete lineage'))
    for m in maps:
        if not c.execute("SELECT 1 FROM raw_artifacts WHERE id=?", (m['raw_id'],)).fetchone():
            bad.append((r[0], f"lineage raw missing {m['raw_id']}"))
check("4+5. every canonical valid USACM/SDT + complete lineage", not bad)
if bad:
    for b in bad:
        print("    -", b)

# 6. rejection of invalid canonical (import the pilot module's validators)
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import pilot_asset_inventory as P
v = P.load_valid(c)
good = dict(P.GROUPS[0]['canonical'])
bad_c = dict(good); bad_c['sub_domain'] = 'SD-06.02'  # does not belong to SD-02
check("6a. valid canonical passes validation", P.validate_canonical(v, good) == [])
check("6b. invalid sub-domain is rejected", len(P.validate_canonical(v, bad_c)) > 0)
bad_t = dict(good); bad_t['type'] = 'ART-XXX'
check("6c. invalid USACM type is rejected", len(P.validate_canonical(v, bad_t)) > 0)

print()
if fails:
    print("PILOT TESTS FAILED:", fails)
    sys.exit(1)
print("ALL PILOT ACCEPTANCE TESTS PASSED.")
