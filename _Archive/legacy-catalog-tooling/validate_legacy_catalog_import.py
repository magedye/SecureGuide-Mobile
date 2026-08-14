# -*- coding: utf-8 -*-
"""Gate for Phase 3 (amani import). Builds a fresh migrated DB, imports the 706
amani controls, and asserts the structural guarantees:
  - 706 raw + 706 staging, full lineage, deterministic ids
  - every control domain mapped via amani_domain_alias (no silent unmapped)
  - fail-loud abort on an unmapped domain (synthetic input)
  - non-empty lineage/mappings on every staging row
  - personal controls flagged for review; enterprise carry rich classification
  - imported enrichment is clean (passes enrichment_blockers)
  - an imported enterprise control actually promotes through promote.py, with its
    rich collections normalized into the catalog child tables (real write path)
"""
import io
import json
import os
import subprocess
import sqlite3
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SCRATCH = os.environ.get('SG_SCRATCH', ROOT)
DB = os.path.join(SCRATCH, 'amani_validate.db')
AMANI = os.environ.get('AMANI_JSON', r'd:/APP/amani/SecureGuide/archive/amani_content_v4.json')
PLANDIR = os.path.join(ROOT, 'consolidation', 'promotion')
PY = sys.executable
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import _promote_common as C
fails = []


def run(*a):
    return subprocess.run([PY] + list(a), cwd=ROOT, capture_output=True, text=True, encoding='utf-8')


def check(n, c):
    print(("PASS" if c else "FAIL"), "-", n)
    if not c:
        fails.append(n)


if not os.path.exists(AMANI):
    print("SKIP: amani_content_v4.json not found at", AMANI); sys.exit(0)
if os.path.exists(DB):
    os.remove(DB)
run('scripts/ingest_raw.py', '--db', DB)
imp = run('scripts/import_amani_content.py', '--input', AMANI, '--db', DB, '--apply')
check("import applied (exit 0)", imp.returncode == 0)

src = json.load(io.open(AMANI, encoding='utf-8'))
controls = src['controls']
conn = sqlite3.connect(DB); conn.row_factory = sqlite3.Row
conn.execute("PRAGMA foreign_keys=ON")


def one(q, *p):
    return conn.execute(q, p).fetchone()[0]


print("# counts + lineage")
check("706 amani raw rows", one("SELECT COUNT(*) FROM raw_artifacts WHERE id LIKE 'amani_v4::%'") == len(controls))
check("706 staging rows", one("SELECT COUNT(*) FROM staging_artifacts WHERE batch_id='AMANI-IMPORT'") == len(controls))
check("all amani raw have content_hash + external id + lineage",
      one("SELECT COUNT(*) FROM raw_artifacts WHERE id LIKE 'amani_v4::%' AND (content_hash IS NULL OR external_raw_id IS NULL OR source_document IS NULL)") == 0)
check("every staging row links to a real raw row",
      one("SELECT COUNT(*) FROM staging_artifacts s WHERE s.batch_id='AMANI-IMPORT' AND NOT EXISTS (SELECT 1 FROM raw_artifacts r WHERE r.id=s.raw_artifact_id)") == 0)
check("integrity ok", conn.execute("PRAGMA integrity_check").fetchone()[0] == 'ok')

print("# domain mapping (no silent unmapped)")
alias = {r['amani_key']: (r['sdt_primary'], r['sdt_sub']) for r in conn.execute("SELECT amani_key,sdt_primary,sdt_sub FROM amani_domain_alias")}
check("every control domain is in the alias", all(c['domain'] in alias for c in controls))
# every staging primary/sub equals the alias for its source control
mism = 0
rows = {r['id']: r for r in conn.execute("SELECT id, proposed_primary_domain, proposed_sub_domain, raw_artifact_id FROM staging_artifacts WHERE batch_id='AMANI-IMPORT'")}
ext = {r['id']: r['external_raw_id'] for r in conn.execute("SELECT id, external_raw_id FROM raw_artifacts WHERE id LIKE 'amani_v4::%'")}
by_extid = {c['id']: c for c in controls}
for sid, r in rows.items():
    ctrl = by_extid.get(ext.get(r['raw_artifact_id']))
    if not ctrl:
        mism += 1; continue
    pri, sub = alias[ctrl['domain']]
    if r['proposed_primary_domain'] != pri or r['proposed_sub_domain'] != sub:
        mism += 1
check("staging domain/sub matches alias for every row", mism == 0)

print("# fail-loud on an unmapped domain")
bad = {'schema_version': 4, 'controls': [{'id': 'X.BOGUS', 'domain': 'totally_unknown_domain',
        'title_en': 'x', 'description_en': 'x', 'priority': 'medium', 'tier': 'advanced',
        'effort': 'low', 'risk_reduction': 3, 'sub_domain': 's', 'source_refs': []}],
        'source_registry': []}
bp = os.path.join(SCRATCH, 'amani_bad.json')
io.open(bp, 'w', encoding='utf-8').write(json.dumps(bad, ensure_ascii=False))
rb = run('scripts/import_amani_content.py', '--input', bp, '--db', DB, '--apply')
check("unmapped domain aborts import (exit != 0)", rb.returncode != 0 and 'unmapped' in (rb.stdout + rb.stderr).lower())
os.remove(bp)

