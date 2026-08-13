# Implementation Plan: Complete Catalog Curation

**Branch**: `agent/complete-secureguide-mobile` | **Date**: 2026-08-13 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-catalog-curation/spec.md`

## Summary

Turn the preserved SecureGuide source corpus into a reproducible minimum-valid catalog without conflating catalog readiness, human review, content enrichment, or strict USACM conformance. Extend the existing Python/SQLite build-time pipeline with a versioned field contract, normalized raw dispositions and final lineage, source manifests and rights, a conflict-safe Excel round trip, deterministic global reconciliation, and release/upgrade qualification. Build and validate a release candidate outside `mobile/assets/catalog.db`; update the bundled asset only after every applicable gate passes.

## Technical Context

**Language/Version**: Python 3.12 build-time tooling; SQLite schema 031+; Flutter/Dart runtime consumes the qualified database

**Primary Dependencies**: Python standard library, SQLite, `openpyxl==3.1.5` for the product's build-time XLSX contract; no Python dependency is added to the mobile runtime

**Storage**: SQLite is authoritative; JSON/YAML manifests and XLSX are governed interchange artifacts

**Testing**: Python `unittest`, repository validation scripts, Flutter database migration/lifecycle tests, deterministic hash comparison

**Target Platform**: Windows/Linux build hosts; Android/iOS offline mobile runtime

**Project Type**: Offline-first mobile application with build-time catalog tooling

**Performance Goals**: Measure and compare catalog search, profile dashboard, report generation, startup/open, database size, memory, migration duration, and integrity on declared target profiles; enforce only evidence-backed existing budgets

**Constraints**: No direct curation writes to `mobile/assets/catalog.db`; no physical deletion by workbook omission; no invented provenance; controlled USACM/SDT values; profile data preserved; deterministic release construction

**Scale/Scope**: 4,265 preserved raw records currently in `catalog_work.db`; 1,467 staged curated/Amani candidates; existing unified projection of 1,223 candidate canonicals; all eight SDT domains

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

- **Offline-first / no production Python**: PASS. Python remains build-time only; the runtime receives SQLite and embedded migrations.
- **SQLite authority**: PASS. XLSX is an interchange format and never becomes the system of record.
- **Catalog/profile separation**: PASS. New schema is reference/curation metadata; operational profile rows are read only during qualification and upgrade.
- **Data preservation**: PASS BY DESIGN. Migrations are additive, raw records and stable IDs are protected, and release qualification includes a populated upgrade fixture.
- **Behavioral parity**: PASS. Mobile read models are unchanged; any schema embedding is regenerated and existing parity gates remain applicable.
- **Simplicity**: PASS. Reuse current ingestion, promotion, migration, and release components; add only missing semantic entities and one workbook CLI.
- **Definition of Done**: PENDING EXECUTION. Each phase has explicit tests and a final clean rebuild/upgrade gate.

## Project Structure

### Documentation (this feature)

```text
specs/002-catalog-curation/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
└── tasks.md
```

### Source Code (repository root)

```text
config/
├── catalog_minimum_fields.yaml
├── source_manifest.json
└── source_rights.yaml

migrations/
├── 031_catalog_closure_foundation.sql
└── 032_catalog_workbook_audit.sql

secureguide/
├── catalog_validation.py
├── catalog_workbook.py
└── catalog_curation.py

scripts/
├── catalog_validate.py
├── catalog_workbook.py
├── curate_complete_catalog.py
├── build_release_db.py
└── benchmark_release_catalog.py

consolidation/
├── unified/equivalence.json
├── curation_checkpoint.json
└── release_catalog.json

tests/
├── test_catalog_closure_schema.py
├── test_catalog_validation.py
├── test_catalog_workbook.py
├── test_complete_catalog_curation.py
├── test_release_build.py
├── test_catalog_upgrade.py
└── test_performance_benchmark.py

mobile/
├── lib/core/database/generated_migrations.dart
└── test/catalog_upgrade_test.dart
```

**Structure Decision**: Keep catalog curation in the existing Python build-time layer, persist governed facts in normalized SQLite migrations, and expose one thin CLI per workflow. Do not add a server or runtime dependency.

## Complexity Tracking

No constitution violations require justification.
