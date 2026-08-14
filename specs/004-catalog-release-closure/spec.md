# Feature Specification: Catalog Release Closure

**Feature Branch**: `agent/complete-secureguide-mobile`

**Created**: 2026-08-14

**Status**: Approved for implementation

**Input**: Owner-approved completion contract for semantic catalog correction, neutral terminology, governed bulk curation, deterministic release, and safe installed-catalog upgrades.

## User Scenarios & Testing

### User Story 1 - Trust the Minimum-Valid Catalog (Priority: P1)

As a catalog owner, I can rely on every released control being independently classified from its semantics, structurally valid under one versioned minimum contract, and traceable to preserved source evidence without confusing human review or optional enrichment with catalog eligibility.

**Why this priority**: Every curation, release, and upgrade action depends on a semantically defensible catalog boundary.

**Independent Test**: Evaluate representative requirements, controls, configurations, threats, procedures, ambiguous records, and low-confidence records; verify distinct minimum, strict-conformance, review, disposition, and lineage outcomes.

**Acceptance Scenarios**:

1. **Given** a structurally complete low-confidence record with accountable uncertainty, **when** minimum validation runs, **then** it can be minimum-valid without a false human-review or strict-conformance claim.
2. **Given** an attacker behavior or framework outcome, **when** classification runs, **then** its type and level are derived from its semantics rather than its source family or the word “control”.
3. **Given** a record with no defensible classification, **when** curation runs, **then** the raw record remains preserved with an explicit deferred disposition and rationale.
4. **Given** the complete corpus, **when** closure validation runs, **then** every raw record has one disposition and every canonical has final source lineage.

---

### User Story 2 - Use Neutral SecureGuide Identity Safely (Priority: P1)

As a product owner, I see only SecureGuide-neutral terminology in active product, data, documentation, and curation surfaces while existing installations and historical references remain upgrade-safe.

**Why this priority**: The former product name is obsolete, but careless renaming could break stable identities and operational records.

**Independent Test**: Scan all active surfaces for the obsolete token, upgrade a populated prior installation, and verify aliases or compatibility history resolve without broken profile, template, evidence, mapping, or relationship references.

**Acceptance Scenarios**:

1. **Given** a clean current build, **when** active code, schema interfaces, manifests, exports, documentation, and user-facing data are inspected, **then** the obsolete name is absent.
2. **Given** immutable historical migration text that must retain the token, **when** the active schema is inspected, **then** the token is isolated as documented compatibility history and is not exposed through current interfaces.
3. **Given** an installed database with legacy stable identifiers, **when** catalog upgrade runs, **then** identifiers and foreign-key references migrate transactionally or resolve through an explicit alias without operational data loss.

---

### User Story 3 - Curate the Complete Catalog Through a Governed Workbook (Priority: P1)

As a curator, I can export all controls or a supported filtered scope, edit all normalized catalog details and raw dispositions, validate them, review a deterministic plan, and apply only non-conflicting changes transactionally.

**Why this priority**: The workbook is the primary human bulk-curation interface and must be complete, reproducible, and fail closed.

**Independent Test**: Complete an export-edit-validate-plan-apply cycle on a representative fixture and the full catalog; prove omission, stale baselines, stale rows, formulas, invalid values, dangling references, and unsafe delete behavior are rejected.

**Acceptance Scenarios**:

1. **Given** an unchanged exported workbook, **when** it is validated and planned, **then** it produces no mutations and no conflicts.
2. **Given** a valid `UPSERT` or `DEPRECATE`, **when** a reviewed plan is applied, **then** the change and its audit evidence are committed atomically.
3. **Given** a changed database baseline or row hash, **when** planning or apply runs, **then** the row becomes `CONFLICT` and is not overwritten automatically.
4. **Given** a filtered export, **when** it is round-tripped, **then** omission outside and inside its scope never becomes a physical deletion and supported details remain lossless.
5. **Given** the full workbook, **when** raw disposition data is inspected, **then** every raw record, disposition, rationale, and final lineage reference needed for closure is represented.

---

### User Story 4 - Reconcile Globally and Reproducibly (Priority: P1)

As a catalog curator, I can reproduce classifications and duplicate candidates from pinned inputs, distinguish candidate detection from merge decisions, and retain meaningful rationale for separate, merged, split, and supporting records.

**Why this priority**: Source-specific defaults and local optional files make results irreproducible and hide semantic conflicts.

