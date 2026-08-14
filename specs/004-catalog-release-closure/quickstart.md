# Quickstart: Catalog Release Closure

Run from the repository root with Python 3.12 and Flutter 3.41.1.

```powershell
python -m pip install -r requirements-curation.txt
python -m unittest discover -s tests -v
python -m scripts.generate_mobile_migrations
git diff --exit-code -- mobile/lib/core/database/generated_migrations.dart
```

Pinned semantic classifications are consumed by default. Rebuild them only for an intentional reviewed classifier change:

```powershell
python -m scripts.rebuild_legacy_classifications --rebuild
git diff -- consolidation/curated/legacy_classifications.json
```

Build and validate two fresh candidates to prove logical reproducibility:

```powershell
python -m scripts.build_release_db --mode release --output outputs/release-a.db
python -m scripts.build_release_db --mode release --output outputs/release-b.db
python -m scripts.validate_catalog_release --database outputs/release-a.db --profiles V1,V2,V3,V4
```

Export the complete governed workbook and a filtered review workbook:

```powershell
python -m scripts.export_catalog_workbook --database outputs/release-a.db --output outputs/catalog-complete.xlsx
python -m scripts.export_catalog_workbook --database outputs/release-a.db --output outputs/catalog-review.xlsx --artifact-type ART-CFG --quality-state HUMAN_REVIEW
```

Then run the mobile verification:

```powershell
Push-Location mobile
flutter pub get
dart format --output=none --set-exit-if-changed lib test integration_test
flutter analyze --fatal-infos --fatal-warnings
flutter test
Pop-Location
```

Release evidence is valid only for the exact committed HEAD and the recorded catalog content hash.
