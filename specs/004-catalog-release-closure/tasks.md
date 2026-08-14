---
description: "Implementation tasks for deterministic SecureGuide catalog release closure"
---

# Tasks: Catalog Release Closure

**Input**: Design documents from `/specs/004-catalog-release-closure/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`

**Tests**: Required by the feature specification and release qualification requirements.

## Phase 1: Setup and authoritative contracts

**Purpose**: Establish exact feature scope and authoritative versioned contracts.

- [x] T001 Create and validate the feature specification in `specs/004-catalog-release-closure/spec.md`
- [x] T002 [P] Create the implementation research and decisions in `specs/004-catalog-release-closure/research.md`
- [x] T003 [P] Create the data and upgrade model in `specs/004-catalog-release-closure/data-model.md`
- [x] T004 [P] Create workbook and identity contracts in `specs/004-catalog-release-closure/contracts/`
- [x] T005 Create the implementation plan and constitution check in `specs/004-catalog-release-closure/plan.md`
- [x] T006 Align repository-relative authorities and terminology in `AGENTS.md`, `docs/`, and active specifications

---

## Phase 2: Foundational catalog contracts

**Purpose**: Make shared validation, naming, and reproducibility foundations authoritative before story-specific work.

- [x] T007 Add the versioned `MINIMUM_VALID`, `STRICT_USACM`, and `ENRICHED` profiles to `config/catalog_minimum_fields.yaml`
- [x] T008 [P] Add validation tests for independent quality-profile outcomes and explicit `0.0` confidence semantics in `tests/test_catalog_minimum_contract.py`
- [x] T009 Implement contract loading and independent quality-profile validation in `secureguide/catalog_curation.py` and `secureguide/validation.py`
- [x] T010 Add forward migration `migrations/034_neutral_catalog_identity.sql` for neutral schema names and durable artifact aliases
- [x] T011 Generate migration parity in `mobile/lib/core/database/generated_migrations.dart` and add migration tests
- [x] T012 Update current source manifest and rights records to neutral source identity in `config/source_manifest.json` and `config/source_rights.yaml`
- [x] T013 Rename the recovered source and active legacy scripts/modules to neutral paths and update references

**Checkpoint**: Shared quality, naming, and migration foundations are ready.

---

## Phase 3: User Story 1 - Trust the Minimum-Valid Catalog (Priority: P1)

**Goal**: Produce a truthful catalog of at least 1,000 minimum-valid الضوابط without converting review uncertainty into approval.

**Independent Test**: Build a fresh database, validate `MINIMUM_VALID`, and prove that review-pending/low-confidence rows remain visible while structural, lineage, controlled-value, type-specific, and SDT defects fail.

### Tests for User Story 1

- [x] T014 [P] [US1] Add semantic classifier fixtures covering requirement, policy, control, configuration, procedure, metric, threat, vulnerability, and ambiguous rows in `tests/test_semantic_classification.py`
- [x] T015 [P] [US1] Add curation tests for pinned-input drift, review-pending minimum admission, and strict-profile rejection in `tests/test_catalog_curation.py`
- [x] T016 [P] [US1] Add raw disposition totality and confidence-sentinel tests in `tests/test_catalog_release.py`

### Implementation for User Story 1

- [x] T017 [US1] Implement deterministic semantic rules and type-specific defaults in `secureguide/semantic_classification.py`
- [x] T018 [US1] Add explicit rebuild command in `scripts/rebuild_legacy_classifications.py`
- [x] T019 [US1] Generate and review `consolidation/curated/legacy_classifications.json` with input hash and per-row rationale
- [x] T020 [US1] Replace hardcoded legacy `ART-CTR`/`ABS-CTR` loading with pinned classifications in `secureguide/catalog_curation.py`
- [x] T021 [US1] Align promotion, classification, consolidation, AI review, and import policies in `docs/`
- [x] T022 [US1] Build a fresh catalog and prove minimum-valid count, controlled distributions, no missing required fields, and complete raw dispositions

**Checkpoint**: Minimum-valid catalog qualification passes independently.

---

## Phase 4: User Story 2 - Use Neutral SecureGuide Identity Safely (Priority: P1)

**Goal**: Remove the former product token from active surfaces while preserving historical evidence and installed references.

**Independent Test**: Scan active surfaces against an explicit historical allowlist and upgrade a database containing old IDs without losing profile state.

### Tests for User Story 2

- [x] T023 [P] [US2] Add active-name and historical-exception scan tests in `tests/test_catalog_identity.py`
- [x] T024 [P] [US2] Add alias coverage and old-ID resolution tests in `tests/test_catalog_upgrade.py`

### Implementation for User Story 2

- [x] T025 [US2] Emit neutral raw, staging, source, and canonical IDs plus complete aliases during curation
- [x] T026 [US2] Update active Python/Dart APIs, workbook labels, reports, and documentation to neutral names
- [x] T027 [US2] Resolve artifact aliases transactionally during installed catalog upgrade in `secureguide/catalog_upgrade.py`
- [x] T028 [US2] Validate that only immutable migrations, archives, alias values, and source evidence retain allowlisted former-token references

**Checkpoint**: Current product identity is neutral and old references remain compatible.

---

## Phase 5: User Story 3 - Curate Through a Complete Governed Workbook (Priority: P1)

**Goal**: Export and re-import all الضوابط and their normalized details, including every raw disposition, with deterministic filters.

**Independent Test**: Complete export → unchanged import → re-export preserves governed hashes/counts; filtered exports contain exactly the selected canonical scope and dependent rows.

