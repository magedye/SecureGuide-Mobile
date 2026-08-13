# Feature Specification: Complete Catalog Curation

**Feature Branch**: `agent/complete-secureguide-mobile`

**Created**: 2026-08-13

**Status**: Approved for implementation

**Input**: Owner-approved execution contract for a complete, reproducible SecureGuide minimum-valid catalog.

## User Scenarios & Testing

### User Story 1 - Admit Structurally Valid Canonicals (Priority: P1)

As a catalog curator, I can validate each canonical security artifact against one explicit minimum-entry contract so catalog readiness is not confused with enrichment, human review, or strict USACM conformance.

**Why this priority**: Every later curation, bulk-edit, and release action depends on a stable definition of a catalog-ready canonical.

**Independent Test**: Validate representative governance, requirement, control, asset, risk, exception, policy, standard, and procedure artifacts and confirm core and type-specific failures are reported separately from strict-conformance findings.

**Acceptance Scenarios**:

1. **Given** a canonical with all core fields, a valid type-specific shape, explicit review state, and valid raw lineage, **when** minimum validation runs, **then** it receives `MINIMUM_VALID` even if optional enrichment or human review is absent.
2. **Given** a low-confidence canonical with a recorded rationale and human-review flag, **when** minimum validation runs, **then** confidence alone does not block entry and no human review or strict-conformance claim is made.
3. **Given** an artifact missing a core or applicable type-specific field, **when** minimum validation runs, **then** it fails closed with field-level errors.
4. **Given** an artifact that is minimum-valid but fails stricter USACM rules, **when** both validators run, **then** the two outcomes remain distinguishable.

---

### User Story 2 - Curate Safely Through Excel (Priority: P1)

As a human curator, I can export the catalog to a structured workbook, edit it with controlled values, validate it, review a deterministic import plan, and apply only non-conflicting changes transactionally.

**Why this priority**: Spreadsheet curation is the approved primary bulk-edit workflow and must not permit data loss or stale overwrites.

**Independent Test**: Complete an export, controlled edit, validation, plan, and apply cycle; then prove stale edits, omission-based deletion, invalid values, and unapproved conflicts are rejected.

**Acceptance Scenarios**:

1. **Given** an exported baseline, **when** a valid row is changed with `UPSERT`, **then** validation and planning succeed and transactional apply records an audit trail.
2. **Given** a database row or baseline hash changed after export, **when** apply is attempted, **then** the row is marked `CONFLICT` and is not changed automatically.
3. **Given** a row is omitted from the workbook, **when** the workbook is applied, **then** omission is treated as `NO_CHANGE` and no physical deletion occurs.
4. **Given** a row uses `DEPRECATE`, **when** the plan is explicitly accepted and applied, **then** stable identity and lineage remain preserved.
5. **Given** an invalid controlled value or structural error, **when** validation runs, **then** an actionable entry appears in `08_Validation_Errors` and apply is blocked.

---

### User Story 3 - Account for Every Source Record (Priority: P1)

As a catalog owner, I can trace every raw source record to an explicit disposition and every canonical to at least one reproducible raw-source lineage record without dangling references or invented provenance.

**Why this priority**: Complete disposition and lineage are the evidence boundary for a defensible catalog.

**Independent Test**: Run closure validation across the full raw corpus and confirm every raw row has one allowed disposition, supporting dispositions have matching lineage, every canonical has lineage, and all references resolve.

**Acceptance Scenarios**:

1. **Given** the complete raw corpus, **when** closure validation runs, **then** disposition coverage is 100 percent using only the approved disposition values.
2. **Given** a raw row that supports a canonical, **when** closure validation runs, **then** a matching final lineage record exists.
3. **Given** a source with unknown version or rights, **when** provenance is recorded, **then** uncertainty and its reason are explicit and unavailable metadata is not invented.
4. **Given** source rights are unknown or restricted, **when** a mobile release is built, **then** raw source text is excluded while permitted references, authored canonical content, and lineage are retained.

---

### User Story 4 - Produce a Reproducible Release Candidate (Priority: P2)

As a release engineer, I can construct one deterministic catalog release candidate from a clean working database, qualify integrity and performance against an evidence-backed baseline, and upgrade an existing installation without losing operational profile data.

**Why this priority**: Catalog curation is complete only when its output can be reproduced, installed, and upgraded safely.

**Independent Test**: Build twice from the same pinned inputs, compare hashes and manifests, upgrade a populated installation, and run integrity, query, startup, database-size, memory, and migration measurements.

**Acceptance Scenarios**:

