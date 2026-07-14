# Security Artifact Database Policy (SADP) v1.0
## Self-Contained Master Governance Document for Security Artifact Databases

| Field | Value |
|---|---|
| Document Title | Security Artifact Database Policy (SADP) v1.0 |
| Version | 1.0 |
| Date | 2026-07-12 |
| Purpose | Provide the definitive set of rules and constraints that govern the creation, architecture, and maintenance of the core security artifacts database. |
| Target Audience | Database Architects, Backend Developers, AI Agents, Data Engineers, UI/UX Designers. |
| References | USACM v2.2.1, SDT v2.2.1, ADR 0002, ADR 0003 |
| Status | **ADOPTED** — this is the governing document for the SecureGuide catalog database; it supersedes conflicting guidance in AUTHORING_POLICY / PROMOTION_POLICY where applicable. Conformance mapping: `SADP_CONFORMANCE.md`. |

## 1. Executive Summary
This policy dictates the strict architectural requirements for the application's core security artifact database (whether represented in SQLite, JSON, or any other persistence layer). It guarantees that the database conforms identically to the principles agreed upon in USACM and SDT, ensuring data integrity, predictable filtering, and clear separation of concerns.

## 2. Core Architectural Mandates

### 2.1 Separation of Intrinsic Data vs. User State
The core catalog database must **never** store user context, user interaction states, or dynamically calculated properties.
- **Allowed (Intrinsic):** Baseline Priority, Obligation Source, Threat, Domain, Abstraction Level.
- **Prohibited (State):** User Verification Status, Effective Priority, Recommended Flags, Local Review Required Flags.
- **Implementation:** User states must be joined at runtime (in memory or via an external user-state database) and must not corrupt the source-of-truth catalog.

### 2.2 Strict Adherence to Mandatory Classifications
Every artifact must possess a value for all classifications defined in USACM v2.2.1 and SDT v2.2.1. Null values or missing fields are strictly forbidden for classification columns to prevent broken UI logic.

### 2.3 Universal Fallbacks Rule
Whenever a specific classification value cannot be determined or does not fit perfectly, the system must utilize one of three mandatory fallback values instead of `NULL` or leaving it empty:
1. `*-NA` (لا ينطبق): The classification dimension is irrelevant or Not Applicable to the artifact.
2. `*-UNKNOWN` (غير محسوم): The dimension is relevant, but the correct value is currently unknown or undecided.
3. `*-MULTI` (قيم متعددة): The artifact inherently spans multiple values in a way that forcing a single choice causes data loss.

### 2.3.1 Storage and publication disposition

The presence of a fallback in a lookup table does **not** by itself authorize that
value in an approved catalog record. `classification_fallback_policy` is the
machine-readable authority for each dimension:

- `type`, `primary_domain`, and `sub_domain` never accept fallbacks. They require
  one real USACM/SDT value; uncertainty is recorded through the AI review fields.
- Type-conditional non-applicability is structural: for example, a non-control
  stores `NULL` for `control_nature` rather than the literal `NAT-NA`.
- `*-UNKNOWN` is a review signal and must not be promoted. It requires human
  review and an approved real value before publication.
- `*-MULTI` must not bypass single-value classification. Where multiplicity is
  legitimate, use normalized child rows; otherwise split or review the artifact.
- Native values that already express a valid state remain valid, including
  `TST-NA`, `EFF-UNKNOWN`, `EXC-NOT-APPLICABLE`, and `THR-NA` in their governed
  contexts.

### 2.4 Prohibition of Unstructured Tags
The database shall not implement a free-form "Tags" array or column. All secondary context mapping must be done through formal, pre-approved primary classifications.
The concept of "Tags" has been officially replaced by the **Threat Classification (`THR-*`)**, which is a mandatory, normalized classification dimension.

### 2.5 Configurable UI Visibility
While the database enforces that all 18+ classifications are populated for data integrity, the presentation layer (UI) must decouple from this rigidity.
A configuration layer must be provided allowing administrators or system logic to **Show or Hide** any specific classification dimension. The database architecture is not required to change when a classification is hidden from the user.

### 2.6 Change Control
No new classification dimension, and no new enumeration value within an existing dimension, may be added to the database schema or data pipeline without formal study and explicit approval from the product owner.

## 3. Mandatory Database Columns (SQLite Mapping)
Any SQL table representing a security artifact (e.g., `artifacts`) must include, at a minimum, the following constraint columns mapped to `TEXT` (representing the Enum codes):

- `primary_domain` (e.g., SD-01)
- `sub_domain` (e.g., SD-01.01)
- `artifact_type` (ART-*)
- `abstraction_level` (ABS-*)
- `obligation_source` (SRC-*)
- `obligation_level` (OBL-*)
- `exception_status` (EXC-*)
- `granularity_level` (GRN-*)
- `control_nature` (NAT-*)
- `control_function` (FUN-*)
- `testability` (TST-*)
- `implementation_status` (STS-*)
- `verification_status` (VER-*)
- `effectiveness` (EFF-*)
- `priority` (PRI-*)
- `relationship_type` (REL-*)
- `requirement_type` (RQT-*)
- `mapping_strength` (DIRECT/INDIRECT/etc.)
- `review_frequency` (DAILY/WEEKLY/etc.)

### 3.1 Handling Threat Multiplicity
If an artifact uses the `THR-MULTI` fallback or requires mapping to multiple specific threats (e.g., `THR-RANSOMWARE` and `THR-PHISHING`), these must be stored in a normalized child table (e.g., `artifact_threats`) rather than a JSON array column, conforming to the SQLite-first normalization rule.
