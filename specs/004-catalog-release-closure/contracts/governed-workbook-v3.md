# Contract: Governed Catalog Workbook v3

## Modes

- `COMPLETE`: contains every canonical artifact, every normalized dependent record, and every raw disposition in the candidate database.
- `FILTERED`: contains canonical artifacts matching all supplied filters and the dependent records needed to explain them. It records filters and scoped counts in the manifest.

Supported filters are artifact type, primary domain, sub-domain, source catalog/framework, quality/review state, and publication state. Empty filters are rejected in `FILTERED` mode.

## Required leading sheets

1. `00_Manifest`
2. `01_Artifacts`
3. `02_Source_Lineage`
4. `03_Framework_Mappings`
5. `04_Relationships`
6. `05_Tags`
7. `06_Applicability`
8. `07_Verification`
9. `08_External_References`
10. `09_Raw_Dispositions`

All remaining normalized tables follow in stable numeric order. Legacy-source sheets use neutral names.

## Round-trip rules

1. Headers and controlled values are schema-versioned and validated.
2. Complete export followed by unchanged import and re-export MUST preserve all governed database values and counts.
3. The importer MUST fail on unknown columns where loss would occur, duplicate primary keys, invalid enums, broken foreign keys, disposition gaps, invalid SDT pairs, or edited manifest hashes without an explicit accepted change package.
4. Formula cells are not authoritative data.
5. Repeatable structures remain rows in their normalized sheets, never comma-separated cells or duplicated JSON columns.
6. Filtered imports MAY update only artifacts declared in their manifest scope and MUST NOT imply completeness for the global raw ledger.

## Manifest requirements

The manifest records contract/tool versions, export mode, filter JSON, quality profile, source/rights/minimum-contract hashes, database content hash, generated timestamp, artifact/raw/disposition/lineage counts, and every sheet row count.

