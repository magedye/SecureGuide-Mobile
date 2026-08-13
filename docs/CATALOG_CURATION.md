# SecureGuide Catalog Curation Contract

## 1. Purpose and scope

This document defines the governed workflow for turning preserved source material into the SecureGuide Master Catalog. It covers minimum catalog admission, strict USACM conformance, human review, source rights, raw-record closure, final source lineage, Excel round-trip curation, and release-candidate handling.

The SQLite database is the system of record. Spreadsheets, YAML, JSON, and generated reports are governed inputs or interchange artifacts; none of them replaces the database.

All repository paths in documentation, configuration, manifests, commands, and audit evidence are project-relative. Commands in this document run from the repository root. Examples include:

- `config/catalog_minimum_fields.yaml`
- `specs/002-catalog-curation/`
- `dist/catalog-curation-working.db`
- `mobile/assets/catalog.db`

Do not encode a workstation path or the former `New folder` path in governed project data.

## 2. Terminology

In Arabic product language, **الضوابط** is the generic term for every Master Catalog artifact, regardless of its USACM `type`. This convention is a user-facing vocabulary decision and does not alter the data model.

- **الضوابط**: all catalog artifacts collectively.
- **ضابط من نوع `ART-CTR`**: an artifact whose specific USACM type is Control.
- **Canonical control / canonical**: a normalized SecureGuide-authored catalog artifact of any valid `ART-*` type.
- **Raw record**: preserved source intake before canonical curation.

Database values remain the exact USACM v2.2.1 controlled values. The generic Arabic term must never cause all records to be classified as `ART-CTR`.

## 3. Authority and fail-closed interpretation

Apply authority in this order:

1. Explicit catalog owner decisions.
2. Applicable `AGENTS.md` and repository governance.
3. USACM v2.2.1.
4. SDT v2.2.1.
5. Approved catalog, consolidation, promotion, and authoring policies.
6. Existing implementation and tests.

When authorities conflict, record the conflict and stop the affected decision. Do not silently select a more permissive rule, weaken a controlled value, fabricate provenance, or default an uncertain artifact to `ART-CTR`.

## 4. Independent state dimensions

Catalog lifecycle, publication, classification quality, human review, localized-content review, and profile operation are different facts and must remain separate.

| Dimension | Meaning | Governing representation |
|---|---|---|
| Catalog maturity | Progress from intake to usable and optionally enriched content | Derived as `RAW -> MINIMUM_VALID -> ENRICHED`; do not add a duplicate status column solely for this derivation |
| Minimum admission | Whether the project minimum contract passes | Derived result `MINIMUM_CATALOG_VALIDATION` |
| Strict conformance | Whether all applicable USACM v2.2.1 rules pass | Independent result `STRICT_USACM_CONFORMANCE` |
| Publication | Editorial/catalog publication state | Existing `publication_status` |
| AI classification review | Accountability for machine-assisted classification | Existing `classification_confidence`, `classification_rationale`, `ai_review_status`, and `requires_human_review` |
| Localized-content review | Review of a locale's authored content | Existing localization review fields |
| Operational state | Implementation, verification, effectiveness, exceptions, ownership, evidence, and assessment in an organization | `profile_artifacts` and other `profile_*` tables only |

`MINIMUM_VALID` is a project-defined catalog acceptance profile. It is not a claim that a person reviewed the artifact, that the content is fully enriched, or that every strict USACM rule passes.

## 5. Minimum catalog validation

### 5.1 Single source of truth

`config/catalog_minimum_fields.yaml` is the sole versioned, machine-readable minimum-entry contract. Validators, promotion, curation, workbook validation, and release qualification must load it instead of maintaining independent field lists.

This document explains the contract but does not override it. A contract change requires a version change and corresponding validation tests.

### 5.2 Core requirements

Every active, catalog-ready canonical must contain:

| Category | Required fields or relation |
|---|---|
| Stable identity and kind | `id`, `type` |
| Minimum English content | `title_en`, `definition_short_en` |
| Classification | `primary_domain`, `sub_domain`, `abstraction_level` |
| Source identity | `source`, `source_type`, `source_document` |
| Normative shape | `obligation_level`, `granularity_level` |
| Classification accountability | `classification_confidence`, `classification_rationale` |
| Catalog state | `publication_status`, `is_active` |
| Evidence-bearing provenance | At least one valid row in final `artifact_source_lineage` |

