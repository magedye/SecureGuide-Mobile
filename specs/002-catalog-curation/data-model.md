# Data Model: Complete Catalog Curation

## Existing entities retained

- `source_catalogs` and `raw_artifacts`: preserved intake.
- `staging_artifacts`: mutable curation drafts.
- `security_artifacts`: canonical Master Catalog.
- Existing normalized catalog child tables: reference metadata.
- `enterprise_profiles` and all `profile_*` tables: operational data, never catalog state.

## SourceImportManifest

Immutable record for the exact source file or retrieval used by an import.

Fields: `id`, `source_catalog_id`, `source_version`, `version_unknown_reason`, `source_file`, `source_sha256`, `manifest_sha256`, `retrieval_uri`, `retrieved_at`, `importer_name`, `importer_version`, `raw_record_count`, `created_at`.

Rules: hashes are 64-hex; unknown versions require a reason; counts are non-negative; `raw_artifacts.source_manifest_id` references this entity.

## SourceRightsVersion

Immutable, versioned decision governing raw source shipment.

Fields: `id`, `source_catalog_id`, `source_version`, `rights_version`, `redistribution_status`, `ship_raw_text`, `license_identifier`, `terms_url`, `evidence_sha256`, `evidence_retrieved_at`, `attribution_text`, `decision_reason`, `decided_by`, `decided_at`, `supersedes_id`, `is_current`.

Rules: status is `ALLOWED`, `RESTRICTED`, or `UNKNOWN`; raw text ships only when explicitly allowed; at most one current record exists per source/version.

## RawArtifactDisposition

Exactly one final curation outcome per raw record.

Fields: `raw_artifact_id`, `disposition`, `rationale`, `related_raw_artifact_id`, `decision_method`, `decision_confidence`, `requires_human_review`, `decided_by`, `decided_at`, `decision_batch_id`.

States: `SUPPORTS_CANONICAL`, `SPLIT`, `DUPLICATE`, `CROSSWALK_ONLY`, `RELATION_ONLY`, `REJECTED`, `DEFERRED`.

Rules: primary key enforces one disposition; duplicates identify an existing raw record; every state has rationale; uncertainty is explicit.

## ArtifactSourceLineage

Final many-to-many contribution relation.

Fields: `artifact_id`, `raw_artifact_id`, `lineage_role`, `mapping_strength`, `rationale`, `is_primary`, `created_at`.

Rules: primary key `(artifact_id, raw_artifact_id)`; role is `SUPPORTS_CANONICAL` or `SPLIT`; non-direct strength requires rationale; every minimum-valid canonical has lineage; every supporting/split raw disposition has matching lineage.

For `ART-RSK`, minimum remediation is satisfied by either at least one `remediation_actions` row owned by the risk artifact or an incoming `artifact_relationships` row with `relation_type=REL-MIT` whose source is the mitigating control and target is the risk.

## CatalogWorkbookRun

Audit envelope for one workbook operation.

Fields: `id`, `operation`, `status`, `actor`, `workbook_hash`, `baseline_hash`, `plan_hash`, `contract_hash`, `schema_version`, `started_at`, `completed_at`, `notes`.

## CatalogWorkbookRunItem

Audit record for each proposed or applied workbook row.

Fields: `run_id`, `sheet_name`, `row_key`, `entity_kind`, `action`, `baseline_hash`, `current_hash`, `proposed_hash`, `result`, `resolution_actor`, `resolution_reason`, `detail`.

Rules: actions are `NO_CHANGE`, `UPSERT`, `DEPRECATE`; conflicts never apply automatically; resolution never bypasses validation.

## Validation result model

Deterministic JSON reports hold validator and input hashes, separate minimum/strict per-canonical results, closure/integrity findings, and summaries by outcome/type/domain. Validity is derived, not stored as duplicate lifecycle state.

## State transitions

```text
raw intake -> explicit disposition -> defensible staging candidate
           -> MINIMUM_VALID or deferred -> optional ENRICHED
           -> independent human review -> release qualification
           -> verified catalog-data upgrade
```
