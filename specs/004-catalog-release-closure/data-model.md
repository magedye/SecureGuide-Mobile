# Data Model: Catalog Release Closure

## Quality profiles

`catalog_minimum_fields.yaml` is the versioned machine-readable contract. It defines:

- `MINIMUM_VALID`: identity, content, controlled classifications, SDT pair integrity, traceable source, raw disposition coverage, and required type-specific fields.
- `STRICT_USACM`: minimum-valid plus strict review/publication/confidence requirements.
- `ENRICHED`: strict requirements plus normalized mappings, tags, relationships, applicability, verification guidance, and optional type-enrichment thresholds.

Validation returns a profile result independently; failure of `STRICT_USACM` must not relabel a passing `MINIMUM_VALID` record as structurally invalid.

## `catalog_artifact_id_aliases`

| Column | Type | Rules |
|---|---|---|
| `old_artifact_id` | TEXT | Primary key; non-empty legacy identifier |
| `artifact_id` | TEXT | Required foreign key to `security_artifacts.artifact_id` in a release candidate |
| `reason` | TEXT | Required migration/identity reason |
| `created_at` | TEXT | Required ISO-8601 UTC timestamp |

Aliases are immutable within a release. Chains are prohibited; `artifact_id` must be a current canonical ID. During an installed upgrade, all profile and catalog child references are resolved before commit.

## Neutral legacy-source tables

Migration 034 replaces active schema names while preserving data:

- `legacy_domain_alias(legacy_key, sdt_primary, sdt_sub, confidence, needs_review, note)`
- `legacy_threat_alias(legacy_key, threat_code, needs_review)`
- `catalog_legacy_assets(artifact_id, asset_ref)`
- `catalog_legacy_provenance(artifact_id, legacy_id, legacy_domain, legacy_sub)`

Historical migration files remain immutable and are the only approved schema-name exception.

## Pinned classification document

Top-level fields:

- `schema_version`
- `classifier_version`
- `source_catalog_id`
- `source_file`
- `input_sha256`
- `generated_at`
- `items`

Each item contains:

- source and raw identity
- normalized title and description hash
- `type`
- `abstraction_level`
- `primary_domain` and `sub_domain`
- `classification_confidence`
- `classification_rationale`
- `ai_review_status`
- `requires_human_review`
- `rejected_alternatives`
- applicable type-specific fields such as `requirement_type`, control nature/function, or configuration value metadata

## Raw disposition closure

Each `raw_artifacts.raw_artifact_id` has exactly one `raw_artifact_dispositions` row with:

- disposition code
- optional canonical artifact reference
- rationale and decision basis
- confidence with explicit sentinel semantics
- review state
- decision timestamp and tool/version provenance

Allowed minimum closure outcomes include canonical promotion/support, valid deferral, exclusion, duplicate/equivalence handling, and invalid-source quarantine as defined by the contract. A disposition referencing a canonical row must resolve to an existing current ID or alias.

## Workbook v3 aggregate

The workbook manifest binds:

- workbook and schema contract versions
- export mode (`COMPLETE` or `FILTERED`)
- deterministic filter JSON
- minimum contract hash
- source manifest hash
- source rights hash
- database content hash
- canonical/raw/disposition/lineage row counts
- per-sheet row counts and headers
- generation timestamp and tool version

The workbook contains canonical artifacts plus normalized child tables and the complete raw disposition ledger for `COMPLETE` mode. A filtered workbook includes selected artifacts, their dependent normalized rows, and the raw rows/dispositions needed to explain their source lineage; the manifest states that it is not a global closure ledger.

## Upgrade invariants

- Catalog reference data can change; enterprise/profile operational rows cannot be discarded.
- Every old referenced artifact ID resolves to a current artifact or causes rollback.
- `PRAGMA foreign_key_check` returns no rows.
- `PRAGMA integrity_check` returns `ok`.
- The new `release_manifest` and content hash match the candidate package.
- Any failure rolls back the entire catalog/schema/alias update.

