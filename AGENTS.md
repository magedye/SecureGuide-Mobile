# AGENTS.md - SecureGuide Implementation Contract

## Purpose

This file defines the working rules for any AI agent or developer implementing SecureGuide.

The project goal is to build an offline-first security knowledge and assessment platform that imports security catalogs, normalizes every security element into a unified artifact model, classifies it using USACM and SDT, lets users select relevant templates or artifacts for an enterprise context, and tracks implementation, verification, evidence, gaps, and progress per profile.

## Primary Authorities

The main source of truth is:

1. `SecureGuide_Mobile_Docs/USACM_v2.2.1_Unified_Security_Artifact_Classification_Model.md`
2. `SecureGuide_Mobile_Docs/SDT_v2.2.1_Security_Domain_Taxonomy.md`

The primary architectural guides are:
3. `SecureGuide_Mobile_Docs/00_Executive_Summary_and_Vision.md`
4. `PROJECT_VISION.md`

The normative policy for writing and formatting artifact content is:
5. `docs/AUTHORING_POLICY.md`

The normative project policy for selecting and distinguishing artifact types is:
6. `docs/ARTIFACT_TYPE_POLICY.md`

This policy is subordinate to USACM v2.2.1 and must not introduce additional `ART-*` values.

Use other project documents only as supporting material. If any document, screen idea, schema draft, or implementation detail conflicts with USACM v2.2.1 or SDT v2.2.1, USACM and SDT win.

Before making schema, classification, import, assessment, or reporting changes, read the relevant parts of the primary documents.

## Non-Negotiable Design Rules

### 1. Separate Reference Data From Operational Data

`security_artifacts` is the Master Catalog. It describes what an artifact is.

`enterprise_profiles`, `profile_artifacts`, `profile_assessments`, profile evidence, and profile exceptions describe what is happening in a specific organization, branch, system, audit, environment, or template instance.

Do not store organization-specific implementation state only in the Master Catalog.

Allowed in the Master Catalog:

- Artifact identity and source metadata
- Artifact type and abstraction level
- Domain and sub-domain
- Reference priority and default obligation
- Reference testability
- Reference applicability
- Reference mappings, tags, relationships, dependencies, and verification methods
- AI classification metadata
- Publication and import metadata

Must be profile-specific:

- `implementation_status`
- `verification_status`
- `effectiveness`
- `exception_status`
- assessment score and comments
- evidence
- assigned owner for that organization
- due dates and review execution
- profile-specific priority overrides
- risk acceptance and exception justification

If a USACM baseline table contains operational fields in `security_artifacts`, treat them as default or reference fields only when building SecureGuide profiles. Never let them replace profile-specific state.

### 2. Do Not Treat All Items As Controls

In Arabic user-facing conversation, **الضوابط** is the agreed umbrella term for
all catalog artifacts. It does not change the stored USACM `type`: only
`ART-CTR` is a Security Control in the classification model.

Every imported item must be classified by `type`.

Use the USACM artifact types exactly:

- `ART-REQ`, `ART-OBJ`, `ART-PRI`, `ART-POL`, `ART-STD`
- `ART-CTR`, `ART-CTE`
- `ART-PRO`, `ART-PRC`, `ART-PRG`, `ART-PLN`, `ART-TSK`
- `ART-CFG`, `ART-RUL`
- `ART-EVD`, `ART-MET`
- `ART-EXC`, `ART-RSK`, `ART-AST`, `ART-THR`, `ART-VUL`, `ART-OWN`

Use `ART-CFG` for concrete technical settings, baselines, and hardening values.
Use `ART-REQ` for statements of required outcomes or obligations.
Use `ART-CTR` for safeguards or risk-reducing measures.
Use `ART-EVD` for proof, artifacts, logs, reports, or attestations.
Use `ART-RSK`, `ART-THR`, `ART-VUL`, and `ART-AST` only when the item itself is a risk, threat, vulnerability, or asset.

### 3. Keep Type, Level, and Domain Separate

`type` answers: what is this artifact?

`abstraction_level` answers: where does it sit in the operating model?

`primary_domain` and `sub_domain` answer: what security domain does it primarily belong to?

Do not infer one of these fields automatically from another without explicit rules and validation.

### 4. Enforce Single Domain Classification

Each artifact gets exactly one `primary_domain` and exactly one `sub_domain`.

Use SDT v2.2.1:

- `SD-01` Governance, Risk & Compliance
- `SD-02` Assets, Data & Privacy
- `SD-03` Identity, Access & Privilege
- `SD-04` Infrastructure, Network & Cloud
- `SD-05` Applications, Development & Change
- `SD-06` Detection, Monitoring & Vulnerability
- `SD-07` Response, Recovery & Resilience
- `SD-08` People, Third Parties & Physical

