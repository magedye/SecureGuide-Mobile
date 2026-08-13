# Data Model: Comprehensive Catalog Workbook v2

## Workbook Projection

The workbook is a deterministic projection of the Master Catalog. Each editable sheet contains:

- `_action`: `NO_CHANGE`, `UPSERT`, or artifact-only `DEPRECATE`.
- `_baseline_key`: hash of the table's primary-key fields.
- `_baseline_hash`: hash of every exported business column.
- Every SQLite column from the represented table, in schema order.

## In-Scope Tables

Core tables: `security_artifacts`, `artifact_source_lineage`, `framework_mappings`, `artifact_relationships`, and `artifact_tags`.

Normative reference details: `artifact_applicability_scope`, `artifact_self_assessments`, `technical_dependencies`, `verification_tools`, `stakeholders`, `remediation_actions`, and `external_references`.

Project catalog enrichment: `artifact_localizations`, `artifact_actions`, `artifact_variants`, `artifact_security_objectives`, `artifact_csf_functions`, `artifact_control_purposes`, `artifact_implementation_types`, `artifact_maturity_requirements`, `artifact_verification_evidence_types`, `artifact_threats`, `artifact_platforms`, `catalog_amani_assets`, and `catalog_amani_provenance`.

`06_Type_Specific` remains a governed view over type-dependent columns in `security_artifacts`.

## Excluded Data

- Profile and operational state (`profile_*`, enterprise assets, indicators, playbooks, blueprints).
- Raw payload text and raw JSON.
- Derived embeddings and other generated search indexes.
- Curation workflow state not constituting a catalog artifact detail.

## Validation Rules

- Worksheet order and headers exactly match contract v2.
- Row identities use authoritative primary keys, including composite keys.
- Duplicate row identities fail validation.
- Controlled values are sheet-qualified.
- Omission is `NO_CHANGE`; child `DEPRECATE` is invalid.
- Relationships affect and revalidate both source and target artifacts.
- Manifest counts must match the unchanged exported database projection.
