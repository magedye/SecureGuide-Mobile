# Implementation Plan: Comprehensive Catalog Export

**Branch**: `agent/complete-secureguide-mobile` | **Date**: 2026-08-14 | **Spec**: [spec.md](spec.md)

## Summary

Upgrade the governed catalog workbook from its nine-sheet v1 contract to a comprehensive v2 contract. Preserve the nine established core sheets, append one normalized sheet for every in-scope Master Catalog detail table, drive export/validation/plan/apply from one table registry, expose sheet-specific controlled lists, and reconcile manifest counts against SQLite. Operational/profile tables, raw payload text, and embedding vectors remain excluded.

## Technical Context

**Language/Version**: Python 3.13 build-time tooling
**Primary Dependencies**: Python standard library, SQLite, existing `openpyxl==3.1.5` workbook dependency
**Storage**: SQLite remains authoritative; XLSX is a governed bulk-curation projection
**Testing**: `unittest` through `py -3 -m unittest`
**Target Platform**: Windows build/curation environment; generated workbook is standard XLSX
**Project Type**: Offline-first mobile application with build-time Python curation tools
**Performance Goals**: Export the 1,227-artifact release catalog and all current detail rows in one bounded run
**Constraints**: No direct apply to `mobile/assets/catalog.db`; no deletion by omission; no profile-state mixing; no raw payload export; relative repository paths; controlled USACM/SDT values
**Scale/Scope**: 1,227 catalog artifacts plus roughly 9,000 current normalized detail rows across 28 editable worksheets

## Constitution Check

- **Offline-first / no production Python**: PASS. The change is limited to existing build-time tooling.
- **SQLite authority**: PASS. XLSX remains a projection with row/database hashes and transactional apply.
- **Catalog/profile separation**: PASS. Operational and profile tables are explicitly excluded.
- **Data preservation**: PASS. Omission remains `NO_CHANGE`; child rows cannot be deprecated or physically deleted.
- **Localization**: PASS. The complete localization child table is exported.
- **Simplicity / unnecessary complexity**: PASS. A declarative table registry replaces duplicated hard-coded sheet loops.
- **Definition of done / specification supremacy**: PASS. Contract, tests, implementation, release export, and documentation are included.

## Project Structure

### Documentation (this feature)

```text
specs/003-comprehensive-catalog-export/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/catalog-workbook-v2.md
├── checklists/requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
secureguide/catalog_workbook.py
scripts/catalog_workbook.py
tests/test_catalog_workbook.py
tests/test_catalog_workbook_apply.py
docs/CATALOG_CURATION.md
outputs/<thread-id>/secureguide_catalog_complete.xlsx
```

**Structure Decision**: Extend the existing catalog workbook module and thin CLI. No schema migration or runtime/mobile dependency is required because all exported tables already exist in the authoritative database.

## Design

1. Define a stable ordered registry from worksheet name to authoritative SQLite table and primary key.
2. Retain `00_Manifest` through `08_Validation_Errors` in their established order, then append normalized detail worksheets.
3. Use the registry for state hashing, export, validation, planning, conflict lookup, and transactional apply.
4. Use sheet-qualified controlled-field mappings so overlapping names such as `type` and `status` resolve correctly.
5. Record artifact and per-sheet row counts in the manifest; validate those counts for unchanged exports.
6. Resolve affected artifact IDs by sheet semantics, including both endpoints of a relationship.

## Post-Design Constitution Check

All gates remain PASS. The design adds no operational tables, no JSON duplication, no raw payload, no direct release-asset mutation, and no production dependency.
