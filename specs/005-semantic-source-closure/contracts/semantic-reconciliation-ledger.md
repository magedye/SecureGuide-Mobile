# Semantic Reconciliation Ledger Contract v1

## Purpose

Define the immutable, source-hash-bound input that reconciles every authoritative raw record without a generic default disposition.

## Required entry fields

| Field | Requirement |
|---|---|
| `raw_id` | Unique raw record identifier present in the pinned corpus. |
| `source_content_sha256` | Must match the current raw record canonical content hash. |
| `disposition` | One of `SUPPORTS_CANONICAL`, `SPLIT`, `DUPLICATE`, `CROSSWALK_ONLY`, `RELATION_ONLY`, `REJECTED`, `DEFERRED`. |
| `decision_method` | Versioned deterministic method or named owner decision. |
| `confidence_state` | Explicitly distinguishes a numeric score from `UNSCORED`. |
| `rationale` | Specific to this raw record and outcome; generic fallback language is invalid. |
| `links` | Required where a disposition targets an existing canonical/raw record; each link supplies a target, strength, and rationale where required. |

## Rules

1. The ledger covers every raw record exactly once and rejects stale or duplicate entries.
2. `SUPPORTS_CANONICAL` and `SPLIT` must create matching `artifact_source_lineage` rows.
3. `DUPLICATE`, `CROSSWALK_ONLY`, and `RELATION_ONLY` must create normalized reconciliation links, not fabricated final lineage.
4. `DEFERRED` requires a controlled reason code and a record-specific explanation; it cannot claim missing historical classifier evidence.
5. New canonical entries require an atomic authored candidate and independent type, abstraction, and SDT decisions.
6. All target artifact/raw identifiers must exist in the transaction scope.

## Closure outputs

The curation report exposes counts by source, disposition, decision method, confidence state, deferred reason category, link type, final lineage, semantic corrections, and unresolved errors.
