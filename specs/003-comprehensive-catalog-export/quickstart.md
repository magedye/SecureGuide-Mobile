# Quickstart: Comprehensive Catalog Export

Run from the repository root.

## 1. Focused tests

```powershell
py -3 -m unittest tests.test_catalog_workbook tests.test_catalog_workbook_apply
```

Expected: all workbook schema, comprehensive detail, validation, conflict, audit, omission, and apply tests pass.

## 2. Export the release catalog

```powershell
py -3 -m scripts.catalog_workbook export `
  --db mobile/assets/catalog.db `
  --workbook outputs/<thread-id>/secureguide_catalog_complete.xlsx `
  --actor codex
```

Expected: workbook contract v2, every artifact, and every supported normalized detail row are exported.

## 3. Validate the unchanged export

```powershell
py -3 -m scripts.catalog_workbook validate `
  --db mobile/assets/catalog.db `
  --workbook outputs/<thread-id>/secureguide_catalog_complete.xlsx
```

Expected: `valid` is `true`, `errors` is empty, and manifest row counts reconcile with the database.

## 4. Inspect boundaries

Confirm that profile/operational sheets, raw source payload text, and embedding vectors are absent. Confirm the manifest uses `mobile/assets/catalog.db`, not an absolute workstation path.
