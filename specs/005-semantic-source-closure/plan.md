# Implementation Plan: Semantic Source Closure

**Branch**: `agent/complete-secureguide-mobile` | **Date**: 2026-08-14 | **Spec**: [spec.md](spec.md)

**Input**: Owner-authorized semantic and source-coverage closure of the Minimum Valid Catalog.

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Replace the current bulk default reconciliation of unclassified source records with a pinned, deterministic all-corpus decision ledger. Reconcile the complete raw corpus against existing canonicals first, apply independently governed semantic corrections, persist record-specific disposition and lineage evidence, validate semantic closure, and qualify an isolated candidate before replacing the shipped asset.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.12 curation toolchain; Dart/Flutter mobile runtime.

**Primary Dependencies**: Standard-library SQLite curation pipeline, PyYAML/OpenPyXL curation dependencies, Flutter/Dart offline database runtime.

**Storage**: SQLite with additive migrations; JSON/YAML pinned source and decision inputs; XLSX governed workbook.

**Testing**: Python unittest suite, deterministic release validators, Flutter unit/widget/integration tests, GitHub Actions Android/iOS compile gates.

**Target Platform**: Offline Android and iOS runtime; Windows curation workstation; Linux/macOS CI qualification.

**Project Type**: Offline-first mobile application with deterministic catalog build/curation tooling.

**Performance Goals**: Preserve the established candidate-query and upgrade budget while processing all 4,265 raw source records deterministically.

**Constraints**: No production Python runtime; no direct production asset mutation before qualification; preserve profile isolation, aliases, raw records, source rights, and workbook round-trip integrity.

**Scale/Scope**: Current baseline is 4,265 raw records, 1,218 canonicals, 1,473 lineage rows, and 959 aliases across 23 pinned source manifests.

## Constitution Check

*GATE: Passed before Phase 0 research; rechecked after Phase 1 design.*

| Principle | Plan response | Status |
|---|---|---|
| Offline-first / SQLite authority | All reconciliation and qualification occur against isolated SQLite candidates; the mobile runtime remains offline. | PASS |
| No Python in production / no sidecars | Python remains build-time tooling only; no mobile runtime dependency or service is added. | PASS |
| Data separation | Only reference catalog and governed curation structures are changed; profile operational data is preserved and upgrade-tested. | PASS |
| Data preservation | Raw records, lineage, aliases, and installed operational data are additive or compatibility-protected. | PASS |
| Behavioral parity | Any curation-to-mobile schema change receives generated migration parity and upgrade verification. | PASS |
| Evidence integrity | Inputs, decision ledger, candidate hashes, reports, and workbook manifests are deterministic and SHA-bound. | PASS |
| Multi-platform and localization | Existing Flutter/runtime gates remain; no Arabic translation is made a closure blocker. | PASS |
| Simplicity | Extend existing curation, validation, release, upgrade, and workbook paths instead of introducing a parallel catalog model. | PASS |

## Project Structure

### Documentation (this feature)

```text
specs/005-semantic-source-closure/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
secureguide/
├── catalog_curation.py             # source ingestion, projection, reconciliation
├── semantic_classification.py      # deterministic per-record semantic decisions
├── catalog_validation.py           # Minimum/strict/closure validation
├── catalog_workbook.py             # complete and filtered governed workbook
└── catalog_upgrade.py               # transactional installed-catalog replacement

scripts/
├── build_release_db.py              # isolated curated candidate construction
├── validate_catalog_release.py      # V1-V4 qualification
├── catalog_workbook.py              # export, validate, plan, apply CLI
└── rebuild_*                        # deterministic decision/equivalence builders

config/
├── source_manifest.json
├── source_rights.yaml
└── semantic_reconciliation_ledger.json

migrations/
└── 035_semantic_reconciliation_closure.sql

tests/
├── test_semantic_classification.py
├── test_complete_catalog_curation.py
├── test_catalog_validation.py
├── test_catalog_workbook.py
├── test_catalog_reconciliation.py
├── test_catalog_identity.py
└── test_catalog_upgrade.py

mobile/
├── lib/core/database/generated_migrations.dart
└── test/catalog_upgrade_test.dart
```

**Structure Decision**: Extend the established deterministic curation path and normalized SQLite model. The semantic decision ledger is a pinned input; the reconciliation-link table makes non-lineage outcomes queryable and foreign-key verifiable without storing repeatable structures in artifact JSON.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | Existing catalog layers, migrations, and workbook contract are sufficient. |
