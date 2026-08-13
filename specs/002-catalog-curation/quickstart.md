# Quickstart: Complete Catalog Curation

Run from the repository root. All paths are project-relative.

## 1. Prepare an isolated working database

```powershell
Copy-Item -LiteralPath catalog_work.db -Destination dist/catalog-curation-working.db
```

Never use `mobile/assets/catalog.db` as a curation target.

## 2. Apply schema and validate the contract

```powershell
py -3 -m scripts.catalog_validate --db dist/catalog-curation-working.db --output dist/catalog-validation-before.json
```

Expected: separate minimum and strict results plus explicit closure gaps.

## 3. Verify the Excel round trip

```powershell
py -3 -m scripts.catalog_workbook export --db dist/catalog-curation-working.db --out dist/catalog-curation.xlsx
py -3 -m scripts.catalog_workbook validate --db dist/catalog-curation-working.db --workbook dist/catalog-curation.xlsx --out dist/catalog-curation.validated.xlsx
py -3 -m scripts.catalog_workbook plan --db dist/catalog-curation-working.db --workbook dist/catalog-curation.validated.xlsx --out dist/catalog-curation-plan.json --actor Codex
py -3 -m scripts.catalog_workbook apply --db dist/catalog-curation-working.db --plan dist/catalog-curation-plan.json --actor Codex
```

An unchanged workbook plans zero mutations. Omitted rows are not deleted.

## 4. Curate and reconcile the corpus

```powershell
py -3 -m scripts.curate_complete_catalog --db dist/catalog-curation-working.db --equivalence consolidation/unified/equivalence.json --checkpoint dist/catalog-curation-checkpoint.json
py -3 -m scripts.catalog_validate --db dist/catalog-curation-working.db --output dist/catalog-validation-final.json
```

Expected: 100 percent dispositions, complete canonical lineage, zero dangling references, and SD-01 through SD-08 checkpoint results.

## 5. Build and qualify a release candidate

```powershell
py -3 -m scripts.build_release_db --mode curated --release-source dist/catalog-curation-working.db --output dist/secureguide-catalog-rc.db
py -3 -m scripts.benchmark_release_catalog --database dist/secureguide-catalog-rc.db --mode qualification --output dist/performance-qualification.json
```

## 6. Run upgrade and project gates

```powershell
py -3 -m unittest discover -s tests -v
Set-Location mobile
flutter test
Set-Location ..
```

Update the bundled asset only after release, upgrade, integrity, and performance qualification pass.