**Independent Test**: Run a clean-checkout build without optional local result files, compare pinned input hashes, inspect global duplicate candidates across sources, and verify materially different records are not silently merged.

**Acceptance Scenarios**:

1. **Given** optional local classification outputs are absent, **when** the default curation path runs, **then** it consumes the pinned authoritative input and produces the same corpus.
2. **Given** similar records from different sources, **when** candidate discovery runs, **then** all sources participate and similarity alone never authorizes a merge.
3. **Given** generic duplicate titles that describe distinct atomic requirements, **when** reconciliation completes, **then** titles become distinct and source alternatives remain traceable.
4. **Given** known and unknown source metadata, **when** provenance is materialized, **then** known facts are pinned and unknown facts remain explicit without fabrication.

---

### User Story 5 - Build and Upgrade a Real Release Candidate (Priority: P2)

As a release engineer, I can reproduce one rights-safe real-content catalog candidate and transactionally upgrade existing installations without resetting profile or operational state.

**Why this priority**: A valid catalog is not releasable until it is reproducible, installable, retry-safe, and preserves user data.

**Independent Test**: Build twice from identical pinned inputs, compare candidate and manifest hashes, then exercise clean install, populated upgrade, failed upgrade and retry, and repeated unchanged upgrade.

**Acceptance Scenarios**:

1. **Given** identical pinned inputs, **when** two clean release builds run, **then** database and canonical manifest hashes match.
2. **Given** restricted or unknown redistribution rights, **when** the mobile candidate is built, **then** restricted raw text is absent while authored canonicals and permitted provenance remain.
3. **Given** profiles, selections, assessments, evidence, exceptions, templates, and tasks, **when** catalog upgrade runs, **then** all operational data and valid references are preserved.
4. **Given** an interrupted upgrade, **when** the transaction fails and is retried, **then** the first attempt rolls back and the retry is idempotent.

---

### User Story 6 - Qualify the Exact Candidate (Priority: P2)

As a release reviewer, I receive concise evidence bound to the exact candidate revision and hashes, including closure, integrity, upgrade preservation, deterministic rebuild, performance, and available mobile-platform gates.

**Why this priority**: Release claims must describe what was actually tested and must fail closed where mandatory evidence is missing.

**Independent Test**: Run the complete validation matrix against the exact candidate and verify every claim records its input identity, outcome, and any platform limitation.

**Acceptance Scenarios**:

1. **Given** a candidate with any closure, integrity, semantic fallback, or upgrade-preservation failure, **when** release qualification runs, **then** release status fails closed.
2. **Given** optional platform capability is unavailable, **when** unrelated gates pass, **then** the limitation is recorded without blocking unrelated implementation work.
3. **Given** existing performance budgets, **when** measurements run, **then** established thresholds are enforced and no new arbitrary threshold is invented.

### Edge Cases

- One raw record supports multiple canonicals after a split, or multiple raw records support one canonical.
- A record contributes only a crosswalk or relationship and does not create a canonical.
- A genuinely scored confidence of zero must remain distinguishable from unscored classification.
- A source file contains the obsolete token as immutable evidence while its active catalog identity is neutral.
- A workbook scope is empty, contains duplicate identities, or includes relationships whose opposite endpoint lies outside the filter.
- A canonical is deprecated while profile selections, historical assessments, mappings, templates, and lineage still reference it.
- A duplicate candidate has similar text but differs in type, level, scope, obligation, atomicity, or verification semantics.
- The release population changes from its performance baseline; evidence must disclose the population rather than inflate it.

## Requirements

### Functional Requirements

