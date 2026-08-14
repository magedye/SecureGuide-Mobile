# Research: Semantic Source Closure

## Decision: Use a pinned all-corpus reconciliation ledger

**Rationale**: The existing curation loader only consumes 761 curated and 706 legacy records. The remaining raw records receive one generic `DEFERRED` disposition because no input reaches the projection. A versioned ledger binds each raw ID to source hash, outcome, semantic evidence, target, confidence, and record-specific rationale while remaining deterministic and reviewable.

**Alternatives considered**:

- Generate canonicals directly from all raw records: rejected because it would duplicate concepts and replace provenance closure with volume.
- Keep a generic deferred fallback: rejected because it is syntactic totality rather than semantic reconciliation.
- Store decisions only in a mutable candidate database: rejected because reproducibility and source/input binding would be lost.

## Decision: Reconcile against existing canonicals before canonical creation

**Rationale**: Existing canonicals already have stable IDs, aliases, and profile-compatible references. For each source record, deterministic candidate discovery and semantic comparison select support, duplicate, crosswalk, relation, split, rejection, or genuine new canonical creation. Similarity remains a candidate signal, never automatic merge authorization.

**Alternatives considered**:

- One canonical per raw record: rejected because it inflates duplicates and ignores global equivalence rules.
- Crosswalk every unmatched record: rejected because it conceals real support or genuine new concepts.

## Decision: Separate semantic corrections from source-disposition decisions

**Rationale**: A canonical semantic correction is an auditable change to type, level, and SDT assignment. It must not be inferred as a side effect of a source row. A distinct pinned correction set permits regression fixtures and a clear before/after audit, especially for NIST CSF outcome statements.

**Alternatives considered**:

- Source-wide bulk conversion: rejected because type is determined per statement, not by source family.
- Keep semantic updates only as hand-edited database content: rejected because clean rebuild cannot reproduce them.

## Decision: Add normalized reconciliation links and deferred reason codes

**Rationale**: Existing final lineage represents support and split relationships. `CROSSWALK_ONLY`, `RELATION_ONLY`, and `DUPLICATE` need explicit target references and strength without pretending they are lineage. A normalized link table and controlled deferred reason code enable foreign-key validation, workbook representation, and category reporting.

**Alternatives considered**:

- Encode all targets in a rationale string: rejected because it is not queryable, constraint-validatable, or safely round-trippable.
- Add JSON arrays to `security_artifacts`: rejected by USACM normalized-storage rules.

## Decision: Treat unknown confidence separately from numeric zero

**Rationale**: Legacy `0.0` represents an unscored bulk default. The ledger must represent unknown/unscored explicitly while retaining legitimate numeric zero where evidence warrants it. Low confidence remains visible and review-routed but does not block Minimum Valid admission.

## Decision: Qualify only isolated curated candidates before asset replacement

**Rationale**: `--mode curated` ingests all pinned sources and applies curation. The release mode consumes an already-approved baseline and cannot prove full reconciliation. Candidate A/B, workbook no-op, upgrade preservation, and platform gates bind evidence to an exact SHA before any asset replacement.

## Decision: Preserve former-name compatibility history and neutralize active surfaces

**Rationale**: Aliases and immutable migrations can legally and technically require historical tokens. Active mapping rationale and current reports are mutable current surfaces and must use neutral wording. Validation differentiates the two scopes.
