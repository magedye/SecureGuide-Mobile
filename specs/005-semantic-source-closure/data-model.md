# Data Model: Semantic Source Closure

## Existing entities retained

| Entity | Role | Invariant |
|---|---|---|
| `raw_artifacts` | Immutable authoritative source record | Never deleted or silently overwritten. |
| `raw_artifact_dispositions` | One reconciliation outcome per raw record | Exactly one allowed disposition and meaningful rationale. |
| `security_artifacts` | Master Catalog canonical | One USACM type and one valid SDT pair; no operational profile state. |
| `artifact_source_lineage` | Supporting/split raw provenance for a canonical | Every canonical has at least one row; support/split decisions match it. |
| `artifact_id_aliases` | Historical ID compatibility | Stable aliases resolve without breaking profile references. |

## New normalized entity

### `raw_artifact_reconciliation_links`

Represents a non-destructive relationship from a raw record to a canonical or raw target when final lineage would be semantically false.

| Field | Purpose | Rules |
|---|---|---|
| `raw_artifact_id` | Source record | Foreign key to `raw_artifacts`; part of key. |
| `link_index` | Stable ordinal for multiple links | Non-negative; part of key. |
| `disposition` | Outcome context | Allowed non-lineage dispositions or explicit split support context. |
| `target_artifact_id` | Canonical target | Nullable only when target is raw; foreign key when present. |
| `target_raw_artifact_id` | Raw target | Nullable only when target is canonical; foreign key when present. |
| `mapping_strength` | Relationship strength | USACM controlled value. |
| `rationale` | Evidence explanation | Required for all non-direct/non-trivial links. |
| `evidence_method` | Deterministic decision provenance | Non-empty ledger method/version. |

## Disposition decision input

Each ledger entry contains raw ID, source content hash, disposition, decision method, confidence state, review routing, substantive rationale, zero or more reconciliation links, and optional new-canonical or semantic-correction reference. The loader rejects duplicate raw IDs, stale hashes, unsupported controlled values, missing targets, generic defer text, and mismatched source provenance.

## Deferred reason categories

`DEFERRED` records use a controlled reason code such as insufficient authoritative context, genuinely composite unresolved scope, ambiguous artifact boundary, or conflicting authoritative evidence. A code does not replace the record-specific rationale.

## State transitions

1. Pinned raw source is ingested unchanged.
2. A source-hash-bound decision is loaded and validated.
3. Existing canonical reconciliation, semantic corrections, and only genuine new canonical creation are projected.
4. Dispositions, links, and matching final lineage are written transactionally.
5. Closure validators, workbook, release candidate, and upgrade validation consume the resulting candidate.
