# Catalog Workbook Contract v1

## Commands

```text
catalog_workbook export   --db <working.db> --out <catalog.xlsx>
catalog_workbook validate --db <working.db> --workbook <catalog.xlsx> --out <validated.xlsx>
catalog_workbook plan     --db <working.db> --workbook <validated.xlsx> --out <plan.json> --actor <name>
catalog_workbook apply    --db <working.db> --plan <plan.json> --actor <name> [--resolution <resolution.json>]
```

Mutating commands reject a resolved target equal to `mobile/assets/catalog.db`.

## Required sheets

`00_Manifest`, `01_Artifacts`, `02_Source_Lineage`, `03_Framework_Mappings`, `04_Relationships`, `05_Tags`, `06_Type_Specific`, `07_Reference_Lists`, `08_Validation_Errors`.

## Editable-row envelope

Every editable row includes `row_key`, `row_version`, `baseline_hash`, and `action`. Actions are `NO_CHANGE`, `UPSERT`, and `DEPRECATE`.

- Omitted row: no comparison and no mutation.
- `NO_CHANGE`: proposed semantic hash equals baseline.
- `UPSERT`: whitelisted insert or update while preserving immutable IDs and passing validation.
- `DEPRECATE`: only on `01_Artifacts`; sets publication to `DEPRECATED` and inactive without deletion.

## Conflict rules

- Changed database baseline or row hash produces `CONFLICT`.
- Conflicting rows never apply automatically.
- A resolution identifies each row, expected current hash, actor, and reason.
- Resolved changes still undergo complete validation inside the transaction.
- Any failure rolls back the complete batch.

## Hashing

Semantic hashes use UTF-8 canonical JSON, Unicode NFC, sorted keys, explicit nulls, and fixed fields. Formatting, export time, formulas, and comments are excluded. Formula cells in editable data are errors.

## Validation errors

`08_Validation_Errors` contains severity, code, sheet, workbook row, row key, field, message, and current database hash. Any `ERROR` blocks plan/apply.
