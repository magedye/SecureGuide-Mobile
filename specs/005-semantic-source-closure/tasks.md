---
description: "Implementation tasks for SecureGuide semantic and source-coverage closure"
---

# Tasks: Semantic Source Closure

**Input**: Design documents from `/specs/005-semantic-source-closure/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`

**Tests**: Required. Each behavior change must have focused regression coverage before release qualification.

## Phase 1: Scope and baseline

**Purpose**: Bind the implementation to the exact corpus and current governed artifacts.

- [x] T001 Create and validate the semantic-source-closure specification in `specs/005-semantic-source-closure/spec.md`
- [x] T002 [P] Record baseline counts, source deficits, active former-name occurrences, and exact candidate identity in `specs/005-semantic-source-closure/research.md`
- [x] T003 [P] Create the closure plan, data model, ledger contract, and qualification quickstart in `specs/005-semantic-source-closure/`

---

## Phase 2: Foundational reconciliation contract

**Purpose**: Establish source-hash-bound decisions and normalized evidence before changing catalog semantics.

- [x] T004 Add failing schema and curation tests for reconciliation links, deferred reason codes, source-hash-bound ledger coverage, and prohibited generic deferral in `tests/test_catalog_closure_schema.py` and `tests/test_catalog_validation.py`
- [x] T005 Add forward migration for normalized reconciliation links and controlled deferred reason data in `migrations/035_semantic_reconciliation_closure.sql`
- [x] T006 Generate migration parity and add migration coverage in `mobile/lib/core/database/generated_migrations.dart` and `tests/test_catalog_closure_schema.py`
- [ ] T007 Implement the pinned all-corpus ledger loader and source-hash validation in `secureguide/catalog_curation.py` and `config/semantic_reconciliation_ledger.json`
- [ ] T008 Extend closure validation and release gates for ledger totality, record-specific deferred evidence, link integrity, and lineage/disposition consistency in `secureguide/catalog_validation.py` and `scripts/build_release_db.py`

**Checkpoint**: The candidate rejects any generic/default reconciliation outcome and can represent all permitted source outcomes without violating normalized storage.

---

## Phase 3: User Story 1 - Reconcile Every Source Record (Priority: P1) 🎯 MVP

**Goal**: Reconcile the complete authoritative raw corpus against existing canonicals first and record evidence-backed outcomes.

**Independent Test**: Build a curated candidate and prove 100% decision coverage, no generic deferred rationale, source-by-source outcomes, and matching lineage for all support/split decisions.

- [ ] T009 [P] [US1] Add full-corpus source fixtures and assertion helpers for NIST, MITRE, ASVS, CSF, ECC, NCA, PCI, ISO, and low-volume sources in `tests/test_complete_catalog_curation.py`
- [ ] T010 [P] [US1] Add disposition/link/lineage round-trip and closure-report tests in `tests/test_catalog_reconciliation.py` and `tests/test_catalog_validation.py`
- [ ] T011 [US1] Implement deterministic raw-record candidate discovery and source-aware reconciliation planning in `secureguide/catalog_curation.py`
- [ ] T012 [US1] Populate the complete source-hash-bound reconciliation ledger with record-specific outcomes, targets, rationale, confidence state, and review routing in `config/semantic_reconciliation_ledger.json`
- [ ] T013 [US1] Apply ledger decisions transactionally, preserving existing canonicals where appropriate and writing final lineage or reconciliation links by disposition in `secureguide/catalog_curation.py`
- [ ] T014 [US1] Add a reproducible full-corpus ledger rebuild/report command in `scripts/rebuild_semantic_reconciliation.py`
- [ ] T015 [US1] Build an isolated candidate and record before/after raw, disposition, source, canonical, and lineage counts in `consolidation/semantic_source_closure_baseline.json`

**Checkpoint**: Every raw record has an evidence-backed outcome; any remaining deferral is individual, categorized, and justified.

---

## Phase 4: User Story 2 - Trust Semantic Classifications (Priority: P1)

**Goal**: Correct outcome/noun-driven type mistakes and independently re-evaluate type, level, and SDT assignment.

**Independent Test**: Run required regression cases and an individual NIST CSF audit, then validate all type-specific and SDT constraints on an isolated candidate.

- [x] T016 [P] [US2] Add required semantic regression fixtures for policy, plan, review/audit, process, outcome, PCI PAN, vulnerability management, and MITRE cases in `tests/test_semantic_classification.py`
- [ ] T017 [P] [US2] Add NIST CSF individual-audit and source-wide no-blind-conversion tests in `tests/test_semantic_classification.py` and `tests/test_complete_catalog_curation.py`
- [ ] T018 [US2] Correct classifier ordering, source-aware CSF outcome handling, stable CSF identifier recognition, and safe domain fallback behavior in `secureguide/semantic_classification.py`
- [ ] T019 [US2] Add a pinned canonical semantic-correction input with independent type, level, domain, sub-domain, confidence, and rationale decisions in `config/canonical_semantic_corrections.json`
- [ ] T020 [US2] Apply semantic corrections before curation validation and preserve all required type-specific fields in `secureguide/catalog_curation.py` and `secureguide/catalog_validation.py`
- [ ] T021 [US2] Produce a deterministic semantic audit report with NIST CSF results and rejected alternatives where relevant in `scripts/rebuild_semantic_reconciliation.py` and `consolidation/semantic_audit.json`