- **FR-001**: The catalog MUST preserve separate `RAW`, `MINIMUM_VALID`, and `ENRICHED` quality states and separate human-review and strict-conformance outcomes.
- **FR-002**: One versioned machine-readable minimum contract MUST be the implementation source for core, type-specific, and enrichment-only validation.
- **FR-003**: Every minimum-valid canonical MUST satisfy all contract-defined core and applicable type-specific fields and MUST have at least one valid final raw-source lineage record.
- **FR-004**: Missing human review, confidence at or below 0.70, Arabic, or optional enrichment MUST NOT alone block minimum-valid status; uncertainty and review requirements MUST remain explicit.
- **FR-005**: Classification MUST evaluate every item independently from its semantics and MUST NOT globally default type, abstraction level, or security domain from its source family.
- **FR-006**: Threat and adversary behavior, framework outcomes, requirements, controls, configurations, and procedures MUST retain defensible distinct artifact types.
- **FR-007**: Indefensible classifications MUST preserve the raw record, receive an explicit deferred disposition and rationale, and MUST NOT be silently published.
- **FR-008**: Genuinely scored zero confidence MUST be distinguishable from an unscored or unknown classification.
- **FR-009**: Every raw source record MUST have exactly one disposition from the approved vocabulary, with rationale wherever the disposition does not directly support a canonical.
- **FR-010**: Final source lineage MUST support many-to-many raw/canonical links, lineage role, mapping strength, deterministic source hash, decision reference, rationale, and accountable audit metadata where available.
- **FR-011**: Every disposition claiming canonical support MUST have matching final lineage, and closure MUST reject dangling or inconsistent references.
- **FR-012**: Provenance MUST preserve the strongest evidenced original source identity, document, version or explicit unknown reason, publication date when known, section/reference, content hash, pinned source/manifest hash, and retrieval/import evidence when available.
- **FR-013**: Source rights MUST be versioned; public availability MUST NOT be treated as redistribution permission, and restricted or unknown raw text MUST be excluded from mobile releases.
- **FR-014**: Active product, data-interface, script, export, generated, test, fixture, documentation, and new-identifier surfaces MUST use one neutral SecureGuide terminology scheme instead of the obsolete former-product token.
- **FR-015**: Historical compatibility that cannot safely be renamed MUST be isolated, documented, and hidden from current interfaces; stable identifiers MUST migrate transactionally or resolve through explicit aliases.
- **FR-016**: Identifier migration MUST preserve all valid foreign-key, profile, assessment, evidence, exception, template, relationship, mapping, and audit references.
- **FR-017**: The authoritative catalog store MUST remain the system of record for the governed workbook workflow `export → edit → validate → plan → transactional apply`.
- **FR-018**: The workbook MUST expose manifest, artifacts, source lineage, mappings, relationships, tags, type-specific fields, reference lists, validation errors, and raw dispositions, plus every other supported normalized catalog-detail collection.
- **FR-019**: Workbook manifests MUST include export identity/time, baseline hash, schema version, `MINIMUM_VALID` quality profile, minimum-contract hash, source-rights/manifest hashes, and raw, disposition, canonical, and lineage counts.
- **FR-020**: Workbook actions MUST be limited to `NO_CHANGE`, `UPSERT`, and `DEPRECATE`; omission MUST mean `NO_CHANGE`, and physical deletion MUST NOT be a normal bulk action.
- **FR-021**: Every editable workbook row MUST carry immutable identity and baseline version/hash evidence; stale database or row state MUST produce a non-applicable conflict.
- **FR-022**: Workbook validation and apply MUST reject formulas, invalid controlled values, broken references, minimum-contract violations, unauthorized conflict overrides, and partial transactions.
- **FR-023**: Full and supported filtered exports MUST remain lossless for their declared scope and MUST support filtering by domain, artifact type, source, confidence/quality, and review state.
- **FR-024**: The default classification and reconciliation path MUST consume a pinned committed source of truth; rebuilding it from optional results MUST require an explicit operation.
- **FR-025**: Duplicate/equivalence candidate discovery MUST operate globally across relevant sources before domain closure and MUST remain distinct from merge decisions.
- **FR-026**: A merge decision MUST consider type, abstraction, domain, atomicity, obligation/scope, verification semantics, and provenance; text similarity alone MUST NOT merge records.
- **FR-027**: Known exact and near duplicates and ambiguous generic titles MUST be reconciled or explicitly retained separately with meaningful rationale and preserved alternatives.
- **FR-028**: Semantic text cleanup MUST correct only defects that affect canonical integrity and MUST NOT expand optional enrichment into a release blocker.
- **FR-029**: Release construction MUST start clean, apply authoritative migrations, load pinned inputs, materialize dispositions/classifications/consolidation/lineage, enforce closure and rights gates, and emit a deterministic database and versioned manifest with hashes.
- **FR-030**: Curation MUST NOT modify the shipped catalog asset directly; only a verified candidate may replace it.
- **FR-031**: Installed-catalog upgrade MUST be transactional, retry-safe, idempotent, and preserve catalog/profile separation and every operational record named in FR-016.
- **FR-032**: Upgrade qualification MUST cover clean install, populated profile state, assessments and evidence, failed upgrade and retry, and unchanged repeated upgrade.
- **FR-033**: Closure qualification MUST prove complete dispositions and lineage, zero missing minimum/type fields, valid SDT parentage, zero broken foreign keys or dangling graph references, zero silent classification fallbacks, and deterministic rebuild.
- **FR-034**: Exact-candidate release qualification MUST run applicable governance, integrity, deterministic, upgrade, performance, Python, Flutter, Android, and available iOS gates without inventing thresholds or unsupported claims.
- **FR-035**: Active authority paths MUST be repository-relative and MUST NOT depend on the former `New folder` location.