There are exactly 40 SDT sub-domains. `sub_domain` must belong to `primary_domain`.

Use SDT tie-breakers. In particular:

- Cloud IAM is `SD-03` when the main focus is identity, authentication, authorization, or privilege.
- Cloud platform configuration or workload protection is `SD-04`.
- Application/API testing is `SD-05`.
- Broad penetration testing, red teaming, and maturity assessment are `SD-06`.
- Ambiguous legacy technology controls require human review unless confidence is above 0.70.

### 5. Use Tags For Secondary Context

Tags do not replace domain classification.

Allowed tag types are exactly:

- `Technology`
- `Framework`
- `Concept`
- `Context`
- `Threat`
- `Data`
- `Party`

Store tags as normalized rows in `artifact_tags`, not as comma-separated strings or duplicated JSON arrays in `security_artifacts`.

Examples:

- `Technology`: Windows, Linux, Azure, AWS, Kubernetes
- `Framework`: CIS, ISO 27002, NIST CSF, PCI DSS, NCA
- `Concept`: Zero Trust, Least Privilege, Defense in Depth
- `Context`: Production, Cloud, Mobile, OT, IoT, SaaS
- `Threat`: Ransomware, Phishing, Insider Threat
- `Data`: PII, Cardholder Data, Confidential
- `Party`: Supplier, Customer, Regulator, Employee

### 6. SQLite Is Normative

SecureGuide is offline-first. SQLite is the normative storage model for mobile and embedded deployments.

Use normalized child tables for repeatable structures:

- `artifact_tags`
- `artifact_relationships`
- `framework_mappings`
- `artifact_applicability_scope`
- `artifact_self_assessments` when using USACM reference assessments
- `technical_dependencies`
- `verification_tools`
- `stakeholders` or profile-specific stakeholders
- `remediation_actions`
- `external_references`

Do not duplicate repeatable arrays as JSON columns in `security_artifacts`.

Enable foreign keys in SQLite:

`PRAGMA foreign_keys = ON;`

### 7. Controlled Fields Must Use Controlled Values

Do not invent enum values.

Use USACM controlled lists for:

- artifact type
- abstraction level
- obligation source
- obligation level
- exception status
- granularity
- control nature
- control function
- testability
- implementation status
- verification status
- effectiveness
- priority
- relationship type
- AI review status
- requirement type
- mapping strength
- tag type
- review frequency
- publication status
- source type
- asset type
- maturity level
- cost category
- import status

If product language needs friendly labels, map labels at the UI layer. Do not change database values.

### 8. Do Not Collapse Operational Status Fields

Never merge these fields into one status:

- `implementation_status`
- `verification_status`
- `effectiveness`
- `exception_status`

They answer different questions:

- Is it implemented?
- Was it verified?
- Is it effective?
- Is there an exception?

### 9. AI Classification Must Be Accountable

AI may assist classification, but it is not silent authority.

Any AI-generated classification must include:

- `classification_confidence`
- `classification_rationale`
- `ai_review_status`
- `requires_human_review`
- rejected alternatives when relevant

If `classification_confidence <= 0.70`, set:

- `requires_human_review = 1`
- `ai_review_status = AIR-HUMAN-REVIEW`

Never auto-publish a low-confidence artifact.

### 10. Mappings Are Evidence-Bearing

Use `framework_mappings` for framework references and crosswalks.

`mapping_strength` must be one of:

- `DIRECT`
- `INDIRECT`
- `PARTIAL`
- `INFORMATIVE`

Any mapping other than `DIRECT` requires a non-empty rationale.

Do not claim equivalence between frameworks without recording mapping strength and rationale.

### 11. Relationships Must Be Explicit

Use `artifact_relationships` instead of free text for artifact graph logic.

Allowed relationship types:

- `REL-DER`: source derives from target
- `REL-SAT`: source satisfies target
- `REL-SUP`: source supports target
- `REL-SPL`: source specifies target
- `REL-IMP`: source implements target
- `REL-VER`: source verifies target
- `REL-MEA`: source measures target
- `REL-MIT`: source mitigates target
- `REL-AFF`: source affects target
- `REL-EXC`: source exempts target
- `REL-DEP`: source depends on target
- `REL-CNF`: source conflicts with target

`REL-CNF` requires `resolution_status` and `resolution_note`.

Do not create relationships to missing artifacts.

### 12. Do Not Destructively Merge Imported Artifacts

Raw imported items from CIS, ISO, NIST, Microsoft, OWASP, MITRE, or other sources must remain traceable.

