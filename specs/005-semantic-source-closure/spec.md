# Feature Specification: Semantic Source Closure

**Feature Branch**: `agent/complete-secureguide-mobile`

**Created**: 2026-08-14

**Status**: Approved for implementation

**Input**: Owner-authorized semantic and source-coverage closure of the SecureGuide Minimum Valid Catalog.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reconcile Every Source Record (Priority: P1)

As a catalog curator, I can account for every preserved source record through a record-specific, evidence-backed disposition, so that catalog coverage reflects real reconciliation rather than a bulk placeholder state.

**Why this priority**: Source coverage and provenance are the basis for a defensible Minimum Valid catalog.

**Independent Test**: Rebuild a candidate from the complete pinned raw corpus and verify every source record has exactly one disposition, every remaining deferred record has a unique substantive rationale, and supporting records have matching final lineage.

**Acceptance Scenarios**:

1. **Given** a source record that substantively supports an existing canonical, **when** reconciliation runs, **then** the record is attached to that canonical with a meaningful lineage role and rationale.
2. **Given** a source record that contains several independent concepts, **when** reconciliation runs, **then** it is split or related without fabricating a single composite canonical.
3. **Given** a genuinely unresolved record, **when** reconciliation runs, **then** it remains deferred only with a record-specific ambiguity or evidence rationale.
4. **Given** the full corpus, **when** closure validation runs, **then** generic no-classifier-evidence deferral is rejected.

---

### User Story 2 - Trust Semantic Classifications (Priority: P1)

As a security architect, I can rely on every canonical being classified according to what the record itself is, with independently valid type, abstraction level, and SDT domain decisions.

**Why this priority**: Keyword-driven or source-family defaults can turn requirements, outcomes, and adversary behavior into incorrect control, process, or principle records.

**Independent Test**: Run regression fixtures for policy, plan, review/audit, outcome, process, adversary-technique, payment-card protection, and vulnerability-management cases, then audit the full NIST CSF population and selected outcome-heavy source families.

**Acceptance Scenarios**:

1. **Given** a requirement that mentions a policy or plan, **when** it is classified, **then** the mention alone cannot make it a policy or plan artifact.
2. **Given** a framework outcome statement, **when** it is classified, **then** its type is based on the statement's semantics rather than its source taxonomy or the word control.
3. **Given** a reclassified canonical, **when** validation runs, **then** its type-specific fields, level, domain, and sub-domain remain independently valid.
4. **Given** an adversary technique, **when** it is classified, **then** it remains distinguishable from a defensive control.

---

### User Story 3 - Preserve Source-Rich, Neutral Catalog Identity (Priority: P2)

As a catalog owner, I retain traceable original-source provenance and compatible historical identifiers while active catalog surfaces use only current SecureGuide-neutral terminology.

**Why this priority**: Better source coverage must not destroy lineage, installed-profile compatibility, or the active naming boundary.

**Independent Test**: Compare source, lineage, alias, and active terminology scans before and after reconciliation; validate a populated catalog upgrade without profile, assessment, evidence, exception, template, or workflow loss.

**Acceptance Scenarios**:

1. **Given** a canonical supported by several sources, **when** its lineage is inspected, **then** each attached source has an appropriate, non-generic justification where the relationship is non-trivial.
2. **Given** an active mapping or report, **when** it is generated, **then** it does not expose the obsolete former product name.
3. **Given** a historical alias or immutable migration requiring the former name, **when** compatibility is verified, **then** it remains available only as documented history and does not leak into active terminology.

---

### User Story 4 - Release a Reproducible Closed Candidate (Priority: P2)

As a release owner, I can qualify a deterministic catalog candidate and a governed workbook without changing the shipped asset until all applicable closure, integrity, round-trip, upgrade, and runtime checks pass.

**Why this priority**: Semantic improvements are useful only if the candidate is reproducible, upgrade-safe, and auditable.

**Independent Test**: Produce two clean candidates from pinned inputs, compare their logical and file hashes, complete a workbook no-op round trip, validate upgrade preservation, and run the available Python, Flutter, Android, and iOS gates.

**Acceptance Scenarios**:

1. **Given** the same pinned inputs, **when** two candidate builds run, **then** their documented release hashes and logical catalog content agree.
2. **Given** an unchanged complete workbook, **when** it is validated, planned, applied to an isolated candidate, and re-exported, **then** no governed catalog data changes.
3. **Given** a candidate that fails any applicable closure or integrity gate, **when** release qualification runs, **then** the shipped catalog asset is unchanged and the failure is reported.

### Edge Cases

