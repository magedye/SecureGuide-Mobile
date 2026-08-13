# Tasks: Comprehensive Catalog Export

## Phase 1: Setup

- [x] T001 Confirm the comprehensive table boundary, worksheet names, and contract identifiers in `specs/003-comprehensive-catalog-export/contracts/catalog-workbook-v2.md`

## Phase 2: Foundational Tests

- [x] T002 [P] Write failing export tests for every supported table, full columns, composite keys, empty sheets, manifest counts, and excluded data in `tests/test_catalog_workbook.py`
- [x] T003 [P] Write failing round-trip tests for a newly supported detail row, controlled values, affected-artifact validation, child deprecation rejection, and omission safety in `tests/test_catalog_workbook_apply.py`

## Phase 3: User Story 1 - Export the Complete Master Catalog (Priority: P1)

**Goal**: Export every catalog artifact and all normalized Master Catalog details.

**Independent Test**: Seed every supported detail-table shape and reconcile exported worksheet columns and row counts with SQLite.

- [x] T004 [US1] Implement workbook v2 table registry, complete detail sheets, sheet-specific controlled lists, relative manifest metadata, and row-count reconciliation in `secureguide/catalog_workbook.py`

## Phase 4: User Story 2 - Curate Complete Details Safely (Priority: P1)

**Goal**: Extend validation, planning, apply, conflict detection, and audit to every detail sheet.

**Independent Test**: Apply a valid detail edit and reject stale, duplicate, invalid, deprecated-child, and omitted-row cases.

- [x] T005 [US2] Generalize validation, planning, current-row lookup, transactional apply, and affected-artifact resolution across every registered sheet in `secureguide/catalog_workbook.py`
- [x] T006 [US2] Keep the workbook CLI module-safe and verify all four round-trip commands in `scripts/catalog_workbook.py`

## Phase 5: Polish & Cross-Cutting Validation

- [x] T007 Document workbook v2 scope, exclusions, worksheet inventory, and migration note in `docs/CATALOG_CURATION.md`
- [x] T008 Run focused and full Python tests, export and validate the release catalog, inspect the workbook in Excel, and record the delivered file under `outputs/<thread-id>/`

## Dependencies & Execution Order

- T001 defines the boundary.
- T002 and T003 establish failing behavior tests and may proceed independently.
- T004 precedes T005 and T006.
- T007 and T008 follow successful implementation tests.

## Parallel Opportunities

- T002 and T003 touch separate test modules.
- Documentation review can begin after the contract is stable, while the release export verification remains pending.

## Implementation Strategy

1. Lock the contract and tests.
2. Add the declarative export registry.
3. Extend round-trip handling using the same registry.
4. Document, export, validate, and visually inspect the final workbook.