For duplicates or near-duplicates:

- preserve original source records
- use relationships, mappings, or equivalence groups
- keep source document, version, section, and raw artifact ID
- prefer deprecation over deletion

If a true merge is required, preserve old IDs and source lineage through references or relationships.

## Architecture Rules

SecureGuide uses a 5-layer offline-first architecture:

1. Presentation Layer
2. Service & State Layer
3. Core Engines Layer
4. Data Access Layer
5. Storage Layer

Keep business logic out of UI components. UI should call services, state managers, repositories, or engines.

Use the active `enterprise_profile_id` as part of any query that displays operational state. A user viewing a catalog artifact inside a profile must see that profile's state, not a global state.

## Core Engines

Implement engines incrementally. Do not overbuild all engines before the MVP works.

Required for MVP:

- Import and Normalization
- Classification
- Search and Filter
- Template Selection
- Profile Context
- Assessment
- Data Integrity

Later phases may add:

- Priority and Weighting
- Recommendation
- Mapping and Crosswalk intelligence
- Threat and Indicator intelligence
- Asset risk scoring
- Sync

## Import Pipeline

Every import should follow this order:

1. Store source catalog metadata.
2. Store raw artifact content before transformation.
3. Normalize title, description, source, section, version, and keywords.
4. Classify `type`.
5. Classify `abstraction_level`.
6. Classify `primary_domain` and `sub_domain` using SDT.
7. Assign source, source_type, obligation level, granularity, and control fields where applicable.
8. Extract normalized tags.
9. Create framework mappings.
10. Detect duplicates or near-duplicates without destroying source lineage.
11. Validate JSON Schema and SQLite constraints.
12. Route low-confidence or conflicting records to human review.
13. Publish only valid approved records.

## Template Rules

Templates are selections and rules over Master Catalog artifacts. They are not copies of artifacts.

A template item should be able to record:

- artifact reference
- inclusion reason
- mandatory, recommended, optional, or conditional status
- applicability condition
- default priority override
- default profile review frequency
- template version

Creating a profile from a template should create profile-specific rows that reference catalog artifacts.

Do not modify the Master Catalog when a user changes template-derived operational state.

## Profile and Assessment Rules

An `enterprise_profile` can represent:

- an organization
- a branch
- a department
- a system
- a cloud environment
- an audit scope
- a project
- a custom assessment context

`profile_artifacts` links a profile to selected Master Catalog artifacts and stores profile-specific current state.

`profile_assessments` stores historical assessment events.

Evidence must be profile-specific unless it is a reference evidence example.

Reports and dashboards must calculate from profile state, not from the global catalog alone.

## Asset, Risk, Threat, and Vulnerability Rules

Use asset intelligence only when the required model and calculations are defined.

Do not display risk scores unless the formula is explicit and traceable.

At minimum, risk or priority calculations must identify their inputs, such as:

- asset criticality
- exposure
- related vulnerabilities
- related threats
- implementation gaps
- verification failure
- exception status

Use relationships to connect:

- controls to risks or vulnerabilities through `REL-MIT`
- threats or risks to assets through `REL-AFF`
- evidence to controls through `REL-VER`
- configurations or rules to controls through `REL-IMP`

## UI and UX Rules

The UI must make the Master Catalog vs Profile distinction visible.

Core screens should include:

- Dashboard for the active profile
- Master Catalog search and filtering
- Artifact Detail with source, classification, tags, mappings, relationships, and active profile state
- Template selection and preview
- Profile assessment workspace
- Evidence and review queue
- Reports

Filters should support:

- artifact type
- primary domain
- sub-domain
- source/framework
- tags
- obligation level
- testability
- priority
- implementation status within active profile
- verification status within active profile
- exception status within active profile
- applicability scope
- AI review status

Do not show global implementation status as if it were universal.

## MVP Scope

The first successful version should do these things well:

1. Create the SQLite database with USACM and SDT constraints.
2. Import the current JSON catalogs.
3. Preserve raw imported artifacts.
4. Convert imported items into `security_artifacts`.
5. Classify each item by USACM and SDT.
6. Store normalized tags, mappings, relationships, and applicability scope.
7. Provide a searchable Master Catalog.
8. Create and manage enterprise profiles.
9. Create a profile from a template or selected artifacts.
10. Track implementation, verification, effectiveness, exceptions, notes, evidence, and assessment history per profile.
11. Show a basic dashboard of progress and gaps.
12. Export a simple report.

Defer advanced features until the MVP is stable:

- complex threat graphs
- SIEM or EDR integrations
- automated evidence collection
- collaborative sync
- advanced recommendation engine
- predictive risk scoring

