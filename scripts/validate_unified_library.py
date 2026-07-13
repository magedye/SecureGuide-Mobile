# -*- coding: utf-8 -*-
"""Gate for the unified library on catalog_work.db: amani + curated candidates
merged with AI-decided equivalence groups. Asserts group integrity + SADP/no-tags
+ non-destructive/NEEDS_REVIEW state, and writes dedup stats to
consolidation/unified/UNIFIED_DISTRIBUTION.md."""
import io
import json
import os
import sqlite3
import sys
from collections import Counter, defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import _promote_common as C

DB = os.environ.get('UNIFIED_DB', os.path.join(ROOT, 'catalog_work.db'))
DIST = os.path.join(ROOT, 'consolidation', 'unified', 'UNIFIED_DISTRIBUTION.md')
BATCHES = ('AMANI-IMPORT', 'CURATED-IMPORT')
fails = []


def check(n, c):
    print(("PASS" if c else "FAIL"), "-", n)
    if not c:
        fails.append(n)


conn = sqlite3.connect(DB); conn.row_factory = sqlite3.Row
conn.execute("PRAGMA foreign_keys=ON")
rows = conn.execute("SELECT * FROM staging_artifacts WHERE batch_id IN (?,?)", BATCHES).fetchall()
by_id = {r['id']: r for r in rows}
src = {r['id']: ('amani' if r['batch_id'] == 'AMANI-IMPORT' else 'curated') for r in rows}

print("# unified pool")
check("1467 unified candidates (amani + curated)", len(rows) == 1467)
# pre-promotion state: no row is approved or ready (NEEDS_REVIEW / CLASSIFIED both fine)
check("nothing approved (final_review_status NULL)", all(not r['final_review_status'] for r in rows))
check("none ready_for_promotion", all(r['ready_for_promotion'] == 0 for r in rows))
check("all in a pre-promotion status", all(r['curation_status'] in ('NEEDS_REVIEW', 'CLASSIFIED', 'DRAFT') for r in rows))
check("no tags (SADP §2.4)", all(not r['proposed_tags_json'] for r in rows))

print("# equivalence group integrity")
groups = defaultdict(list)
for r in rows:
    if r['canonical_group_id']:
        groups[r['canonical_group_id']].append(r)
bad = []
for gid, members in groups.items():
    canon = [m for m in members if m['merge_action'] == 'CANONICALIZE']
    if len(members) < 2:
        bad.append(f"{gid}: <2 members")
    if len(canon) != 1:
        bad.append(f"{gid}: {len(canon)} canonicals (need exactly 1)")
    if not conn.execute("SELECT 1 FROM equivalence_groups WHERE id=?", (gid,)).fetchone():
        bad.append(f"{gid}: no equivalence_groups header")
check(f"every group well-formed ({bad[:3]})", not bad)
# no member in >1 group is guaranteed by canonical_group_id being single-valued per row
member_ids = [r['id'] for r in rows if r['canonical_group_id']]
check("no row in two groups (single canonical_group_id per row)", len(member_ids) == len(set(member_ids)))

print("# canonical dual lineage on cross-source groups")
xsrc_bad = 0
for gid, members in groups.items():
    srcs = {src[m['id']] for m in members}
    if len(srcs) == 2:  # cross-source group
        canon = next(m for m in members if m['merge_action'] == 'CANONICALIZE')
        maps = json.loads(canon['proposed_mappings_json']) if canon['proposed_mappings_json'] else []
        docs = {mp.get('source_document') for mp in maps}
        if len(docs) < 2:
            xsrc_bad += 1
check("cross-source canonicals carry dual lineage", xsrc_bad == 0)

check("integrity ok", conn.execute("PRAGMA integrity_check").fetchone()[0] == 'ok')
check("production catalog untouched (working DB)", conn.execute("SELECT COUNT(*) FROM security_artifacts").fetchone()[0] == 4)

# ---- stats + distribution ----
n_groups = len(groups)
n_dups = sum(len(m) - 1 for m in groups.values())        # rows collapsed into a canonical
n_xsrc = sum(1 for m in groups.values() if len({src[x['id']] for x in m}) == 2)
grouped_rows = sum(len(m) for m in groups.values())
unified_size = len(rows) - n_dups                        # canonicals + singletons
amani_n = sum(1 for r in rows if src[r['id']] == 'amani')
curated_n = len(rows) - amani_n

md = ["# Unified Library — amani + curated (deduplicated)", "",
      f"Pool: **{len(rows)}** candidates ({amani_n} amani + {curated_n} curated) on catalog_work.db, all NEEDS_REVIEW.",
      "", "## Deduplication", "",
      f"- Equivalence groups: **{n_groups}**",
      f"- Cross-source groups (amani&curated): **{n_xsrc}**",
      f"- Duplicates collapsed into a canonical: **{n_dups}**",
      f"- Rows participating in a group: **{grouped_rows}**",
      f"- **Unified library size (canonicals + standalone): {unified_size}**",
      f"- Deduplication rate: **{round(100 * n_dups / len(rows), 1)}%**", ""]
# distribution of the unified set (canonicals + ungrouped) by domain/source
canonical_or_solo = [r for r in rows if not r['canonical_group_id'] or r['merge_action'] == 'CANONICALIZE']
dom = Counter(r['proposed_primary_domain'] or '(null)' for r in canonical_or_solo)
md += ["## Unified set by SDT domain", "", "| domain | count |", "|---|---|"]
md += [f"| {k} | {v} |" for k, v in sorted(dom.items())]
md += ["", "## Group size histogram", "", "| members | groups |", "|---|---|"]
hist = Counter(len(m) for m in groups.values())
md += [f"| {k} | {v} |" for k, v in sorted(hist.items())]
io.open(DIST, 'w', encoding='utf-8', newline='\n').write("\n".join(md) + "\n")
print(f"  groups={n_groups} cross-source={n_xsrc} duplicates={n_dups} unified_size={unified_size}")
print(f"  wrote -> {DIST}")

print()
if fails:
    print("UNIFIED LIBRARY VALIDATION FAILED:", fails); sys.exit(1)
print("ALL UNIFIED-LIBRARY CHECKS PASSED.")