The artifact must also satisfy controlled values, the single SDT domain/sub-domain pairing, foreign keys, and all applicable structural constraints.

Release-eligible canonicals have `publication_status` equal to `APPROVED` or `PUBLISHED` and `is_active = 1`. Validity is derived at validation time; it is not stored by overloading publication or review fields.

### 5.3 Type-specific and conditional requirements

| Type or condition | Minimum requirement |
|---|---|
| `ART-REQ` | `requirement_type` |
| `ART-CTR`, `ART-CTE` | `control_nature`, `control_function`, `testability` |
| `ART-AST` | `asset_type`, `asset_criticality` |
| `ART-RSK` | At least one owned remediation action, or an incoming `REL-MIT` relationship from the mitigating artifact to the risk |
| `ART-EXC` | `exception_approval_date`, `exception_expiry_date` |
| Published `ART-POL`, `ART-STD`, `ART-PRC` | `effective_date` |

The risk remediation requirement is relational and must not be satisfied by unsupported free text.

### 5.4 Enrichment-only content

Arabic content, full definitions, objectives, implementation guidance, verification notes, evidence examples, extended mappings, tags, relationships other than a required risk remediation, platforms, threats, stakeholders, cost, and maturity enrich a canonical but do not independently block minimum entry.

An absent enrichment field must not be misreported as a structural failure. Conversely, labeling an artifact `ENRICHED` must be supported by the applicable enrichment evidence and must not be inferred merely because minimum validation passed.

## 6. Strict USACM conformance and human review

Every evaluated canonical produces two distinguishable results:

- `MINIMUM_CATALOG_VALIDATION`: applies the project contract in `config/catalog_minimum_fields.yaml`.
- `STRICT_USACM_CONFORMANCE`: applies all relevant USACM v2.2.1 validation rules without modification.

A strict-conformance failure does not automatically fail minimum validation. It blocks minimum entry only when the same finding also violates the minimum structural/type contract or another higher-authority repository policy. Reports must preserve both outcomes and their findings; they must never alias one result to the other.

Human review is a third, independent dimension:

- `NOT_REVIEWED` is valid for a structurally valid `MINIMUM_VALID` canonical.
- Human review is claimed only when reviewer identity, decision, and time evidence exist.
- Low confidence is allowed when the canonical is structurally valid and the uncertainty is explicit.
- When `classification_confidence <= 0.70`, set `requires_human_review = 1` and `ai_review_status = AIR-HUMAN-REVIEW`.
- If no artifact type is defensible from evidence, do not invent one. Preserve the raw record with disposition `DEFERRED` and a rationale.

The strict validator remains authoritative for strict claims. Minimum admission must never be implemented by weakening USACM rules.

## 7. Source provenance and rights

### 7.1 Reproducible provenance

Every raw record must be connected to sufficient reproducible provenance:

- `source_catalog_id` and `source_document`;
- `source_version`, or explicit `UNKNOWN` plus a non-empty reason;
- `source_section` or location when available;
- a content SHA-256 hash;
- the pinned source or import-manifest SHA-256 hash;
- source file or retrieval provenance when relevant;
- importer identity/version and import counts in the source manifest.

Unavailable metadata is recorded as unknown with its reason. It is never guessed from publisher names, filenames, neighboring rows, or framework familiarity.

### 7.2 Versioned source-rights decisions

Source-rights decisions are immutable and versioned per source and source version. A rights record identifies the redistribution state (`ALLOWED`, `RESTRICTED`, or `UNKNOWN`), whether raw text may ship, supporting evidence where available, the decision reason, decision actor/time, superseded record, and current version.

Rights handling is fail-closed:

- Raw text may ship only when the current versioned decision explicitly states `ALLOWED` and `ship_raw_text = 1`.
- `UNKNOWN` or `RESTRICTED` means `ship_raw_text = 0`.
- Working databases retain source records and their full evidence according to project custody rules.
- A mobile release excludes protected source-derived text payloads while retaining raw identity, permitted references, hashes, manifests, disposition, final lineage, and SecureGuide-authored canonical content.
- Rights scrubbing never deletes the raw record or breaks lineage.

