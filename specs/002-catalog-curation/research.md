# Research: Complete Catalog Curation

## Decision 1: Derive MINIMUM_VALID; do not add another lifecycle status

**Decision**: Make `config/catalog_minimum_fields.yaml` the versioned contract and compute `MINIMUM_CATALOG_VALIDATION`. Continue to use `publication_status`, AI review fields, and localization review fields for their existing distinct meanings.

**Rationale**: The schema already separates publication, classification quality, human review, localized-content review, and profile operational state. Reusing any one for minimum validity would collapse forbidden meanings.

**Alternatives considered**: A new `catalog_status` column and reuse of localization `content_maturity` were rejected as duplicate or incorrect state.

## Decision 2: Preserve strict USACM as a separate validator

**Decision**: Return `MINIMUM_CATALOG_VALIDATION` from the project contract and `STRICT_USACM_CONFORMANCE` from USACM rules. Promotion and release report both without aliasing them.

**Rationale**: Existing promotion rejects low confidence and missing human approval. That can remain an optional strict/review gate but cannot determine minimum entry after the owner's decision.

**Alternatives considered**: Weakening USACM and retaining the current promotion gate as the minimum validator were rejected.

## Decision 3: Add normalized closure facts in migration 031

**Decision**: Add source import manifests, versioned source rights, exactly-one raw dispositions, and many-to-many final canonical lineage. Staging JSON remains transient input only.

**Rationale**: `raw_artifacts.promoted_artifact_id` cannot represent split or many-source lineage, and the release gate currently reconstructs lineage from staging JSON.

**Alternatives considered**: Extending `framework_mappings` with `raw_id` and reusing `merge_action` were rejected because their claims differ from source contribution and raw disposition.

## Decision 4: Fail closed on source rights while retaining raw identity

**Decision**: Unknown or restricted rights set `ship_raw_text=0`. Working databases retain full payloads; release candidates retain identity, provenance, hashes, dispositions, and lineage but scrub protected text-bearing columns unless a versioned `ALLOWED` decision permits shipment.

**Rationale**: The current mobile asset ships raw text without rights metadata. The owner requires default non-shipment when rights are unknown or restricted.

**Alternatives considered**: Guessing rights from publisher names and dropping raw rows were rejected. Destructively splitting legacy tables is unnecessary for this release-copy approach.

## Decision 5: Use a deterministic global projection over defensible candidates

**Decision**: Use the existing 1,467 curated/Amani staging candidates plus `consolidation/unified/equivalence.json`. Select each declared group canonical and standalone candidates, apply the minimum contract, and disposition every other raw row explicitly. No type is fabricated for rows lacking defensible evidence.

**Rationale**: The existing projection yields 1,223 candidates. A live contract simulation found 1,068 minimum-valid canonicals after excluding 153 missing-confidence candidates, one invalid `ART-AST`, and one `ART-RSK` without remediation evidence. This clears the existing provisional performance population without synthetic duplication.

**Alternatives considered**: Defaulting to `ART-CTR`, promoting all staged duplicates, and blocking globally on review state were rejected.

## Decision 6: One conflict-safe workbook CLI

**Decision**: Implement `export`, `validate`, `plan`, and transactional `apply` in `secureguide/catalog_workbook.py`, exposed by `scripts/catalog_workbook.py`. Pin `openpyxl==3.1.5` for build-time use.

**Rationale**: Existing tooling is only a one-way first-sheet import. Existing promotion supplies useful hashing and transaction patterns but not the nine-sheet contract.

**Alternatives considered**: Pandas, Excel as system of record, and `INSERT OR REPLACE` were rejected.

## Decision 7: Hash semantic content, not formatting

**Decision**: SHA-256 covers Unicode-normalized canonical JSON with sorted keys, explicit nulls, and whitelisted fields. The workbook manifest pins database, contract, schema, reference-list, and payload hashes. Each editable row carries stable key, version, baseline hash, and action.

**Rationale**: Formatting changes must not create false conflicts; stale database or row changes must fail closed.

**Alternatives considered**: Latest-wins and hashing XLSX bytes were rejected.

## Decision 8: Restrict initial workbook deletion semantics

**Decision**: Omission is `NO_CHANGE`. `DEPRECATE` is supported only for canonical artifacts and performs a logical update. Child-row deletion remains unsupported until a lifecycle contract exists.

**Rationale**: This preserves IDs, lineage, templates, and profile history and keeps the first implementation recoverable.

## Decision 9: Make the release pair deterministic and atomic

**Decision**: Build database and manifest in staging paths, normalize technical timestamps, hash all governed inputs, verify the pair, then promote it to the requested candidate location. Volatile run metadata is separate.

**Rationale**: The current database is reproducible from a pinned prebuilt database, but the manifest contains current time and is written after database replacement.

## Decision 10: Add catalog-data upgrade, not only schema migration

**Decision**: Qualify an additive catalog merge from a candidate into a cloned installed database with backup, transaction, stable-ID checks, profile snapshots, integrity/FK checks, and rollback.

**Rationale**: Mobile startup copies the asset only on first install; schema migrations do not import later catalog content.

## Decision 11: Treat 1,000 as provisional, not catalog truth

**Decision**: Record the declared release population and retain current p95 budgets as regression thresholds. Add startup, database size, memory, migration duration, and integrity measurements. Do not equate the provisional floor with semantic completeness.

**Rationale**: The current budget labels the floor provisional, and the owner prohibits invented thresholds.