**Checkpoint**: Semantic false-positive patterns are regression-protected and the candidate has no silent type, level, or SDT fallback.

---

## Phase 5: User Story 3 - Preserve Source-Rich, Neutral Catalog Identity (Priority: P2)

**Goal**: Improve source provenance and remove obsolete active terminology while retaining compatibility history.

**Independent Test**: Build a candidate, verify active terminology is clean, historical aliases remain usable, and profile-bearing upgrade fixtures preserve data.

- [ ] T022 [P] [US3] Add active-surface identity scans for mappings, actions, current config, aliases, and historical exemptions in `tests/test_catalog_identity.py`
- [ ] T023 [P] [US3] Add lineage-rationale specificity and original-source coverage assertions in `tests/test_complete_catalog_curation.py` and `tests/test_catalog_reconciliation.py`
- [ ] T024 [US3] Neutralize active legacy-derived mapping rationale and action wording while preserving raw historical provenance in `SecureGuide_Mobile_Docs/Raw_Catalogs/legacy_catalog_v4_recovered.json`
- [ ] T025 [US3] Add a forward migration to neutralize current scoring-policy wording without rewriting historical migrations in `migrations/035_semantic_reconciliation_closure.sql`
- [ ] T026 [US3] Strengthen identity validation to inspect generated candidate database active fields and retain only documented compatibility/history exceptions in `scripts/validate_catalog_identity.py`
- [ ] T027 [US3] Verify alias resolution and operational-data preservation for changed or consolidated identities in `secureguide/catalog_upgrade.py`, `tests/test_catalog_upgrade.py`, and `mobile/test/catalog_upgrade_test.dart`

**Checkpoint**: Active current surfaces are neutral, source lineage is meaningful, and compatibility history remains upgrade-safe.

---

## Phase 6: User Story 4 - Release a Reproducible Closed Candidate (Priority: P2)

**Goal**: Qualify the exact full-corpus candidate and governed workbook before publishing the asset.

**Independent Test**: Compare two fresh candidates, run V1-V4 validation, complete a no-op workbook round trip, and demonstrate catalog-upgrade preservation.

- [ ] T028 [P] [US4] Extend workbook export/import/validation coverage for reconciliation links, deferred evidence, and semantic audit fields in `secureguide/catalog_workbook.py`, `tests/test_catalog_workbook.py`, and `tests/test_catalog_workbook_apply.py`
- [ ] T029 [P] [US4] Extend release qualification reporting for semantic closure evidence and exact source-count comparisons in `scripts/validate_catalog_release.py` and `tests/test_release_build.py`
- [ ] T030 [US4] Regenerate the complete workbook contract and prove export→validate→plan→transactional no-op apply on an isolated candidate in `scripts/catalog_workbook.py` and `consolidation/semantic_source_workbook_qualification.json`
- [ ] T031 [US4] Build two deterministic full-corpus candidates, run V1-V4 release validation, and record hashes in `consolidation/semantic_source_release_qualification.json`
- [ ] T032 [US4] Run focused and full Python validation, migration parity, runtime-boundary verification, Flutter format/analyze/tests, Android release compile, and applicable CI iOS compile in `outputs/semantic-source-closure/`
- [ ] T033 [US4] Replace `mobile/assets/catalog.db` and its manifest only with the exact qualified candidate through `scripts/build_release_db.py`

**Checkpoint**: The shipped asset is SHA-bound to a candidate that passes all applicable closure and release gates.

---

## Phase 7: Review, publish, and evidence

**Purpose**: Independently review the exact implementation, preserve evidence, and update the existing draft review surface.

- [ ] T034 Perform a multi-axis code/data/security-integrity review against USACM, SDT, source rights, lineage, aliases, profile isolation, and SQLite constraints in `FINAL_REVIEW_REPORT.md`
- [ ] T035 Record exact before/after counts, remaining deferred categories, semantic corrections, hashes, and genuine blockers in `PRODUCTION_PROMOTION_REPORT.md`
- [ ] T036 Confirm `old/` and unrelated artifacts remain untouched, commit coherent verified increments, push `agent/complete-secureguide-mobile`, update draft PR #1, and verify CI for the exact head

## Dependencies & Execution Order

- Phase 1 is complete and establishes the evidence baseline.
- Phase 2 blocks all user stories because semantic closure needs a reproducible decision model and validator.
- US1 creates complete source outcomes and supplies lineage evidence to US2-US4.
- US2 semantic corrections must complete before the final US1 candidate and all US4 qualification.
- US3 identity changes require the forward migration before workbook/release qualification.
- US4 qualifies an isolated candidate before asset replacement.
- Phase 7 occurs only after all required validation is complete.

## Parallel Opportunities

- T004 and T009/T010 can prepare tests in separate files before their implementation tasks.
- T016/T017 and T022/T023 are isolated regression-test work.
- T028/T029 can begin after the finalized schema/ledger contract and before final candidate qualification.

## Implementation Strategy

1. Complete the foundational contract, migration, validator, and ledger loader first.
2. Implement source reconciliation as small, tested increments; preserve existing canonicals before considering new ones.
3. Land semantic classifier fixes independently from bulk decision data.
4. Land active terminology cleanup as a compatibility-safe migration/data increment.
5. Qualify candidates and workbook/upgrade behavior only after source and semantic changes are stable.
