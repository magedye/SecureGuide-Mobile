# Quickstart: Complete Catalog Curation

Run from the repository root. All paths are project-relative.

## 1. Prepare and reconcile an isolated working database

```powershell
python -m scripts.curate_complete_catalog `
  --base-db catalog.db `
  --db dist/catalog-curation-working.db `
  --checkpoint dist/catalog-curation-checkpoint.json `
  --validation dist/catalog-validation-final.json
```

Never use `mobile/assets/catalog.db` as a curation target.

## 2. Apply schema and validate the contract

```powershell
python -m scripts.catalog_validate --db dist/catalog-curation-working.db --output dist/catalog-validation-final.json --require-strict
```

Expected: 1,227 of 1,227 minimum-valid and strict-conformant canonicals,
complete closure, and zero integrity or foreign-key findings.

## 3. Verify the Excel round trip

```powershell
python -m scripts.catalog_workbook export --db dist/catalog-curation-working.db --workbook dist/catalog-curation.xlsx --actor Codex
python -m scripts.catalog_workbook validate --db dist/catalog-curation-working.db --workbook dist/catalog-curation.xlsx --annotated-workbook dist/catalog-curation.validated.xlsx --output dist/catalog-curation-workbook-validation.json
python -m scripts.catalog_workbook plan --db dist/catalog-curation-working.db --workbook dist/catalog-curation.validated.xlsx --output dist/catalog-curation-plan.json
python -m scripts.catalog_workbook apply --plan dist/catalog-curation-plan.json --actor Codex
```

An unchanged workbook plans zero mutations. Omitted rows are not deleted.

## 4. Build and qualify a release candidate

```powershell
python -m scripts.build_release_db --mode curated --output dist/secureguide-catalog-rc.db
python -m scripts.benchmark_release_catalog --database dist/secureguide-catalog-rc.db --mode qualification --output dist/performance-qualification.json
```

The curated builder independently reconstructs from the pinned release source;
it does not trust the mutable working database as a release input.

## 5. Qualify catalog upgrade and populated-install preservation

```powershell
python -m unittest tests.test_catalog_upgrade -v
Copy-Item -LiteralPath catalog.db -Destination dist/catalog-installed-upgrade.db
python -m scripts.catalog_upgrade `
  --installed-db dist/catalog-installed-upgrade.db `
  --candidate-db dist/secureguide-catalog-rc.db `
  --actor Codex `
  --output dist/catalog-upgrade-result.json
```

The focused test seeds two profiles, three selected ضوابط, one assessment, one
evidence record, and one exception, then proves snapshot preservation and
rollback. The CLI command is an additional smoke application against a copied
predecessor database.

## 6. Run upgrade and project gates

```powershell
python -m unittest discover -s tests -v
Set-Location mobile
flutter test
Set-Location ..
```

Update the bundled asset only after release, upgrade, integrity, and performance qualification pass.