- A raw record is related to a canonical but has materially different obligation, atomicity, or verification semantics.
- A legacy numeric zero confidence means unscored rather than genuinely zero confidence.
- A rights-restricted raw text may inform internal classification but cannot ship in a release payload.
- A source record lacks enough trustworthy metadata for a defensible relationship.
- A canonical consolidation would change a stable identifier referenced by an installed profile.
- A source-specific taxonomy suggests a domain that conflicts with the record's actual semantic focus.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST reconcile every record in the pinned authoritative raw corpus through one allowed disposition and preserve all raw records.
- **FR-002**: The system MUST reject generic deferred rationales that merely state classification evidence was unavailable and require a record-specific rationale for every remaining deferred record.
- **FR-003**: The system MUST prefer attaching source records to a correct existing canonical before creating a new canonical and MUST preserve a complete source lineage for every canonical.
- **FR-004**: The system MUST classify and validate type, abstraction level, primary domain, and sub-domain as distinct decisions according to USACM v2.2.1 and SDT v2.2.1.
- **FR-005**: The system MUST add regression coverage for semantic false-positive patterns, including mentions of policy, plan, review, audit, process, defensive controls, and adversary techniques.
- **FR-006**: The system MUST audit NIST CSF and other outcome-heavy source-derived canonicals individually rather than apply a source-wide type conversion.
- **FR-007**: The system MUST retain stable canonical IDs, aliases, profiles, assessment data, evidence, exceptions, templates, and workflow data unless a validated compatibility migration explicitly changes them.
- **FR-008**: The system MUST preserve source-rights fail-closed release behavior while allowing lawful internal source evidence to support reconciliation.
- **FR-009**: The system MUST replace obsolete former-product terminology on active current surfaces without removing documented immutable compatibility history.
- **FR-010**: The system MUST distinguish unscored confidence from an actual zero confidence value using the smallest compatible explicit representation.
- **FR-011**: The system MUST preserve the governed workbook export, validation, planning, and transactional apply contract for complete and filtered scopes.
- **FR-012**: The system MUST provide closure evidence for disposition, lineage, semantic classification, duplicates, active terminology, validation, deterministic rebuild, and applicable release qualification results.
- **FR-013**: The system MUST not replace the shipped catalog asset until the exact candidate passes all applicable semantic-closure and integrity gates.

### Key Entities *(include if feature involves data)*

- **Raw Source Record**: An immutable preserved record from a pinned source, with source identity, content metadata, disposition, and reconciliation rationale.
- **Canonical Artifact**: A normalized SecureGuide security artifact with one USACM type, one SDT domain pair, accountable classification, and at least one raw lineage source.
- **Raw Disposition**: The evidence-backed outcome that explains how a raw record supports, splits from, duplicates, crosswalks to, relates to, is rejected from, or remains deferred from canonical coverage.
- **Final Source Lineage**: The normalized connection between a canonical and a contributing raw source, including relationship role and rationale.
- **Closure Evidence**: A deterministic report binding counts, validations, release candidate hashes, and known remaining quality debt to the exact candidate.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of the authoritative raw corpus has exactly one allowed disposition, and 0 records use the previous generic no-classifier-evidence deferred rationale.
- **SC-002**: 100% of remaining deferred records have an individually recorded substantive category and rationale.
- **SC-003**: 100% of `SUPPORTS_CANONICAL` dispositions have matching final lineage, and 100% of canonicals retain at least one raw lineage record.
- **SC-004**: The candidate has 0 missing Minimum Valid fields, invalid controlled values, invalid SDT pairs, dangling governed references, silent type/domain fallbacks, or exact duplicate canonicals.
- **SC-005**: 100% of audited NIST CSF-derived canonicals are individually evaluated with regression evidence for required semantic edge cases.
- **SC-006**: Active current catalog surfaces contain 0 obsolete former-product naming occurrences, excluding explicitly documented immutable compatibility history.
- **SC-007**: Two clean candidate builds from the same pinned inputs produce matching documented logical content hashes, and the complete workbook no-op round trip reports 0 mutations and 0 validation errors.
- **SC-008**: The exact candidate passes all available project validators and applicable Python, Flutter, Android, and iOS qualification gates before it replaces the shipped asset.

## Assumptions

- The existing raw corpus, source manifests, rights records, and Minimum Valid policy remain the authoritative baseline unless verified evidence requires a forward-compatible correction.
- Low confidence and pending human review remain visible quality signals and do not alone prevent Minimum Valid entry.
- The existing draft pull request remains the implementation review surface because this work corrects the catalog closure it contains; changes will remain atomic and evidence-bound.
- Source text with unknown or restricted redistribution rights remains internal evidence and is not included in shipped release payloads.
