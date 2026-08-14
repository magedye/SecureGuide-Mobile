# Quickstart: Semantic Source Closure Qualification

1. Preserve `mobile/assets/catalog.db`; make an isolated work directory for candidates and evidence.
2. Install curation dependencies with `py -3 -m pip install -r requirements-curation.txt`.
3. Run focused semantic, curation, validation, workbook, identity, and upgrade tests after each implementation increment.
4. Build two isolated full-corpus candidates using `py -3 -m scripts.build_release_db --mode curated --output <candidate>.db`.
5. Validate candidate A against candidate B with `py -3 -m scripts.validate_catalog_release --db <candidate-a>.db --comparison-db <candidate-b>.db --output <validation>.json`.
6. Export, validate, plan, and apply an unchanged complete workbook only against candidate copies; prove zero catalog mutations and equal state hashes.
7. Run generated-migration parity, mobile-runtime boundary, Flutter format/analyze/test, Android release compile, and CI iOS unsigned compile where the platform is available.
8. Replace the shipped asset only through the existing verified release path after all applicable checks pass.
