# Catalog Validation Contract v1

## Required outputs

The validator returns independent `MINIMUM_CATALOG_VALIDATION` and `STRICT_USACM_CONFORMANCE` results plus closure, integrity, provenance, rights, and corpus summaries.

## Minimum validation

`config/catalog_minimum_fields.yaml` is authoritative. Every active catalog-ready canonical satisfies core fields, applicable type fields, and final raw lineage. Low confidence and `NOT_REVIEWED` remain valid when uncertainty and USACM review flags are correct.

## Strict conformance

Strict results evaluate all applicable USACM v2.2.1 validation rules without changing minimum results.

## Closure

- Every raw record has one allowed disposition.
- Every canonical has lineage.
- Supporting/split dispositions have matching lineage.
- Lineage, mappings, relationships, manifests, and rights references resolve.
- SQLite integrity and foreign-key checks succeed.

## Exit codes

- `0`: all requested gates pass.
- `1`: validation failure.
- `2`: qualification blocked by a declared prerequisite, with an explicit blocker code.