### Key Entities

- **Minimum Contract**: Versioned, machine-readable definition of minimum and type-conditional catalog eligibility.
- **Canonical Control**: SecureGuide-authored normalized catalog item of any USACM artifact type.
- **Raw Source Record**: Preserved source intake item with content and provenance hashes.
- **Raw Disposition**: Exactly one accountable outcome for a raw record.
- **Final Source Lineage**: Many-to-many evidence link from preserved raw material to canonical controls.
- **Source Identity and Rights Record**: Neutral current source identity, strongest evidenced provenance, and redistribution decision.
- **Legacy Identifier Alias**: Explicit compatibility mapping from historical identifiers to current stable identities.
- **Curation Workbook**: Versioned bulk-edit projection with controlled values and stale-edit evidence.
- **Curation Plan and Audit**: Deterministic actions, conflicts, resolutions, and transactional result.
- **Reconciliation Decision**: Evidence-backed decision to merge, split, support, relate, defer, reject, or retain separately.
- **Release Candidate and Manifest**: Deterministic real-content database plus bound schema, source, contract, rights, count, validation, and content hashes.
- **Catalog Upgrade**: Versioned, idempotent transformation of installed reference content that preserves operational state.

## Success Criteria

### Measurable Outcomes

- **SC-001**: 100 percent of raw records have exactly one valid disposition.
- **SC-002**: 100 percent of minimum-valid canonicals have at least one valid final lineage record, and every supporting/split disposition has matching lineage.
- **SC-003**: Minimum validation reports zero missing core or applicable type-specific fields while strict conformance and review remain separately measurable.
- **SC-004**: Classification distribution contains zero records created by a silent source-family fallback, and every unclassified record is explicitly deferred.
- **SC-005**: Active-surface scanning finds zero obsolete-name occurrences outside a documented immutable compatibility allowlist.
- **SC-006**: Legacy identifier migration produces zero broken profile, evidence, exception, template, mapping, relationship, or audit references.
- **SC-007**: Complete and filtered workbook fixtures round-trip with zero mutation by omission, 100 percent stale-edit rejection, and auditable atomic application of valid actions.
- **SC-008**: Workbook manifest counts and hashes reconcile with the declared export scope, including all raw dispositions and normalized catalog details.
- **SC-009**: Global reconciliation records an explicit decision for every detected duplicate/equivalence candidate and performs zero similarity-only merges.
- **SC-010**: A clean checkout reproduces the pinned classification corpus without optional local files.
- **SC-011**: Two release builds from identical pinned inputs produce identical database bytes and canonical manifest hashes.
- **SC-012**: The mobile candidate contains zero restricted or unknown-permission raw payload text.
- **SC-013**: Clean install, populated upgrade, failed-upgrade retry, and repeated-upgrade tests preserve 100 percent of seeded operational records.
- **SC-014**: Exact-candidate integrity reports `ok`, zero foreign-key violations, zero dangling references, and complete closure.
- **SC-015**: Performance evidence reports catalog population, baseline identity, query/search latency, startup impact, database size, memory, migration duration, and integrity duration against existing thresholds.
- **SC-016**: Applicable Python and mobile gates pass, and unavailable optional platform qualification is reported explicitly without a false pass claim.

## Assumptions

- The current branch contains newer verified catalog work than `origin/main` and remains the implementation branch.
- Existing closure schema, minimum contract, curation pipeline, workbook implementation, release builder, and installed-upgrade path are extended rather than replaced.
- Immutable migration history may retain the obsolete token only when rewriting it would break an already-applied upgrade contract; any exception is narrowly allowlisted and documented.
- Current mobile catalog content has not yet established immutable external canonical IDs that prevent a transactional neutral-ID migration; if evidence disproves this, explicit aliases become mandatory.
- Missing optional enrichment, Arabic, human review, or one deferred raw item does not globally block completion.
- Rights or source metadata that cannot be proven remains explicit and conservative rather than fabricated.
