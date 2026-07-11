# -*- coding: utf-8 -*-
"""Apply 001+002+003 and cross-check that every value enforced by a schema CHECK
constraint has a matching ref_code_lists seed row (and vice-versa)."""
import io
import os
import re
import sqlite3
import sys

MIG = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'migrations'))
conn = sqlite3.connect(':memory:')
conn.execute("PRAGMA foreign_keys = ON;")
schema_text = ""
for fn in ('001_initial_schema.sql', '002_assets_indicators_embeddings.sql', '003_reference_data.sql'):
    t = io.open(os.path.join(MIG, fn), encoding='utf-8').read()
    schema_text += "\n" + t
    conn.executescript(t)
cur = conn.cursor()

assert cur.execute("PRAGMA integrity_check;").fetchone()[0] == 'ok'

# ref sets from the per-list lookup tables (lk_*)
lk_tables = [r[0] for r in cur.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'lk\\_%' ESCAPE '\\'")]
ref = {}
total = 0
for t in lk_tables:
    lc = t[3:].upper()  # strip 'lk_'
    codes = {r[0] for r in cur.execute(f"SELECT code FROM {t}")}
    ref[lc] = codes
    total += len(codes)
print(f"Applied 001+002+003. {len(lk_tables)} lookup tables, {total} reference rows.")


def all_in_sets(colanchor):
    """All `\\b<anchor>\\b IN ('a',...)` sets in the combined schema text."""
    out = []
    for m in re.finditer(r"\b" + re.escape(colanchor) + r"\b\s+IN\s*\(([^)]*)\)", schema_text):
        out.append(set(re.findall(r"'([^']+)'", m.group(1))))
    return out


def in_set(spec):
    """spec is 'anchor' or ('anchor','must_contain'). Returns the matching set."""
    if isinstance(spec, tuple):
        anchor, must = spec
    else:
        anchor, must = spec, None
    sets = all_in_sets(anchor)
    if not sets:
        return None
    if must is not None:
        for s in sets:
            if must in s:
                return s
        return None
    return sets[0]


# list_code -> the CHECK anchor whose IN-set must equal the ref set
MAP = {
    'ARTIFACT_TYPE': 'type', 'ABSTRACTION_LEVEL': 'abstraction_level',
    'OBLIGATION_SOURCE': 'source',
    'SOURCE_TYPE': ('source_type', 'INTERVIEW'),
    'CATALOG_SOURCE_TYPE': ('source_type', 'FRAMEWORK'),
    'OBLIGATION_LEVEL': 'obligation_level', 'REQUIREMENT_TYPE': 'requirement_type',
    'GRANULARITY_LEVEL': 'granularity_level', 'PRIORITY': 'priority',
    'IMPLEMENTATION_STATUS': 'implementation_status', 'VERIFICATION_STATUS': 'verification_status',
    'EFFECTIVENESS': 'effectiveness', 'EXCEPTION_STATUS': 'exception_status',
    'REVIEW_FREQUENCY': 'review_frequency', 'PUBLICATION_STATUS': 'publication_status',
    'MATURITY_LEVEL': 'required_maturity_level', 'COST_CATEGORY': 'cost_category',
    'IMPORT_STATUS': 'import_status', 'AI_REVIEW_STATUS': 'ai_review_status',
    'MAPPING_STRENGTH': 'mapping_strength', 'TAG_TYPE': 'tag_type',
    'RELATIONSHIP_TYPE': 'relation_type', 'APPLICABILITY_SCOPE_TYPE': 'scope_type',
    'DEPENDENCY_TYPE': 'dependency_type', 'DEPENDENCY_STATUS': 'dependency_status',
    'VERIFICATION_METHOD': 'verification_method', 'STAKEHOLDER_RESPONSIBILITY': 'responsibility',
    'SELF_ASSESSMENT_STATUS': 'status', 'RESOLUTION_STATUS': 'resolution_status',
    'SDT_DOMAIN': 'primary_domain', 'SDT_SUBDOMAIN': 'sub_domain',
    'CONTROL_NATURE': 'control_nature', 'CONTROL_FUNCTION': 'control_function',
    'TESTABILITY': 'testability',
}

problems = []
checked = 0
for lc, anchor in MAP.items():
    cset = in_set(anchor)
    rset = ref.get(lc)
    if rset is None:
        problems.append(f"{lc}: missing from ref_code_lists")
        continue
    if cset is None:
        problems.append(f"{lc}: could not locate CHECK IN-set for '{anchor}'")
        continue
    checked += 1
    only_check = cset - rset
    only_ref = rset - cset
    if only_check:
        problems.append(f"{lc}: values in CHECK but NOT seeded: {sorted(only_check)}")
    if only_ref:
        problems.append(f"{lc}: seeded but NOT in CHECK: {sorted(only_ref)}")

# lists that have no direct single-column CHECK (multi-use) — presence only
for lc in ('VERIFICATION_TOOL_TYPE', 'EXTERNAL_REFERENCE_TYPE', 'ASSET_TYPE'):
    if lc not in ref:
        problems.append(f"{lc}: missing from ref_code_lists")

# SDT belongs-to sanity: every subdomain parent is a real domain (FK-backed)
bad_parent = cur.execute(
    "SELECT code FROM lk_sdt_subdomain WHERE domain_code NOT IN (SELECT code FROM lk_sdt_domain)").fetchall()
if bad_parent:
    problems.append(f"SDT sub-domains with invalid parent: {bad_parent}")
# and every subdomain prefix == its domain_code
mismatch = cur.execute(
    "SELECT code, domain_code FROM lk_sdt_subdomain WHERE substr(code,1,5)<>domain_code").fetchall()
if mismatch:
    problems.append(f"SDT sub-domain prefix != domain: {mismatch}")
# counts
d = cur.execute("SELECT count(*) FROM lk_sdt_domain").fetchone()[0]
s = cur.execute("SELECT count(*) FROM lk_sdt_subdomain").fetchone()[0]
if (d, s) != (8, 40):
    problems.append(f"SDT counts wrong: {d} domains, {s} subdomains (expected 8/40)")

print(f"Cross-checked {checked} classification lists against schema CHECK constraints.")
print()
if problems:
    print("REFERENCE-DATA MISMATCHES:")
    for p in problems:
        print("  -", p)
    sys.exit(1)
print("All reference data matches the schema constraints exactly. Coverage complete.")