The release builder must use an explicit allow decision. It must not infer redistribution permission from public accessibility.

## 8. Raw dispositions and closure

Every raw record receives exactly one final disposition:

| Disposition | Meaning | Required linkage |
|---|---|---|
| `SUPPORTS_CANONICAL` | The raw record materially supports one canonical | Matching final lineage row |
| `SPLIT` | The raw record contributes to more than one canonical | Matching lineage row for every supported canonical |
| `DUPLICATE` | The raw record duplicates an existing raw record or represented source concept | Existing related raw record and rationale; record remains preserved |
| `CROSSWALK_ONLY` | The record contributes only a framework mapping | Resolvable mapping evidence; no fabricated canonical contribution |
| `RELATION_ONLY` | The record contributes only an artifact relationship | Resolvable relationship evidence |
| `REJECTED` | The record is intentionally excluded from canonical contribution | Non-empty rationale; raw record remains preserved |
| `DEFERRED` | Evidence is insufficient for a defensible decision | Non-empty uncertainty/blocker reason and review flag where applicable |

Each disposition records its rationale, decision method, confidence, review flag, actor/time, and decision batch. `DUPLICATE` identifies the related raw record. Disposition values are closed; adding a value requires an owner-approved contract change.

Closure succeeds only when:

1. Every raw record has exactly one allowed disposition.
2. Every minimum-valid canonical has at least one valid final lineage row.
3. Every `SUPPORTS_CANONICAL` or `SPLIT` disposition has its matching lineage.
4. Every lineage, mapping, relationship, manifest, and rights reference resolves.
5. SQLite foreign-key and integrity checks pass.
6. No source record, stable canonical ID, final lineage record, or audit fact is physically discarded.

## 9. Normalized final source lineage

Final lineage is a normalized many-to-many relation. Staging JSON, `raw_artifacts.promoted_artifact_id`, framework mappings, and free-text source notes are not substitutes for final lineage.

`artifact_source_lineage` contains:

| Field | Meaning |
|---|---|
| `artifact_id` | Existing canonical stable ID |
| `raw_artifact_id` | Existing preserved raw-record ID |
| `lineage_role` | `SUPPORTS_CANONICAL` or `SPLIT` |
| `mapping_strength` | `DIRECT`, `INDIRECT`, `PARTIAL`, or `INFORMATIVE` |
| `rationale` | Evidence for the contribution; mandatory for non-`DIRECT` strength |
| `is_primary` | Whether this is the principal source contribution |
| `created_at` | Audit timestamp |

The primary key is `(artifact_id, raw_artifact_id)`. Both identifiers are foreign keys. Lineage must be inserted, validated, and promoted transactionally with the related disposition and canonical changes. A dangling or inconsistent row fails closed.

## 10. Nine-sheet Excel round trip

Excel is the primary human bulk-curation interface. SQLite remains authoritative. A governed workbook has exactly these sheets in this stable order:

| Sheet | Semantics |
|---|---|
| `00_Manifest` | Contract/schema/tool versions and semantic hashes for the database baseline, contract, reference lists, and workbook payload |
| `01_Artifacts` | Canonical identity, minimum content, classification, publication, and active-state edits |
| `02_Source_Lineage` | Normalized canonical-to-raw contribution rows |
| `03_Framework_Mappings` | Evidence-bearing framework references, strength, and rationale |
| `04_Relationships` | Directed normalized artifact relationships and required conflict-resolution data |
| `05_Tags` | Normalized controlled tags; never a replacement for SDT classification |
| `06_Type_Specific` | Type-specific fields and relational requirements such as risk remediation |
| `07_Reference_Lists` | Controlled values and named ranges used for spreadsheet dropdown validation |
| `08_Validation_Errors` | Actionable severity, code, sheet, row, key, field, message, and current database hash |

### 10.1 Command sequence

The only supported bulk round trip is:

```text
export -> validate -> plan -> transactional apply
```

