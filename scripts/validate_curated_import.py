# -*- coding: utf-8 -*-
"""Gate for the curated (Excel) import on catalog_work.db: the 761 controls are
in staging as reviewable, SADP-conformant candidates. Asserts counts, lineage,
enum validity, no tags, all NEEDS_REVIEW/not-promoted, and writes a distribution
summary to consolidation/curated/DISTRIBUTION.md."""
import io
import json
import os
import re
import sqlite3
import sys
from collections import Counter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import _promote_common as C

DB = os.environ.get('CURATED_DB', os.path.join(ROOT, 'catalog_work.db'))
DIST = os.path.join(ROOT, 'consolidation', 'curated', 'DISTRIBUTION.md')
BATCH = 'CURATED-IMPORT'
fails = []


def check(n, c):
    print(("PASS" if c else "FAIL"), "-", n)
    if not c:
        fails.append(n)


conn = sqlite3.connect(DB); conn.row_factory = sqlite3.Row
conn.execute("PRAGMA foreign_keys=ON")
valid = C.load_valid(conn)


def one(q, *p):
    return conn.execute(q, p).fetchone()[0]


raw_n = one("SELECT COUNT(*) FROM raw_artifacts WHERE source_catalog_id='securekit_curated_controls'")
rows = conn.execute(f"SELECT * FROM staging_artifacts WHERE batch_id='{BATCH}'").fetchall()
stg_n = len(rows)

print("# counts + lineage")
check("761 curated raw", raw_n == 761)
check("staging rows loaded (== raw)", stg_n == raw_n)
check("every staging links to a real raw",
      one(f"SELECT COUNT(*) FROM staging_artifacts s WHERE s.batch_id='{BATCH}' AND NOT EXISTS (SELECT 1 FROM raw_artifacts r WHERE r.id=s.raw_artifact_id)") == 0)


def maps_ok(j):
    try:
        m = json.loads(j) if j else []
    except Exception:
        return False
    return bool(m) and all(x.get('raw_id') and x.get('source_document') and x.get('mapping_strength') in valid['strength'] for x in m)


check("every row has DIRECT lineage mapping", all(maps_ok(r['proposed_mappings_json']) for r in rows))

print("# SADP conformance")
check("zero tags (SADP §2.4)", all(not r['proposed_tags_json'] for r in rows))
check("all NEEDS_REVIEW", all(r['curation_status'] == 'NEEDS_REVIEW' for r in rows))
check("none ready_for_promotion", all(r['ready_for_promotion'] == 0 for r in rows))
# every stored enum value is valid-or-null (loader guarantees; verify)
badenum = []
for r in rows:
    for field, key in (('proposed_type', 'type'), ('proposed_abstraction_level', 'abs'),
                       ('proposed_primary_domain', 'dom'), ('proposed_sub_domain', 'sub'),
                       ('proposed_obligation_level', 'obl'), ('proposed_requirement_type', 'rqt'),
                       ('proposed_control_nature', 'nat'), ('proposed_control_function', 'fun'),
                       ('proposed_testability', 'tst'), ('proposed_priority', 'priority')):
        v = r[field]
        if v is not None and v not in valid[key]:
            badenum.append((r['id'], field, v))
    for t in (json.loads(r['proposed_threats_json']) if r['proposed_threats_json'] else []):
        if t['threat_code'] not in valid['threat']:
            badenum.append((r['id'], 'threat', t['threat_code']))
check(f"no invalid enum stored ({badenum[:3]})", not badenum)

print("# classification quality (informational)")
complete = sum(1 for r in rows if r['proposed_type'] and r['proposed_primary_domain'] and r['proposed_sub_domain'])
generated_group_note = re.compile(
    r"\s*\[(?:canonical of [^\]]+|duplicate in [^\]]+|unified-group [^\]]+)\]",
    flags=re.IGNORECASE,
)
fixups = sum(1 for r in rows if generated_group_note.sub('', r['review_notes'] or '').strip())
conf = [r['classification_confidence'] for r in rows if r['classification_confidence'] is not None]
avgconf = round(sum(conf) / len(conf), 3) if conf else 0
check("majority fully classified (type+domain+sub)", complete >= stg_n * 0.8)
print(f"  fully-classified={complete}/{stg_n}  rows-with-fixup-notes={fixups}  avg_confidence={avgconf}")

# distribution
types = Counter(r['proposed_type'] or '(null)' for r in rows)
doms = Counter(r['proposed_primary_domain'] or '(null)' for r in rows)
pris = Counter(r['proposed_priority'] or '(null)' for r in rows)
thr = Counter()
for r in rows:
    for t in (json.loads(r['proposed_threats_json']) if r['proposed_threats_json'] else []):
        thr[t['threat_code']] += 1

md = ["# Curated Controls — Classification Distribution", "",
      f"Source: `SecureGuide Curated Controls v1` · {stg_n} controls · batch `{BATCH}` (all NEEDS_REVIEW).",
      f"Fully classified (type+domain+sub): **{complete}/{stg_n}** · rows flagged for fixup: **{fixups}** · avg confidence: **{avgconf}**.",
      "", "## USACM type", "", "| type | count |", "|---|---|"]
md += [f"| {k} | {v} |" for k, v in types.most_common()]
md += ["", "## SDT primary domain", "", "| domain | count |", "|---|---|"]
md += [f"| {k} | {v} |" for k, v in sorted(doms.items())]
md += ["", "## Priority", "", "| priority | count |", "|---|---|"]
md += [f"| {k} | {v} |" for k, v in sorted(pris.items())]
md += ["", "## Threats (THR-*)", "", "| threat | count |", "|---|---|"]
md += [f"| {k} | {v} |" for k, v in thr.most_common()]
io.open(DIST, 'w', encoding='utf-8', newline='\n').write("\n".join(md) + "\n")
print(f"  wrote distribution -> {DIST}")

check("integrity ok", conn.execute("PRAGMA integrity_check").fetchone()[0] == 'ok')
check("production catalog untouched (working DB only)", one("SELECT COUNT(*) FROM security_artifacts") == 4)

print()
if fails:
    print("CURATED IMPORT VALIDATION FAILED:", fails); sys.exit(1)
print("ALL CURATED-IMPORT CHECKS PASSED.")
