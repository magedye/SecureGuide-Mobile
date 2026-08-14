# Feature Specification: Comprehensive Catalog Export

**Feature Directory**: `specs/003-comprehensive-catalog-export`
**Created**: 2026-08-14
**Input**: Make the catalog export tool include every catalog control and all normalized reference details linked to each control.

## User Scenarios & Testing

### User Story 1 - Export the Complete Master Catalog (Priority: P1)

As a catalog curator, I can export every catalog artifact and every normalized Master Catalog detail linked to it so that I can review the complete reference model without querying the database manually.

**Independent Test**: Export a seeded catalog containing one row in every supported reference-detail collection and verify that every artifact and detail row appears once in the expected worksheet with all database columns.

**Acceptance Scenarios**:

1. **Given** a catalog with artifacts of multiple USACM types, **when** export runs without filters, **then** every row in `security_artifacts` appears in `01_Artifacts` regardless of review state or artifact type.
2. **Given** normalized detail rows linked to artifacts, **when** export runs, **then** each supported Master Catalog child table has a dedicated worksheet containing all of its columns and rows.
3. **Given** an empty supported detail table, **when** export runs, **then** its worksheet is still present with the complete header contract.
4. **Given** operational/profile data, raw payload text, or derived embeddings, **when** export runs, **then** those records are excluded from the catalog-curation workbook.

### User Story 2 - Curate Complete Details Safely (Priority: P1)

As a human curator, I can validate, plan, and apply edits made to any exported Master Catalog detail while retaining conflict detection, controlled values, audit evidence, and no-deletion-by-omission semantics.

**Independent Test**: Edit one newly supported detail row using `UPSERT`, validate and plan it, apply it to a working database, and verify the database change and row-level audit; then prove duplicate identities, stale rows, and `DEPRECATE` on child rows are rejected.

**Acceptance Scenarios**:

1. **Given** an exported detail row, **when** a valid `UPSERT` is applied, **then** only that normalized row changes and the affected artifact is revalidated.
2. **Given** a controlled detail field, **when** the workbook is opened, **then** the relevant controlled list is exposed for selection and invalid values fail validation.
3. **Given** an omitted detail row, **when** the workbook is applied, **then** omission causes no deletion or mutation.
4. **Given** a stale detail row or database baseline, **when** planning runs, **then** it produces a conflict and does not silently overwrite current data.

### Edge Cases

- A detail table is present in the schema but contains zero rows.
- A detail row uses a composite primary key.
- A relationship references two catalog artifacts and both must remain valid.
- A detail table has a column name such as `type` or `status` whose controlled list differs from the artifact table.
- A workbook is missing, reorders, or adds worksheets outside the declared contract.

## Requirements

### Functional Requirements

- **FR-001**: Export MUST include 100 percent of rows and columns from `security_artifacts` by default, with no artifact-type or human-review filter.
- **FR-002**: Export MUST include dedicated normalized worksheets for source lineage, mappings, relationships, tags, applicability, reference self-assessments, dependencies, verification tools, stakeholders, remediation actions, external references, localizations, actions, variants, security objectives, CSF functions, control purposes, implementation types, maturity requirements, verification-evidence types, threats, platforms, and neutral legacy catalog enrichment.
- **FR-003**: Each supported detail worksheet MUST expose every column in its authoritative SQLite table and MUST preserve composite row identities.
- **FR-004**: The workbook manifest MUST declare the contract version, relative source database path, artifact count, per-sheet row counts, and the export/exclusion boundary.
- **FR-005**: Operational/profile tables, raw source payload text, and derived embedding vectors MUST remain outside the Master Catalog curation workbook.
- **FR-006**: Exported controlled fields MUST use the authoritative USACM/SDT/project reference lists, including sheet-specific fields whose names overlap other meanings.
- **FR-007**: Validation, planning, conflict detection, transactional apply, and audit MUST cover every editable detail worksheet.
- **FR-008**: Workbook omission MUST remain `NO_CHANGE`; only artifact rows MAY use `DEPRECATE`; physical deletion MUST NOT be introduced.
- **FR-009**: Applying a detail change MUST revalidate the linked artifact or both linked artifacts for relationships.
- **FR-010**: Paths recorded inside workbook metadata and generated evidence MUST be repository-relative when the target is inside the project.
- **FR-011**: The export MUST remain deterministic for the same database state and MUST preserve SQLite as the system of record.

### Key Entities

- **Catalog Artifact**: The canonical Master Catalog row in `security_artifacts`.
- **Catalog Detail Collection**: A normalized, repeatable reference-data table linked to one or more catalog artifacts.
- **Workbook Contract**: The ordered worksheet set, columns, controlled lists, row identities, and hashes governing round-trip curation.
- **Operational Data Boundary**: Profile-specific, raw-payload, and derived-index data intentionally excluded from this export.

## Success Criteria

- **SC-001**: A release-database export contains exactly the same artifact count as `security_artifacts` and the same row count as every supported detail table.
- **SC-002**: Every supported worksheet contains 100 percent of its authoritative table columns, including empty tables.
- **SC-003**: An unchanged comprehensive workbook validates with zero errors.
- **SC-004**: A valid edit to each supported detail-table shape can be planned and applied without changing unrelated rows.
- **SC-005**: Duplicate identities, invalid controlled values, stale changes, and child-row deprecation are rejected in 100 percent of tested cases.
- **SC-006**: No operational/profile rows, raw source payload text, or embedding vectors appear in the exported workbook.

## Assumptions

- The term "controls" means all catalog artifacts regardless of USACM artifact type.
- "Complete details" means all normalized Master Catalog reference and enrichment tables linked to artifacts; it does not collapse profile-specific state into the catalog.
- Raw payload content remains governed by source-rights rules and is not part of the human-curation workbook.