### Tests for User Story 3

- [x] T029 [P] [US3] Add workbook v3 manifest, raw disposition, neutral-sheet, and lossless round-trip tests in `tests/test_catalog_workbook.py`
- [x] T030 [P] [US3] Add deterministic type/domain/source/quality filter tests in `tests/test_catalog_workbook.py`

### Implementation for User Story 3

- [x] T031 [US3] Add `09_Raw_Dispositions`, shift detail sheets, and use neutral sheet names in `secureguide/catalog_workbook.py`
- [x] T032 [US3] Add complete and filtered export scopes plus manifest hashes/counts in `secureguide/catalog_workbook.py`
- [x] T033 [US3] Validate/import raw dispositions and scoped workbook changes without data loss in `secureguide/catalog_workbook.py`
- [x] T034 [US3] Extend CLI flags and help in `scripts/export_catalog_workbook.py` and `scripts/import_catalog_workbook.py`
- [x] T035 [US3] Export and validate final complete and representative filtered XLSX artifacts

**Checkpoint**: Workbook v3 is complete, lossless, neutral, and filterable.

---

## Phase 6: User Story 4 - Reconcile Globally and Reproducibly (Priority: P1)

**Goal**: Discover and record duplicate/equivalence candidates across all sources without destructive merging or hidden classifier drift.

**Independent Test**: Run discovery twice against identical inputs and compare normalized output hashes; confirm every group has multi-source candidates, method/version, strength, rationale, and review state.

- [x] T036 [P] [US4] Add global equivalence coverage and deterministic-output tests in `tests/test_catalog_reconciliation.py`
- [x] T037 [US4] Implement conservative all-source equivalence discovery in `scripts/rebuild_unified_equivalence.py`
- [x] T038 [US4] Rebuild and review `consolidation/unified/equivalence.json` without deleting raw candidates
- [x] T039 [US4] Record classifier/equivalence tool versions and input hashes in release provenance

**Checkpoint**: Reconciliation is global, reproducible, evidence-bearing, and non-destructive.

---

## Phase 7: User Story 5 - Build and Upgrade a Real Release Candidate (Priority: P2)

**Goal**: Produce deterministic real-content catalog assets and safely upgrade installed catalogs while preserving profile operations.

**Independent Test**: Two fresh builds have the same logical content hash, and an upgrade fixture preserves profile artifacts, assessments, evidence, exceptions, notes, ownership, and review fields.

- [x] T040 [P] [US5] Add two-build reproducibility and release-input binding tests in `tests/test_catalog_release.py`
- [x] T041 [P] [US5] Expand operational-state preservation and rollback tests in `tests/test_catalog_upgrade.py`
- [x] T042 [US5] Bind release manifest to contracts, pinned inputs, rights, counts, and logical content hash in `secureguide/catalog_release.py`
- [x] T043 [US5] Complete transactional installed-catalog replacement and rollback in Python and Flutter upgrade paths
- [x] T044 [US5] Build and replace `mobile/assets/catalog.db` with the exact qualified candidate

**Checkpoint**: Candidate build is deterministic and installed upgrades preserve operational data.

---

## Phase 8: User Story 6 - Qualify the Exact Candidate (Priority: P2)

**Goal**: Bind V1-V4 evidence, automated tests, mobile analysis/tests, and CI to the exact release candidate and Git SHA.

**Independent Test**: All validators and tests pass against the packaged candidate, CI installs pinned tooling dependencies, and evidence records exact Git/content hashes.

- [x] T045 [P] [US6] Extend V1 structural/semantic validation and V2 source/rights validation in `scripts/validate_catalog_release.py`
- [x] T046 [P] [US6] Extend V3 classification/mapping and V4 release/upgrade validation in `scripts/validate_catalog_release.py`
- [x] T047 [US6] Install `requirements-curation.txt` in `.github/workflows/ci.yml`
- [x] T048 [US6] Run Python tests, migration parity, runtime-boundary verification, workbook validation, and two-build reproducibility
- [x] T049 [US6] Run Flutter format, analyze, unit/widget tests, and relevant upgrade integration tests
- [x] T050 [US6] Run Spec Kit consistency/convergence checks and complete every implemented task marker

---

## Phase 9: Review, save, and publish

**Purpose**: Review the exact diff, persist evidence, and publish only the intended branch changes.

- [x] T051 Perform multi-axis code/data/security-integrity review against USACM, SDT, lineage, profile isolation, and SQLite constraints
- [x] T052 Record exact catalog/database/workbook/Git hashes and qualification evidence in the release report
- [x] T053 Confirm `old/` and unrelated user artifacts remain untouched, then intentionally commit the scoped changes
- [x] T054 Push `agent/complete-secureguide-mobile`, update the existing draft PR, and verify CI conclusion for the exact head

---

## Dependencies and execution order

- Phase 1 defines scope and is complete before implementation.
- Phase 2 blocks all user stories because naming, migration, and quality profiles are shared foundations.
- User Story 1 supplies the valid content consumed by User Stories 2-6.
- User Story 2 aliases must exist before installed-upgrade qualification.
- User Story 3 consumes the finalized schema and neutral identity.
- User Story 4 must finish before the release manifest/content hash is sealed.
- User Story 5 produces the candidate validated by User Story 6.
- Review and publication occur only after all desired stories pass.

## Implementation strategy

Implement in dependency order and verify each checkpoint before continuing. Use small commits only after coherent, tested increments. Never regenerate pinned classifications or equivalence data implicitly. Preserve all source rows and unrelated workspace artifacts.
