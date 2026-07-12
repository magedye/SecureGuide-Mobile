# -*- coding: utf-8 -*-
"""Gate for Phase 5 (amani asset generator). Proves catalog -> asset -> catalog
is a stable inverse:
  1. fresh DB, import amani, promote every fully-promotable control
  2. build_amani_asset --validate produces a valid v4 asset
  3. re-importing that asset into a fresh DB reproduces the SAME control-id set
     and every domain still maps (no fail-loud) — generator & importer are
     inverse over the amani_domain_alias / amani_* tags
  4. amani facets survive the trip: priority (critical count), enterprise blocks,
     and the asset scores as expected under the ported engine.
"""
import io
import json
import os
import subprocess
import sqlite3
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SCRATCH = os.environ.get('SG_SCRATCH', ROOT)
DB1 = os.path.join(SCRATCH, 'asset_src.db')
DB2 = os.path.join(SCRATCH, 'asset_roundtrip.db')
ASSET = os.path.join(SCRATCH, 'amani_asset.json')
AMANI = os.environ.get('AMANI_JSON', r'd:/APP/amani/SecureGuide/amani_content_v4.json')
PLANDIR = os.path.join(ROOT, 'consolidation', 'promotion')
PY = sys.executable
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import _promote_common as C
import scoring as S
fails = []


def run(*a):
    return subprocess.run([PY] + list(a), cwd=ROOT, capture_output=True, text=True, encoding='utf-8')


def check(n, c):
    print(("PASS" if c else "FAIL"), "-", n)
    if not c:
        fails.append(n)


if not os.path.exists(AMANI):
    print("SKIP: amani json not found."); sys.exit(0)
for p in (DB1, DB2, ASSET):
    if os.path.exists(p):
        os.remove(p)

# 1. import + promote everything promotable
run('scripts/ingest_raw.py', '--db', DB1)
run('scripts/import_amani_content.py', '--input', AMANI, '--db', DB1, '--apply')
conn = sqlite3.connect(DB1); conn.row_factory = sqlite3.Row
conn.execute("PRAGMA foreign_keys=ON")
valid = C.load_valid(conn)
REVIEW = ('not ready_for_promotion', 'final_review_status', 'requires_human_review', 'confidence <=')
promotable = []
for r in conn.execute("SELECT * FROM staging_artifacts WHERE batch_id='AMANI-IMPORT'"):
    blk = C.promotion_blockers(r, valid)
    if all(b.startswith(REVIEW) for b in blk):
        promotable.append(r['id'])
conn.executemany("UPDATE staging_artifacts SET final_review_status='APPROVED', ready_for_promotion=1, "
                 "requires_human_review=0, classification_confidence=0.9 WHERE id=?",
                 [(i,) for i in promotable])
conn.commit()
check("found a large promotable set (>=300)", len(promotable) >= 300)
run('scripts/promote.py', 'plan', '--db', DB1, '--batch', 'AMANI-ALL')
ap = run('scripts/promote.py', 'apply', '--db', DB1, '--plan', os.path.join(PLANDIR, 'plan-AMANI-ALL.json'))
promoted = conn.execute("SELECT COUNT(*) FROM security_artifacts WHERE is_active=1").fetchone()[0]
check("apply promoted the whole set", ap.returncode == 0 and promoted == len(promotable))
crit_src = conn.execute("SELECT COUNT(*) FROM artifact_tags WHERE tag_value='amani_priority:critical' "
                        "AND artifact_id IN (SELECT id FROM security_artifacts)").fetchone()[0]
ent_src = conn.execute("SELECT COUNT(DISTINCT artifact_id) FROM artifact_security_objectives").fetchone()[0]
conn.close()

# 2. generate asset (+ its own validation)
gen = run('scripts/build_amani_asset.py', '--db', DB1, '--out', ASSET, '--validate')
check("build_amani_asset --validate OK", gen.returncode == 0)
asset = json.load(io.open(ASSET, encoding='utf-8'))
check("asset control count == promoted count", len(asset['controls']) == promoted)
check("asset carries scoring_policy bands", len(asset['scoring_policy']['bands']) == 4)
check("asset carries taxonomy", len(asset['taxonomy']['domains']) == 8)
check("every asset control has an id + domain", all(c.get('id') and c.get('domain') for c in asset['controls']))
crit_asset = sum(1 for c in asset['controls'] if c.get('priority') == 'critical')
check("priority preserved (critical count matches source)", crit_asset == crit_src)
ent_asset = sum(1 for c in asset['controls'] if c.get('enterprise'))
check("enterprise blocks preserved", ent_asset == ent_src)

# 3. round-trip: re-import the generated asset into a fresh DB
run('scripts/ingest_raw.py', '--db', DB2)
ri = run('scripts/import_amani_content.py', '--input', ASSET, '--db', DB2, '--apply')
check("round-trip import succeeds (all domains still map)", ri.returncode == 0)
conn2 = sqlite3.connect(DB2)
rt_ids = {r[0] for r in conn2.execute("SELECT external_raw_id FROM raw_artifacts WHERE id LIKE 'amani_v4::%'")}
conn2.close()
asset_ids = {c['id'] for c in asset['controls']}
check("round-trip reproduces the exact control-id set", rt_ids == asset_ids)

# 4. scoring behaves on the generated asset (deps dropped by design -> no clamp)
allc = S.controls_from_amani(asset)
settings = {'view_tier': 'full', 'platforms': sorted({p for c in allc for p in c['platform_ids'] if p != 'all'})}
rs0 = S.score(allc, settings, dict(S.DEFAULT_POLICY))
check("asset scores 0 with nothing implemented", abs(rs0['overall']) < 0.001)
check("asset applicable count == control count", rs0['total_controls'] == len(asset['controls']))
implc = S.controls_from_amani(asset, states={c['id']: 'implemented' for c in asset['controls']})
rs1 = S.score(implc, settings, dict(S.DEFAULT_POLICY))
check("asset scores 100 fully implemented (no dangling deps)", abs(rs1['overall'] - 100.0) < 0.001)
check("asset critical-cap consistent with critical presence", rs0['capped'] == (crit_asset > 0))

for p in (DB1, DB2, ASSET):
    if os.path.exists(p):
        os.remove(p)
print()
if fails:
    print("AMANI-ASSET VALIDATION FAILED:", fails); sys.exit(1)
print("ALL AMANI-ASSET (ROUND-TRIP) CHECKS PASSED.")