1. **Given** identical pinned inputs, **when** two clean builds run, **then** the release database and manifest are byte-for-byte or canonically deterministic with matching hashes.
2. **Given** an existing installation containing profiles, assessments, evidence, and exceptions, **when** the catalog upgrade runs, **then** all operational rows and relationships are preserved.
3. **Given** no established performance threshold for a metric, **when** qualification runs, **then** the baseline is recorded without inventing a release threshold.
4. **Given** an established project threshold, **when** performance exceeds it, **then** release qualification fails with reproducible evidence.

### Edge Cases

- A raw record can contribute only a framework crosswalk or relationship and no canonical content.
- One raw record may be split across multiple canonicals, while one canonical may be supported by multiple raw records.
- Duplicate or rejected raw records remain preserved and traceable.
- Low-confidence classification remains deferred or review-flagged when no defensible type exists; it is never silently defaulted to `ART-CTR`.
- A workbook contains duplicate row identities, modified hidden baseline hashes, unsupported actions, or changes to immutable identifiers.
- A transactional apply fails midway and must leave both catalog and audit state recoverable.
- A source version is unavailable and must be recorded as `UNKNOWN` with a reason.
- A source contains text whose redistribution permission is unknown or restricted.
- A canonical is deprecated without deleting template, mapping, lineage, or historical profile references.
- A release candidate is valid but smaller or larger than a previous performance corpus; measurements must disclose the population.

## Requirements

### Functional Requirements

- **FR-001**: The catalog MUST distinguish the lifecycle states `RAW`, `MINIMUM_VALID`, and `ENRICHED` from human-review state and classification quality.
- **FR-002**: `NOT_REVIEWED` MUST be valid for `MINIMUM_VALID`, and the system MUST NOT claim human review without recorded evidence.
- **FR-003**: The project MUST maintain one versioned minimum-entry contract that defines core requirements, conditional type requirements, and enrichment-only fields.
- **FR-004**: Every minimum-valid canonical MUST have stable identity, type, English title and short definition, single valid domain and sub-domain, abstraction level, source metadata, obligation and granularity, classification confidence and rationale, publication/catalog state, active state, and at least one valid raw-source lineage record.
- **FR-005**: `ART-REQ` MUST require `requirement_type`; `ART-CTR` and `ART-CTE` MUST require `control_nature`, `control_function`, and `testability`; `ART-AST` MUST require `asset_type` and `asset_criticality`.
- **FR-006**: `ART-RSK` MUST have a required remediation relationship or action.
- **FR-007**: `ART-EXC` and applicable published policy, standard, and procedure types MUST satisfy their authoritative date requirements.
- **FR-008**: Arabic content, full definitions, guidance, extended mappings, platforms, threats, stakeholders, cost, and maturity MUST remain enrichment-only for minimum entry.
- **FR-009**: Minimum catalog validation and strict USACM conformance MUST be evaluated and reported as separate results.
- **FR-010**: Low-confidence artifacts MAY enter when structurally valid and explicitly flagged, but uncertain artifacts MUST NOT default to `ART-CTR`; indefensible classifications MUST be deferred with a reason.
- **FR-011**: Every raw record MUST have exactly one traceable disposition from `SUPPORTS_CANONICAL`, `SPLIT`, `DUPLICATE`, `CROSSWALK_ONLY`, `RELATION_ONLY`, `REJECTED`, or `DEFERRED`.
- **FR-012**: Every canonical MUST have at least one valid final raw-source lineage record, and every raw record supporting a canonical MUST have a matching lineage record.
- **FR-013**: Closure validation MUST reject dangling lineage, mappings, relationships, and disposition-to-lineage inconsistencies.
- **FR-014**: Raw provenance MUST include source catalog, source document, content hash, pinned source or manifest hash, and source version or explicit `UNKNOWN` with reason; section/location and retrieval metadata MUST be recorded when available.
- **FR-015**: The system MUST NOT invent unavailable provenance metadata.
- **FR-016**: Source-rights metadata MUST be versioned and MUST default to excluding raw source text from mobile releases when redistribution permission is unknown or restricted.
- **FR-017**: The catalog database MUST remain the system of record while the workbook is the primary bulk human-curation interface.
- **FR-018**: The workbook MUST contain sheets `00_Manifest`, `01_Artifacts`, `02_Source_Lineage`, `03_Framework_Mappings`, `04_Relationships`, `05_Tags`, `06_Type_Specific`, `07_Reference_Lists`, and `08_Validation_Errors`.
- **FR-019**: The workbook workflow MUST support `export`, `validate`, `plan`, and transactional `apply` operations.
- **FR-020**: Workbook row actions MUST be limited to `NO_CHANGE`, `UPSERT`, and `DEPRECATE`; omission MUST mean `NO_CHANGE` and MUST never cause physical deletion.
- **FR-021**: Exported rows and manifests MUST be versioned and hashed for conflict detection, with controlled-value lists exposed for human selection.
- **FR-022**: A changed database baseline or row hash MUST produce `CONFLICT`; conflicting rows MUST NOT be applied without an explicit, audited per-record or plan-level resolution that still passes validation.
- **FR-023**: Catalog, classification-quality, and human-review states MUST remain semantically separate, reusing existing fields unless a demonstrated semantic gap requires a new field.
- **FR-024**: Curation and qualification MUST operate on a working or release-candidate database and MUST NOT modify `mobile/assets/catalog.db` directly.
- **FR-025**: The process MUST preserve every raw source record, canonical stable ID, final lineage record, catalog/profile separation, existing operational rows, and audit history.
- **FR-026**: The complete corpus MUST be normalized globally, checked for similarity, equivalence, duplicates, and conflicts, reviewed through SD-01 to SD-08 checkpoints, and reconciled globally before release.
- **FR-027**: Release construction MUST pin source versions and hashes and produce a reproducible manifest.
- **FR-028**: Qualification MUST measure representative query latency, startup impact, database size, memory impact, migration duration, and integrity validation on declared target profiles.
- **FR-029**: Existing project thresholds MUST be enforced; new arbitrary release thresholds MUST NOT be invented without evidence.
- **FR-030**: A supported upgrade MUST preserve profiles, selected controls, assessments, evidence, exceptions, and related operational history.
- **FR-031**: All schema changes MUST use migrations with constraints, foreign keys, expected-filter indexes, recovery notes, and validation tests.
- **FR-032**: Release construction MUST be deterministic and auditable from pinned input manifests through the final candidate hash.

