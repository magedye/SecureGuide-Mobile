# Research: Comprehensive Catalog Export

## Decision 1: Contract shape

**Decision**: Introduce `secureguide-catalog-workbook-v2`, preserve the original nine sheets first, and append dedicated normalized detail sheets.

**Rationale**: Dedicated sheets preserve the database model, expose every column, support composite keys, and are auditable. Retaining the first nine sheets minimizes curator disruption.

**Alternatives considered**:

- Flatten repeatable details into `01_Artifacts`: rejected because it duplicates rows and obscures normalized identity.
- Store child collections as JSON cells: rejected because it weakens controlled editing and conflicts with the normalized model.
- Replace the workbook with CSV files: rejected because it loses one governed, controlled, multi-table curation surface.

## Decision 2: Scope boundary

**Decision**: Include all normalized catalog reference/enrichment tables linked directly to artifacts. Exclude profile/operational tables, raw source payloads, generated embeddings, and workflow blueprints.

**Rationale**: This matches the Master Catalog boundary and avoids exporting organization-specific state or rights-sensitive/derived content.

**Alternatives considered**:

- Export every database table: rejected because it would mix catalog and operational state and expose governed raw payloads.
- Export only the ten normative USACM child tables: rejected because project-specific localizations, actions, threats, platforms, and Amani provenance are real catalog details the user asked to retain.

## Decision 3: Round-trip behavior

**Decision**: Every added detail sheet participates in `NO_CHANGE`/`UPSERT`, hashing, validation, planning, conflict detection, apply, and audit. `DEPRECATE` remains artifact-only.

**Rationale**: A comprehensive curation workbook must not present editable-looking details that silently fall outside the governed workflow.

**Alternatives considered**:

- Read-only detail sheets: rejected because it makes the workbook incomplete as the primary bulk-curation interface.
- Physical delete actions: rejected because omission and delete protections are non-negotiable.
