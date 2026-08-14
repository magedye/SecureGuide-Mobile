# Implementation Plan: Catalog Release Closure

**Branch**: `agent/complete-secureguide-mobile` | **Date**: 2026-08-14 | **Spec**: `specs/004-catalog-release-closure/spec.md`

**Input**: Feature specification from `/specs/004-catalog-release-closure/spec.md`

## Summary

Close the catalog release by replacing legacy source-biased classification with a pinned, deterministic semantic classification set; applying a forward-only neutral identity migration with stable aliases; formalizing minimum-valid versus strict/enriched quality profiles; extending the governed workbook with complete raw dispositions and filters; and proving deterministic release builds plus operational-data-preserving upgrades. The production runtime remains Flutter/Dart with embedded SQLite; Python remains build, curation, migration, validation, and export tooling only.

## Technical Context

**Language/Version**: Python 3.12 for build tooling; Dart 3.11 / Flutter 3.41.1 for the mobile runtime; SQL compatible with the repository SQLite migration runner

**Primary Dependencies**: Python standard library, PyYAML 6.0.3, openpyxl 3.1.5; Flutter `sqflite`, `sqlite3`, `crypto`, `file_picker`

**Storage**: SQLite is authoritative; JSON/YAML are versioned source, classification, rights, and contract inputs; XLSX is the governed human-review interchange format

**Testing**: Python `unittest`; SQLite validation queries and reproducibility hashes; Dart/Flutter unit, widget, and integration tests; GitHub Actions release compiles

**Target Platform**: Offline Android and iOS mobile runtime; deterministic catalog build tooling on Windows and Linux CI

**Project Type**: Mobile application plus repository-local catalog curation and release toolchain

**Performance Goals**: Export/import the complete current catalog without information loss; release builds produce identical catalog content hashes from identical committed inputs; upgrade remains transactional at current catalog scale

**Constraints**: No Python or network dependency in production; foreign keys enabled; USACM and SDT controlled values; one primary domain/sub-domain; raw lineage preserved; profile operational state preserved during catalog replacement; no silent classifier regeneration

**Scale/Scope**: At least 1,000 canonical artifacts and all imported raw records; current evidence baseline is 1,227 canonical artifacts and 4,265 raw records across 23 source catalogs

## Constitution Check

*GATE: Passed before Phase 0 research and re-checked after Phase 1 design.*

| Principle | Design evidence | Result |
|---|---|---|
| Offline-first / no sidecars | Runtime consumes a packaged SQLite asset; Python tools execute before packaging | PASS |
| SQLite datastore | Schema changes are forward migrations and catalog release output is SQLite | PASS |
| Reference/operational separation | Catalog replacement snapshots and restores profile tables; no operational state is moved to `security_artifacts` | PASS |
| Data preservation | Old artifact IDs are resolved through a versioned alias table during transactional upgrade | PASS |
| Behavioral parity | Generated Dart migrations are checked against SQL migrations; upgrade is covered in Python and Flutter tests | PASS |
| Localization | Stable codes remain storage values; this feature changes no localized labels | PASS |
| Simplicity | One pinned classification file, one minimum contract, one workbook contract, and one release path remain authoritative | PASS |
| Specification supremacy | Implementation and validation map to FR/SC identifiers in the active feature | PASS |

No constitutional exception is required.

## Project Structure

### Documentation (this feature)

```text
specs/004-catalog-release-closure/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── catalog-identity-upgrade-v1.md
│   └── governed-workbook-v3.md
├── checklists/requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
config/
├── catalog_minimum_fields.yaml
├── source_manifest.json
└── source_rights.yaml

consolidation/
├── curated/
│   ├── classifications.json
│   └── legacy_classifications.json
└── unified/equivalence.json

migrations/
└── 034_neutral_catalog_identity.sql

secureguide/
├── catalog_curation.py
├── catalog_release.py
├── catalog_upgrade.py
├── catalog_workbook.py
├── semantic_classification.py
└── validation.py

scripts/
├── rebuild_legacy_classifications.py
├── build_release_db.py
├── export_catalog_workbook.py
├── import_catalog_workbook.py
└── validate_catalog_release.py

mobile/
├── assets/catalog.db
├── lib/core/database/
└── test/

tests/
├── test_catalog_curation.py
├── test_catalog_release.py
├── test_catalog_upgrade.py
├── test_catalog_workbook.py
└── test_semantic_classification.py
```

**Structure Decision**: Preserve the existing repository split. Python modules produce governed, deterministic artifacts; SQL migrations define the normative store; generated Dart mirrors migrations; Flutter ships and upgrades the resulting SQLite catalog without a Python runtime.

## Complexity Tracking

No constitution violations require justification.