### Key Entities

- **Minimum Field Contract**: Versioned definition of core, type-specific, and enrichment-only catalog fields.
- **Canonical Control**: The normalized SecureGuide-authored catalog element, regardless of USACM artifact type.
- **Raw Source Record**: Preserved source intake record with provenance and content integrity metadata.
- **Raw Disposition**: Final accountable outcome assigned to each raw record.
- **Source Lineage**: Normalized evidence-bearing link between a canonical and a raw source record.
- **Source Rights Record**: Versioned decision governing retention and redistribution of source content.
- **Curation Workbook**: Versioned, hashed bulk-edit representation of catalog and reference data.
- **Import Plan**: Deterministic proposed set of row actions, conflicts, validation outcomes, and audit metadata.
- **Release Manifest**: Pinned inputs, counts, validation results, performance evidence, and release candidate hashes.

## Success Criteria

### Measurable Outcomes

- **SC-001**: 100 percent of raw records have exactly one valid disposition.
- **SC-002**: 100 percent of minimum-valid canonicals have at least one valid final lineage record.
- **SC-003**: 100 percent of raw records with `SUPPORTS_CANONICAL` or `SPLIT` dispositions have matching lineage.
- **SC-004**: Minimum-valid canonicals have zero missing core-required fields and zero missing applicable type-required fields.
- **SC-005**: Integrity validation reports zero broken foreign keys and zero dangling lineage, mappings, or relationships.
- **SC-006**: Export-edit-validate-plan-apply succeeds for a valid workbook and records an auditable transaction.
- **SC-007**: Stale-edit tests reject 100 percent of changed-baseline and changed-row-hash cases.
- **SC-008**: Workbook row omission causes zero database mutations and zero physical deletions.
- **SC-009**: Two clean release builds from identical pinned inputs produce identical catalog and manifest hashes.
- **SC-010**: Upgrade qualification preserves 100 percent of seeded profile, assessment, evidence, exception, and profile-control rows.
- **SC-011**: Every released raw-text payload has an explicit permission allowing redistribution; unknown or restricted content contributes zero raw text to the mobile release.
- **SC-012**: Each SD-01 through SD-08 checkpoint and the final global reconciliation produces a recorded result.
- **SC-013**: Performance evidence discloses target profile, corpus counts, query plans, and all six required measurement categories.
- **SC-014**: Minimum validation and strict conformance are independently reportable for every evaluated canonical.

## Assumptions

- The existing 30-migration SQLite schema, Python build-time tooling, and Flutter runtime remain the implementation foundation unless research demonstrates an incompatibility.
- Existing canonical IDs and operational/profile data are immutable compatibility boundaries.
- The approved disposition vocabulary is exhaustive for this feature; additional values require a future owner decision.
- Missing optional enrichment, Arabic localization, low confidence, and absent human review do not globally block minimum-valid entry.
- Source metadata that cannot be recovered will be represented explicitly as unknown with a reason, never fabricated.
- The existing release process remains responsible for replacing the bundled mobile catalog after candidate qualification.
