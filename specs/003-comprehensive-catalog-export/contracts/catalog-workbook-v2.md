# Catalog Workbook v2 Contract

## CLI

```text
py -3 -m scripts.catalog_workbook export --db <working-or-release.db> --workbook <catalog.xlsx> --actor <name>
py -3 -m scripts.catalog_workbook validate --db <working.db> --workbook <catalog.xlsx> [--annotated-workbook <validated.xlsx>] [--output <validation.json>]
py -3 -m scripts.catalog_workbook plan --db <working.db> --workbook <validated.xlsx> --output <plan.json> [--resolutions <resolution.json>]
py -3 -m scripts.catalog_workbook apply --plan <plan.json> --actor <name>
```

## Contract Identifiers

- Workbook: `secureguide-catalog-workbook-v2`
- Plan: `secureguide-catalog-workbook-plan-v2`

## Required Worksheet Order

The first nine worksheets retain their v1 order. Comprehensive detail worksheets follow in the stable order declared by `secureguide.catalog_workbook.SHEETS`.

## Manifest

The manifest records contract/version hashes, a repository-relative database path, `ALL_CATALOG_ARTIFACTS` scope, excluded data classes, total artifact count, and one `row_count.<worksheet>` entry per editable worksheet.

## Safety

- `mobile/assets/catalog.db` cannot be an apply target.
- No physical delete operation exists.
- Workbook omissions have no effect.
- Child rows accept `NO_CHANGE` or `UPSERT` only.
- Every applied row is audited and every affected artifact is minimum-validated.