The command contract is:

```text
catalog_workbook export   --db <working.db> --out <catalog.xlsx>
catalog_workbook validate --db <working.db> --workbook <catalog.xlsx> --out <validated.xlsx>
catalog_workbook plan     --db <working.db> --workbook <validated.xlsx> --out <plan.json> --actor <name>
catalog_workbook apply    --db <working.db> --plan <plan.json> --actor <name> [--resolution <resolution.json>]
```

`apply` accepts only a previously validated deterministic plan. Any error rolls back the complete transaction and its catalog mutations.

### 10.2 Editable-row envelope and actions

Every editable row contains `row_key`, `row_version`, `baseline_hash`, and `action`. Allowed actions are:

| Action | Behavior |
|---|---|
| `NO_CHANGE` | Semantic content must equal the exported baseline; no mutation |
| `UPSERT` | Insert or update only whitelisted mutable fields while preserving immutable identity and passing all validation |
| `DEPRECATE` | Supported only for `01_Artifacts`; set publication to `DEPRECATED` and `is_active = 0` without physical deletion |

Row omission means `NO_CHANGE`: an omitted row is not compared, mutated, deprecated, or deleted. Child-row deletion is unsupported until a separate lifecycle contract authorizes it. Formulas in editable cells are validation errors.

### 10.3 Semantic hashing and conflicts

Row and payload hashes cover Unicode-NFC, UTF-8 canonical JSON with sorted keys, explicit nulls, and fixed field allowlists. Formatting, comments, formulas, and export time do not affect semantic hashes.

A database baseline change or row-hash change since export produces `CONFLICT`. Latest-wins and latest-export-wins behavior are forbidden. A conflict is never applied automatically.

An explicit resolution must identify the row, expected current hash, actor, and reason. The resolved proposal must still pass the complete minimum, controlled-value, closure, and integrity validation inside the transaction. An override cannot bypass validation, and every decision is audited.

## 11. Working database and release guard

Never perform curation, migration development, workbook apply, corpus normalization, or qualification directly against `mobile/assets/catalog.db`.

Use a copied working database or a separately named release-candidate database, for example:

```powershell
Copy-Item -LiteralPath catalog_work.db -Destination dist/catalog-curation-working.db
```

Mutating curation commands must reject a resolved target equal to `mobile/assets/catalog.db`. This guard is path-based after normalization, not a string comparison that can be bypassed with relative segments.

The release process must:

1. Build from pinned sources and manifests into a staging or candidate path.
2. Apply migrations and curation transactionally.
3. Validate minimum and strict results separately.
4. Verify disposition, lineage, mapping, relationship, foreign-key, and SQLite integrity closure.
5. Apply rights-safe raw-text scrubbing to the candidate.
6. Produce and verify a deterministic database/manifest pair.
7. Qualify a catalog-data upgrade against a clone containing representative profiles, selected controls, assessments, evidence, and exceptions.
8. Measure the declared performance categories against established project baselines and thresholds only.
9. Replace `mobile/assets/catalog.db` only through the verified release process after every applicable gate passes.

If candidate publication fails, retain the existing release asset and the audit evidence needed for recovery. Do not partially replace the database/manifest pair.

## 12. Preservation and validation guarantees

All curation paths must preserve:

- every raw source record and its content hash;
- canonical stable IDs;
- final source lineage;
- normalized mappings, relationships, and tags;
- catalog/profile separation;
- existing profiles, selections, assessments, evidence, exceptions, and operational history;
- workbook, promotion, migration, and release audit history;
- deterministic reconstruction from pinned inputs.

Validation reports are deterministic and include input/contract hashes, separate minimum and strict results, closure and integrity findings, rights/provenance findings, and summaries by result, artifact type, and SDT domain.

Command exit codes are:

- `0`: all requested gates pass.
- `1`: validation failure.
- `2`: qualification is blocked by an explicitly reported prerequisite.

Performance evidence declares the target profile and corpus population and measures representative query latency, startup impact, database size, memory impact, migration duration, and integrity validation. Existing evidence-backed thresholds are enforced. A missing threshold is recorded as a baseline gap, not replaced by an invented release limit.