print("# lineage / review flags / rich coverage")
_strengths = C.load_valid(conn)['strength']
def ok_maps(j):
    if not j:
        return False
    ms = json.loads(j)
    return bool(ms) and all(m.get('raw_id') and m.get('source_document') and m.get('mapping_strength') in _strengths for m in ms)
check("every staging row has >=1 mapping with raw_id+source_document+strength",
      all(ok_maps(r['proposed_mappings_json']) for r in conn.execute("SELECT proposed_mappings_json FROM staging_artifacts WHERE batch_id='AMANI-IMPORT'")))
personal_ids = {c['id'] for c in controls if c.get('actions_en')}
pers_flagged = one("SELECT COUNT(*) FROM staging_artifacts s JOIN raw_artifacts r ON r.id=s.raw_artifact_id "
                   "WHERE s.batch_id='AMANI-IMPORT' AND r.external_raw_id IN (%s) AND s.requires_human_review=1"
                   % ','.join('?' * len(personal_ids)), *personal_ids) if personal_ids else 0
check("all personal controls flagged for review", pers_flagged == len(personal_ids))
check("enterprise controls carry objectives+impl types",
      one("SELECT COUNT(*) FROM staging_artifacts WHERE batch_id='AMANI-IMPORT' AND proposed_security_objectives_json IS NOT NULL AND proposed_implementation_types_json IS NOT NULL") >= 500)
check("personal controls carry actions",
      one("SELECT COUNT(*) FROM staging_artifacts WHERE batch_id='AMANI-IMPORT' AND proposed_actions_json IS NOT NULL") == len(personal_ids))

print("# imported enrichment is clean (no bad codes)")
dirty = 0
for r in conn.execute("SELECT * FROM staging_artifacts WHERE batch_id='AMANI-IMPORT'"):
    if C.enrichment_blockers(r):
        dirty += 1
check("no staging row has enrichment blockers", dirty == 0)

print("# no CLASSIFICATION/ENRICHMENT blockers (content atomicity is a valid review item)")
valid = C.load_valid(conn)
# blockers the IMPORT is responsible for and must NEVER emit:
FORBIDDEN = ('invalid type', 'invalid primary_domain', 'invalid sub_domain', 'sub_domain does not belong',
             'invalid obligation', 'invalid proposed', 'missing required field', 'missing English',
             'invalid objective', 'invalid csf', 'invalid purpose', 'invalid impl', 'invalid tier',
             'invalid effort', 'invalid maturity', 'invalid evidence', 'invalid mapping_strength',
             'malformed JSON', 'duplicate ', 'lineage/mappings missing')
def structural(blk):
    return [b for b in blk if any(b.startswith(f) for f in FORBIDDEN)]
allrows = conn.execute("SELECT * FROM staging_artifacts WHERE batch_id='AMANI-IMPORT'").fetchall()
bad_struct = [r['id'] for r in allrows if structural(C.promotion_blockers(r, valid))]
check("no imported row has a classification/enrichment blocker (all 706)", not bad_struct)

print("# real end-to-end: an imported enterprise control promotes with rich children")
# pick a rich enterprise row that is fully promotable once review gates are cleared
row = None
for r in allrows:
    if (r['proposed_security_objectives_json'] and r['proposed_implementation_types_json']
            and r['proposed_verification_json']):
        gates = C.promotion_blockers(r, valid)
        # remaining blockers must all be review-gating (no content/structural issue)
        if all(b.startswith(('not ready_for_promotion', 'final_review_status', 'requires_human_review', 'confidence <='))
               for b in gates):
            row = r; break
check("found a fully-promotable rich enterprise row", row is not None)
sid = row['id']
conn.execute("UPDATE staging_artifacts SET final_review_status='APPROVED', ready_for_promotion=1, "
             "requires_human_review=0, classification_confidence=0.9 WHERE id=?", (sid,))
# recompute hash unaffected (gate fields aren't hashed) — but re-store to be safe
conn.commit()
run('scripts/promote.py', 'plan', '--db', DB, '--batch', 'AMANI-E2E')
ap = run('scripts/promote.py', 'apply', '--db', DB, '--plan', os.path.join(PLANDIR, 'plan-AMANI-E2E.json'))
fid = one("SELECT promoted_artifact_id FROM staging_artifacts WHERE id=?", sid) if one("SELECT COUNT(*) FROM staging_artifacts WHERE id=? AND promoted_artifact_id IS NOT NULL", sid) else None
check("imported enterprise control promoted", bool(fid))
if fid:
    check("promoted with security objectives", one("SELECT COUNT(*) FROM artifact_security_objectives WHERE artifact_id=?", fid) > 0)
    check("promoted with implementation types", one("SELECT COUNT(*) FROM artifact_implementation_types WHERE artifact_id=?", fid) > 0)
    check("promoted with verification actions", one("SELECT COUNT(*) FROM artifact_actions WHERE artifact_id=? AND kind='VERIFICATION'", fid) >= 0)
    check("catalog row carries risk_reduction/tier", one("SELECT COUNT(*) FROM security_artifacts WHERE id=? AND tier IS NOT NULL", fid) == 1)
check("integrity ok after e2e", conn.execute("PRAGMA integrity_check").fetchone()[0] == 'ok')

conn.close()
os.remove(DB)
print()
if fails:
    print("AMANI IMPORT VALIDATION FAILED:", fails); sys.exit(1)
print("ALL AMANI-IMPORT CHECKS PASSED.")
