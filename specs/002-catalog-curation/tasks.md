# Tasks: Complete Catalog Curation

**Input**: Design documents from `specs/002-catalog-curation/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: Required by the owner success criteria and repository constitution. Each implementation slice must be proven before the next dependent slice.

## Phase 1: Setup

**Purpose**: Establish versioned contracts and reproducible tool dependencies.

- [x] T001 Create the versioned minimum-entry contract and pin build-time workbook dependencies in `config/catalog_minimum_fields.yaml` and `requirements-curation.txt`
- [x] T002 [P] Create pinned source corpus and conservative source-rights inputs in `config/source_manifest.json` and `config/source_rights.yaml`
- [x] T003 [P] Document minimum validation, source rights, raw dispositions, final lineage, and Excel semantics in `docs/CATALOG_CURATION.md`

---

## Phase 2: Foundational

**Purpose**: Add durable catalog-closure facts and reusable validation before user-facing curation flows.

**Checkpoint**: All later stories depend on this phase.

- [x] T004 Write failing migration tests for manifests, source rights, dispositions, lineage, delete guards, and profile separation in `tests/test_catalog_closure_schema.py`
- [x] T005 Implement additive closure schema, constraints, indexes, and recovery notes in `migrations/031_catalog_closure_foundation.sql`
- [x] T006 Regenerate embedded Flutter migrations and verify schema 031 parity in `mobile/lib/core/database/generated_migrations.dart` and `tests/test_catalog_closure_schema.py`
- [x] T007 Write failing tests that distinguish minimum validation, strict USACM conformance, low-confidence review flags, type requirements, risk remediation, and closure errors in `tests/test_catalog_validation.py`
- [x] T008 Implement contract loading, canonical hashing, separate validators, closure/integrity checks, and deterministic JSON reports in `secureguide/catalog_validation.py`
- [x] T009 Expose validation through `scripts/catalog_validate.py` and prove stable exit codes and report hashes in `tests/test_catalog_validation.py`
- [x] T010 Remove silent `ART-CTR` fallback and make unresolved classification explicitly deferred in `scripts/batch_process.py` and its focused tests in `tests/test_catalog_validation.py`
- [x] T011 Backfill source manifests and rights from pinned evidence without inventing metadata in `secureguide/catalog_curation.py` and `tests/test_complete_catalog_curation.py`

---

## Phase 3: User Story 1 - Admit Structurally Valid Canonicals (Priority: P1)

**Goal**: Catalog readiness is evaluated from one minimum contract while human review, enrichment, and strict USACM remain separate.

**Independent Test**: Representative `ART-REQ`, `ART-CTR`, `ART-CTE`, `ART-AST`, `ART-RSK`, `ART-EXC`, and published policy/standard/procedure cases return correct independent minimum and strict outcomes.

- [x] T012 [US1] Refactor promotion blockers into structural/minimum and strict-review gates without weakening controlled values in `scripts/_promote_common.py`
- [x] T013 [US1] Preserve low-confidence `MINIMUM_VALID` rows with correct review flags and publication state during promotion in `scripts/promote.py`
- [ ] T014 [US1] Replace release human-approval equivalence with separately reported minimum, strict, and review summaries in `scripts/build_release_db.py`
- [x] T015 [US1] Add promotion/release regression tests for `NOT_REVIEWED`, low confidence, missing type fields, and strict/minimum divergence in `tests/test_promotion_minimum_valid.py`

**Checkpoint**: A valid canonical can enter the catalog without a false human-review or strict-conformance claim.

---

## Phase 4: User Story 2 - Curate Safely Through Excel (Priority: P1)

**Goal**: A curator can run the nine-sheet export, validate, plan, and transactional apply workflow without stale overwrites or deletion by omission.

**Independent Test**: A valid edit applies; stale DB/row edits, formulas, invalid enums, immutable-ID changes, and mid-batch failures are rejected; omission mutates nothing.

- [x] T016 [US2] Write failing schema tests for workbook runs and per-row audit records in `tests/test_catalog_workbook.py`
- [x] T017 [US2] Add workbook audit entities and indexes in `migrations/032_catalog_workbook_audit.sql`
- [x] T018 [US2] Write failing exact-nine-sheet export/validation tests including named reference lists, dropdowns, formula rejection, and validation errors in `tests/test_catalog_workbook.py`
- [x] T019 [US2] Implement deterministic workbook export and validation in `secureguide/catalog_workbook.py`
- [x] T020 [US2] Write failing plan/apply tests for stale baseline, stale rows, audited resolution, omission, deprecation, rollback, profile preservation, and release-asset guard in `tests/test_catalog_workbook_apply.py`
- [x] T021 [US2] Implement conflict-safe plan and transactional apply without `REPLACE` or physical deletion in `secureguide/catalog_workbook.py`
- [x] T022 [US2] Expose `export`, `validate`, `plan`, and `apply` through `scripts/catalog_workbook.py` and run an unchanged-workbook round trip

**Checkpoint**: The workbook is a safe human interface while SQLite remains authoritative.

---

## Phase 5: User Story 3 - Account for Every Source Record (Priority: P1)

**Goal**: Every raw record has an explicit disposition and every canonical has normalized final lineage across one globally reconciled corpus.

**Independent Test**: Full-corpus closure reports 100 percent dispositions, complete canonical lineage, disposition-lineage consistency, all eight domain checkpoints, and zero dangling references.

- [ ] T023 [US3] Write failing deterministic projection and closure tests using all staging candidates and `consolidation/unified/equivalence.json` in `tests/test_complete_catalog_curation.py`
- [ ] T024 [US3] Implement deterministic canonical selection, stable IDs, duplicate/supporting lineage, explicit deferral, and no-default-type behavior in `secureguide/catalog_curation.py`
- [ ] T025 [US3] Normalize framework mappings, tags, relationships, type-specific data, final lineage, and raw dispositions transactionally in `secureguide/catalog_curation.py`
- [ ] T026 [US3] Expose global curation and SD-01 through SD-08 checkpoints through `scripts/curate_complete_catalog.py`
- [ ] T027 [US3] Run global similarity/equivalence conflict discovery and persist the deterministic checkpoint in `consolidation/curation_checkpoint.json`
- [ ] T028 [US3] Run final closure validation and record counts, debt, and independent minimum/strict results in `consolidation/catalog_validation.json`

**Checkpoint**: The complete raw corpus is closed and the minimum-valid canonical catalog is globally reconciled.

---

## Phase 6: User Story 4 - Produce a Reproducible Release Candidate (Priority: P2)

**Goal**: Produce and qualify one deterministic, rights-safe catalog candidate and upgrade a populated installation without operational data loss.

**Independent Test**: Two builds have identical DB and canonical-manifest hashes; restricted/unknown raw payload is absent; populated upgrade snapshots are identical; performance evidence covers all required categories.

- [ ] T029 [US4] Write failing deterministic manifest, input-hash, rights-scrub, and atomic pair tests in `tests/test_release_build.py`
- [ ] T030 [US4] Extend release construction with curated mode, rights-safe payload scrubbing, canonical deterministic manifests, staged pair verification, and atomic candidate promotion in `scripts/build_release_db.py`
- [ ] T031 [US4] Write failing populated-install catalog-upgrade and rollback tests covering profiles, controls, assessments, evidence, and exceptions in `tests/test_catalog_upgrade.py`
- [ ] T032 [US4] Implement transactional catalog-data upgrade with stable-ID and operational-snapshot guards in `secureguide/catalog_upgrade.py` and `scripts/catalog_upgrade.py`
- [ ] T033 [US4] Add Flutter-side catalog content upgrade qualification and full operational preservation coverage in `mobile/lib/core/database/database_helper.dart` and `mobile/test/catalog_upgrade_test.dart`
- [ ] T034 [US4] Write failing qualification tests for startup, database size, memory, migration duration, integrity, declared population, query plans, and baseline comparison in `tests/test_performance_benchmark.py`
- [ ] T035 [US4] Extend performance qualification and evidence output without inventing new thresholds in `scripts/benchmark_release_catalog.py` and `consolidation/performance_budget.json`
- [ ] T036 [US4] Build two clean candidates, compare hashes, qualify performance and upgrade preservation, then publish the verified pair through `scripts/build_release_db.py` to `mobile/assets/catalog.db` and `mobile/assets/catalog.db.manifest.json`

---

## Phase 7: Polish & Cross-Cutting Validation

- [ ] T037 Run all Python schema, curation, release, upgrade, read-model, security, and performance tests from `tests/`
- [ ] T038 Run Flutter analysis, unit tests, database lifecycle tests, and applicable Android build gates from `mobile/`
- [ ] T039 Re-run catalog validation and verify deterministic clean rebuild, 100 percent closure, zero FK/dangling issues, and profile preservation using `specs/002-catalog-curation/quickstart.md`
- [ ] T040 Update curation, release, installation, recovery, and performance evidence in `docs/CATALOG_CURATION.md`, `docs/PERFORMANCE_QUALIFICATION.md`, and `mobile/docs/RELEASE_INSTALLATION.md`

---

## Dependencies & Execution Order

- Phase 1 establishes authoritative inputs.
- Phase 2 blocks every user story.
- Phase 3 supplies catalog admission semantics used by Phases 4-6.
- Phase 4 must pass before using the workbook for corpus changes.
- Phase 5 produces the closed catalog consumed by Phase 6.
- Phase 6 produces the release candidate and upgrade path.
- Phase 7 is the final repository-wide gate.

## Parallel Opportunities

- T002 and T003 can proceed after T001 without touching the same files.
- Test authoring for a later independent module may proceed while an earlier implementation file is stable, but migrations and generated Flutter migrations remain sequential.
- Python and Flutter final validations may run concurrently only after the release asset pair is fixed.

## Implementation Strategy

1. Land small tested foundation slices: contract, schema, validation.
2. Land workbook export/validate before plan/apply.
3. Run curation only on a copied working database and checkpoint every domain.
4. Build and qualify outside the mobile asset path.
5. Replace the bundled asset only once with the verified candidate pair.
6. Preserve `old/` and all unrelated worktree content.
