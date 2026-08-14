# Research: Catalog Release Closure

## Decision 1: Separate catalog entry quality from strict publication quality

**Decision**: Define three explicit quality profiles: `MINIMUM_VALID`, `STRICT_USACM`, and `ENRICHED`. A record may enter the minimum-valid catalog while still carrying `AIR-HUMAN-REVIEW`, `requires_human_review=1`, or low/unknown confidence, provided structural, lineage, controlled-value, SDT, and type-specific minimum requirements pass. Strict publication remains fail-closed.

**Rationale**: Review state and confidence are quality facts, not evidence that the record is structurally unusable. Conflating them caused 719 review-pending artifacts to block a catalog already large enough for the minimum product objective.

**Alternatives considered**:

- Require human approval for every catalog row: preserves a strict gate but prevents a truthful minimum catalog and does not scale to all imported content.
- Auto-approve low-confidence rows: meets quantity but falsely converts uncertainty into authority and violates accountable classification.

## Decision 2: Pin classifier output and make rebuilding explicit

**Decision**: Commit `legacy_classifications.json` with input hash, classifier version, per-record type/level/domain/confidence/rationale/rejected alternatives, and type-specific fields. Normal curation loads it and fails on drift. Regeneration occurs only through an explicit `--rebuild` command.

**Rationale**: This prevents library changes or heuristic edits from silently changing release content while still allowing reviewed classifier evolution.

**Alternatives considered**:

- Classify on every release build: easy to implement but not reproducible and obscures semantic drift.
- Retain the legacy all-control staging hints: deterministic but semantically invalid.

## Decision 3: Use forward-only neutral identity with durable aliases

**Decision**: Keep immutable historical migrations as audit evidence, add migration 034 that exposes neutral schema/table/column names, change current source IDs, staging IDs, canonical IDs, scripts, documents, and workbook labels to neutral names, and persist `catalog_artifact_id_aliases(old_artifact_id, artifact_id, reason, created_at)`.

**Rationale**: Existing installations and external references may contain old IDs. Aliases allow transactional remapping while removing the former product name from current public contracts.

**Alternatives considered**:

- Rewrite historical migrations: removes text but destroys migration immutability and upgrade confidence.
- Leave current identifiers unchanged: lowest engineering cost but fails the product identity requirement and keeps source-biased canonical IDs.

## Decision 4: Add raw dispositions as a first-class workbook sheet

**Decision**: Workbook contract v3 contains `09_Raw_Dispositions`, shifts subsequent detail sheets, uses neutral sheet names, and includes all governed columns. Complete exports include every canonical artifact and raw disposition. Filtered exports scope canonical rows and dependent rows deterministically and record the applied filters in the manifest.

**Rationale**: A curator must be able to account for every imported raw item, including deferred items that have no canonical row.

**Alternatives considered**:

- Include dispositions only in JSON: machine-readable but breaks the requested single review workbook.
- Export only dispositions linked to canonical artifacts: hides deferred raw records and prevents total reconciliation.

## Decision 5: Treat `0.0` confidence explicitly

**Decision**: `0.0` is permitted only when a non-empty rationale states that confidence is an explicit unknown/unassessed sentinel and the row requires human review. Otherwise it is rejected. Deterministic classified results use calibrated non-zero values.

**Rationale**: A numeric zero without documented semantics cannot distinguish a strong negative assessment from missing data.

## Decision 6: Make equivalence discovery global and conservative

**Decision**: Candidate discovery compares all current source catalogs using normalized semantic text plus deterministic similarity signals. The committed equivalence file records candidate IDs, strength, rationale, method/version, and review state. Consolidation preserves each source row and lineage; non-direct groups never imply equivalence without rationale.

**Rationale**: Source-specific matching misses duplicates across frameworks, while aggressive automatic merging would destroy traceability.

## Decision 7: Release and upgrade by content identity

**Decision**: Build into a fresh SQLite database from committed contracts and pinned classifications, validate V1-V4, record normalized content hashes and input hashes, then package the candidate. Installed upgrades execute in one transaction: migrate schema, resolve aliases, replace reference catalog rows, restore profile references/state, validate FKs/integrity, and commit.

**Rationale**: File hashes can vary from SQLite page layout; a canonical content hash proves logical reproducibility. Transactional replacement protects offline profile data.

## Decision 8: Fix CI dependency installation explicitly

**Decision**: CI installs `requirements-curation.txt` before Python tests and release construction.

**Rationale**: The existing workflow invokes modules that import PyYAML/openpyxl without installing pinned dependencies, producing infrastructure failures unrelated to catalog correctness.