## Validation Checklist For Every Change

Before finishing any implementation task, verify:

- Does it preserve Master Catalog vs Profile separation?
- Does it follow USACM enum values?
- Does it follow SDT single-domain classification?
- Does every `sub_domain` belong to its `primary_domain`?
- Are tags normalized and restricted to approved tag types?
- Are repeatable fields stored in child tables instead of JSON blobs?
- Are operational states profile-specific?
- Are framework mappings given mapping strength and rationale where required?
- Are relationships valid and directionally meaningful?
- Are low-confidence AI outputs routed to review?
- Are raw source records still traceable?
- Are SQLite foreign keys and constraints respected?
- Are user-visible labels mapped from stable codes instead of replacing stable codes?
- Are tests or validation queries included for risky schema or import changes?

## Coding Standards

Follow the existing project structure and framework choices.

Prefer small, focused changes that preserve data integrity.

Add migrations instead of mutating existing schema assumptions silently.

For database changes:

- include constraints
- include indexes for expected filters
- include migration path
- include rollback or recovery notes when practical
- include validation queries or tests

For import/classification changes:

- test with at least one governance item
- test with one technical configuration item
- test with one ambiguous or low-confidence item
- test duplicate detection without destructive merge

For UI changes:

- show active profile context when operational state appears
- keep catalog-only and profile-specific views distinct
- avoid hiding review states or uncertainty
- expose source and rationale for classified artifacts

## Review Standard

Reject or revise any implementation that:

- stores profile implementation state only in `security_artifacts`
- treats all imported records as `ART-CTR`
- invents enum values outside USACM
- creates multiple primary domains for one artifact
- uses tags instead of SDT domain classification
- stores tags, relationships, applicability, or assessments as duplicated JSON arrays in the artifact row
- auto-publishes low-confidence AI classifications
- merges source artifacts without preserving lineage
- creates mappings without strength or rationale
- reports risk scores without a defined formula

## Preferred Implementation Order

1. Reference data and schema constraints
2. Raw import preservation
3. USACM artifact normalization
4. SDT domain classification
5. Tags and mappings
6. Review workflow
7. Template model
8. Enterprise profile model
9. Profile assessment model
10. Search and filter
11. Dashboard and reports
12. Assets, risks, threats, and recommendations

## Recommendation And Decision Presentation Standard

When presenting recommendations, alternative implementations, architectural decisions, or next-step choices, provide **three feasible options**.

1. **Option 1 must be the recommended option.** Label it clearly as `Recommended` / `موصى به` and place it first.
2. Options 2 and 3 must be credible alternatives with materially different tradeoffs. Do not create artificial, unsafe, or non-compliant alternatives merely to reach three options.
3. For every option, include:
   - a concise description of the proposed action
   - the main justification and expected benefit
   - the principal cost, limitation, or tradeoff
   - a confidence score as a percentage and a qualitative label
4. After the three options, explain briefly why Option 1 is preferred over Options 2 and 3 for the current project state and user objective.
5. Confidence measures how strongly the available evidence supports the option as a suitable choice for the stated objective. It is not a guarantee of success.

Use these confidence labels consistently:

- **High confidence:** 85-100%
- **Medium confidence:** 60-84%
- **Low confidence:** below 60%

Base confidence on repository evidence, completed validation, authoritative project documents, known constraints, and unresolved assumptions. State the assumption or missing evidence when confidence is below 85%.

If fewer than three valid options genuinely exist because of safety, compliance, data-integrity, or authorization constraints, present the valid options only and explicitly explain why additional options would be invalid. Never weaken USACM, SDT, lineage, profile isolation, or SQLite integrity rules to manufacture another choice.

## Final Principle

SecureGuide should be extensible because the model is disciplined, not because the code accepts anything.

When in doubt, preserve source lineage, validate against USACM and SDT, store uncertainty explicitly, and route ambiguous decisions to human review.

## Specification-Driven Development (Spec Kit) Governance

1. **Spec Kit Governs Execution**: GitHub Spec Kit governs feature execution. The active feature `spec.md`, `plan.md`, and `tasks.md` located in `specs/` are authoritative.
2. **Constitution is Mandatory**: Principles in `.specify/memory/constitution.md` are non-negotiable.
3. **Autonomous Execution**: Agents should continue documented tasks autonomously in dependency order.
4. **Complete the Loop**: Agents should implement, test, verify, update task status, and continue.
5. **Autonomy on Routine Decisions**: Routine implementation decisions do not require user approval.
6. **When to Stop**: Agents stop only for genuine product-level ambiguity, destructive irreversible actions requiring authorization, or unavoidable external dependencies.
