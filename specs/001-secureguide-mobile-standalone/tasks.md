# Task Backlog: SecureGuide Mobile Standalone

## P0 — Standalone Core

- [x] **SGM-001**: Create supported Flutter App project in `mobile/` for Android and iOS.
  - Dependencies: None
  - Scope: Flutter project configuration, `pubspec.yaml`, app icons, platform runners.
  - Acceptance Criteria: A diagnostic release build succeeds for Android and iOS platforms.
- [x] **SGM-002**: SQLite lifecycle management on the device.
  - Dependencies: SGM-001
  - Scope: Ship base release DB in assets, copy on first run, handle migrations safely in transactions, enforce foreign keys.
  - Acceptance Criteria: Data is preserved across fresh installs, app restarts, and database upgrades.
- [x] **SGM-003**: Create `LocalSecureGuideClient`.
  - Dependencies: SGM-002
  - Scope: Implement native Dart repositories replicating the existing client interfaces but bypassing HTTP.
  - Acceptance Criteria: Existing UI widgets function properly in Airplane mode without `127.0.0.1`.
- [x] **SGM-004**: Migrate business rules with strict parity tests.
  - Dependencies: SGM-003
  - Scope: Assessment calculations, active profile filtering, scoring engines migrated from Python to Dart.
  - Acceptance Criteria: Dart outputs exactly match Python `read-model-v1` golden samples.
- [x] **SGM-005**: Local evidence store.
  - Dependencies: SGM-003
  - Scope: Store evidence locally, tracking hash, type, size, and linking to `profile_artifact_id`.
  - Acceptance Criteria: Files isolated to specific enterprise profiles; corrupt files handled safely.
- [x] **SGM-006**: Independence and E2E testing.
  - Dependencies: SGM-001, SGM-002, SGM-003, SGM-004, SGM-005
  - Scope: Automated and manual full-workflow validation on emulators/devices.
  - Acceptance Criteria: Full assessment workflow completes perfectly with network disconnected.

## P1 — MVP Surfaces

- [x] **SGM-101**: Full Item Details (catalog separation, sources, tags, metadata).
- [x] **SGM-102**: Catalog filters (type, domain, testability, priority).
- [x] **SGM-103**: Templates (list, preview, apply template preserving provenance).
- [x] **SGM-104**: Evidence UI (add/view/delete, link to assessment/artifact).
- [x] **SGM-105**: Exceptions and Review Queue (draft, submit, approve, state machine).
- [x] **SGM-106**: Blueprints and Plans UI (review track, outputs).
- [x] **SGM-107**: Tasks UI (filter, owner, status transitions).
- [x] **SGM-108**: Reporting and Export (offline HTML/PDF export, omitting drafts).
- [x] **SGM-109**: Enterprise Profile management UI (modify, archive, active context UI indicators).

## P2 — Release Quality

- [x] **SGM-201**: CI pipeline integration for Python/Dart tests, golden parity, and Android build.
- [x] **SGM-202**: Advanced integration, data migration, recovery, and E2E device tests.
- [x] **SGM-203**: Performance measurement and database index optimization on the full release catalog.
- [x] **SGM-204**: Evidence file protection, log redaction, and backup/export security review.
- [x] **SGM-205**: Localization (Arabic/English) with true RTL layouts, responsive layouts, and accessibility.
- [x] **SGM-206**: Release signing, binary versioning, installation guide, and rollback instructions.

## Phase 3: Convergence

- [X] **T207 CRITICAL** Build and bundle a governed release catalog from approved promoted source records, preserving raw-source lineage and failing when only demo/test content or no usable templates are present, per SGM-002/SGM-103/SGM-203 and plan §2.2 (partial).
- [X] **T208 CRITICAL** Apply templates transactionally through `profile_templates`, `profile_artifacts`, and `profile_artifact_origins`, preserving template version, inclusion reason, priority/review defaults, idempotency, and profile isolation, per SGM-103 (contradicts).
- [X] **T209** Implement typed local blueprint and task repositories that map SQLite snake_case fields correctly, return actions/outputs/evidence/rules/enrichments, enforce affected-row workflow transitions, and capture accountable actors, per SGM-106/SGM-107 (partial).
- [X] **T210** Implement a persistent Arabic/English locale controller, user-visible language toggle, ARB-backed core screens, and RTL/LTR widget coverage, per SGM-205 and spec §5 (partial).
- [X] **T211** Expose profile-isolated evidence integrity verification and safe content viewing plus tested local database backup/restore controls, per SGM-005/SGM-104/SGM-204 (partial).
- [ ] **T212** Repair CI dependency installation, pin a Flutter version compatible with `pubspec.yaml`, run parity and migration gates, and compile Android and iOS release targets, per SGM-201 and plan §3 (contradicts).
  - Local evidence (2026-08-13): Flutter 3.41.1 analysis/tests and the Android release compile pass; both workflow files parse. Keep this open until hosted CI completes the Android and macOS iOS jobs.
- [X] **T213** Complete catalog sub-domain and locale-aware filtering and add UI coverage for PDF/HTML/JSON export with draft omission, per SGM-102/SGM-108 (partial).
- [X] **T214** Add and document a real-device or emulator offline acceptance workflow covering launch, profile creation, catalog selection, assessment, evidence, restart persistence, and absence of a Python/HTTP runtime, per SGM-006/SGM-202 (partial).
- [ ] **T215** Add release signing configuration, secret-safe CI inputs, signed artifact verification, installation evidence, and non-destructive rollback/recovery instructions, per SGM-206 (partial).
  - Local evidence (2026-08-13): fail-closed Android signing configuration, protected workflow, verifier, and recovery guidance are present; the local APK is deliberately unsigned. Keep this open until owner-approved application/bundle IDs, protected signing material, a verified signed candidate, and installation evidence exist.
- [ ] **T216** Benchmark search, profile dashboard, and report generation against the governed full release catalog with reproducible thresholds and query-plan evidence, per SGM-203 (partial).
  - Local evidence (2026-08-13): schema-030 smoke p95 is 72.093/45.002/72.348 ms and all provisional limits pass, but qualification exits `2` with `BLOCKED_CATALOG_TOO_SMALL` because only 4 approved artifacts exist versus the required 1000.
