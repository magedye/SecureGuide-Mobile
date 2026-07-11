# Unified Security Artifact Classification Model (USACM) v2.2.1
## Self-Contained Reference for Security Knowledge Bases, GRC Platforms, Mobile Applications, and AI Agents

| Field | Value |
|---|---|
| Document Title | Unified Security Artifact Classification Model (USACM) v2.2.1 |
| Version | 2.2.1 |
| Status | Production Baseline - Corrective Release |
| Date | 2026-07-10 |
| Purpose | Provide a unified model for classifying, describing, validating, relating, governing, reviewing, importing, and operationalizing all security artifacts. |
| Target Audience | AI agents, mobile application teams, developers, security architects, GRC teams, auditors, risk owners, and control owners. |
| Compatibility | SDT v2.2.1, SQLite, NIST CSF 2.0, ISO/IEC 27002:2022, CIS Controls v8.1, PCI DSS v4.0, NIST SP 800-53 Rev.5. |
| Supersedes | USACM v2.2.0 |

## 1. Executive Purpose

USACM v2.2.1 is the enterprise and mobile-ready artifact model for security requirements, objectives, principles, policies, standards, controls, enhancements, processes, procedures, programs, plans, tasks, technical configurations, tool rules, evidence, metrics, exceptions, risks, assets, threats, vulnerabilities, and accountable owners.

This release corrects the remaining v2.2.0 production issues: normalized SQLite storage for repeatable collections, fully defined `applicability_scope`, JSON Schema enforcement for review and publication rules, creation of all auxiliary tables in migration, and additional cost and effort fields for planning.

## 2. Design Principles

| Principle | Rule |
|---|---|
| Type/Level separation | `type` answers what the artifact is; `abstraction_level` answers where it sits in the operating model. |
| Requirement/control separation | Requirements state what must be achieved; controls state how risk is reduced or obligations are met. |
| Single domain rule | Each artifact has exactly one `primary_domain` and one `sub_domain`; tags carry secondary context. |
| SQLite-first | SQLite is normative for mobile and embedded deployments. Server systems may translate the model, but the source design is SQLite. |
| Normalized storage | Repeatable collections are stored in child tables in SQLite. JSON Schema may represent them as arrays for API exchange, but SQLite must not duplicate them as JSON columns. |
| AI accountability | AI-generated classifications must include confidence, rationale, review status, and rejected alternatives when relevant. |
| Lifecycle control | Artifacts have review, publication, exception, import, assessment, maturity, cost, and ownership metadata. |

## 3. Security Artifact Types (ART-*)

| Code | Meaning |
|---|---|
| ART-REQ | Requirement |
| ART-OBJ | Security Objective |
| ART-PRI | Security Principle |
| ART-POL | Security Policy |
| ART-STD | Security Standard |
| ART-CTR | Security Control |
| ART-CTE | Control Enhancement |
| ART-PRO | Security Process |
| ART-PRC | Security Procedure |
| ART-PRG | Security Program |
| ART-PLN | Security Plan |
| ART-TSK | Task |
| ART-CFG | Technical Configuration |
| ART-RUL | Technical Rule |
| ART-EVD | Evidence |
| ART-MET | Metric/KPI |
| ART-EXC | Security Exception |
| ART-RSK | Security Risk |
| ART-AST | Information Asset |
| ART-THR | Threat |
| ART-VUL | Vulnerability |
| ART-OWN | Owner/Role |


## 4. Controlled Code Lists


### 4.1 Abstraction Level (ABS-*)
| Value |
|---|
| ABS-GOV |
| ABS-RIS |
| ABS-POL |
| ABS-CTR |
| ABS-PRO |
| ABS-TEC |
| ABS-EVM |


### 4.2 Obligation Source (SRC-*)
| Value |
|---|
| SRC-REG |
| SRC-LEG |
| SRC-CON |
| SRC-STD |
| SRC-INT |
| SRC-BST |
| SRC-RSK |


### 4.3 Obligation Level (OBL-*)
| Value |
|---|
| OBL-MND |
| OBL-CON |
| OBL-REC |
| OBL-OPT |


### 4.4 Exception Status (EXC-*)
| Value |
|---|
| EXC-NONE |
| EXC-NOT-APPLICABLE |
| EXC-RISK-ACCEPTED |
| EXC-DEFERRED |
| EXC-UNAVAILABLE |


### 4.5 Granularity Level (GRN-*)
| Value |
|---|
| GRN-HIGH |
| GRN-MEDIUM |
| GRN-DETAILED |
| GRN-EXECUTABLE |
| GRN-TECHNICAL |
| GRN-EVIDENTIARY |
| GRN-METRIC |


### 4.6 Control Nature (NAT-*)
| Value |
|---|
| NAT-ORG |
| NAT-HUM |
| NAT-PHY |
| NAT-TEC |


### 4.7 Control Function (FUN-*)
| Value |
|---|
| FUN-PRE |
| FUN-DET |
| FUN-COR |
| FUN-REC |
| FUN-DRR |
| FUN-COM |


### 4.8 Testability (TST-*)
| Value |
|---|
| TST-AUTO |
| TST-MAN |
| TST-DOC |
| TST-INT |
| TST-NA |


### 4.9 Implementation Status (STS-*)
| Value |
|---|
| STS-NOT-APPLIED |
| STS-PARTIAL |
| STS-FULL |
| STS-PLANNED |
| STS-NEEDS-IMPROVEMENT |


### 4.10 Verification Status (VER-*)
| Value |
|---|
| VER-NOT-VERIFIED |
| VER-PASS |
| VER-FAIL |


### 4.11 Effectiveness (EFF-*)
| Value |
|---|
| EFF-LOW |
| EFF-MEDIUM |
| EFF-HIGH |
| EFF-UNKNOWN |


### 4.12 Priority (PRI-*)
| Value |
|---|
| PRI-CRITICAL |
| PRI-HIGH |
| PRI-MEDIUM |
| PRI-LOW |


### 4.13 Relationship Type (REL-*)
| Value |
|---|
| REL-DER |
| REL-SAT |
| REL-SUP |
| REL-SPL |
| REL-IMP |
| REL-VER |
| REL-MEA |
| REL-MIT |
| REL-AFF |
| REL-EXC |
| REL-DEP |
| REL-CNF |


### 4.14 AI Review Status (AIR-*)
| Value |
|---|
| AIR-AUTO-ACCEPTED |
| AIR-HUMAN-REVIEW |
| AIR-HUMAN-APPROVED |
| AIR-HUMAN-REJECTED |


### 4.15 Requirement Type (RQT-*)
| Value |
|---|
| RQT-GOV |
| RQT-REG |
| RQT-LEG |
| RQT-CON |
| RQT-STD |
| RQT-INT |
| RQT-RSK |


### 4.16 Mapping Strength
| Value |
|---|
| DIRECT |
| INDIRECT |
| PARTIAL |
| INFORMATIVE |


### 4.17 Tag Type
| Value |
|---|
| Technology |
| Framework |
| Concept |
| Context |
| Threat |
| Data |
| Party |


### 4.18 Review Frequency
| Value |
|---|
| DAILY |
| WEEKLY |
| MONTHLY |
| QUARTERLY |
| SEMI-ANNUAL |
| ANNUAL |
| BIENNIAL |
| AD-HOC |
| CONTINUOUS |


### 4.19 Publication Status
| Value |
|---|
| DRAFT |
| UNDER_REVIEW |
| APPROVED |
| PUBLISHED |
| DEPRECATED |
| WITHDRAWN |


### 4.20 Source Type
| Value |
|---|
| DOCUMENT |
| SYSTEM |
| TOOL |
| INTERVIEW |
| OBSERVATION |
| STANDARD |
| REGULATION |


### 4.21 Asset Type
| Value |
|---|
| HARDWARE |
| SOFTWARE |
| DATA |
| SERVICE |
| FACILITY |
| PERSONNEL |
| NETWORK |
| CLOUD_INSTANCE |
| DOCUMENT |
| INTELLECTUAL_PROPERTY |


### 4.22 Maturity Level
| Value |
|---|
| INITIAL |
| REPEATABLE |
| DEFINED |
| MANAGED |
| OPTIMIZED |


### 4.23 Cost Category
| Value |
|---|
| LOW |
| MEDIUM |
| HIGH |
| VERY_HIGH |


### 4.24 Import Status
| Value |
|---|
| NEW |
| IMPORTED |
| UPDATED |
| MERGED |
| CONFLICT |
| REJECTED |


## 5. Security Domains

USACM uses SDT v2.2.1 for domain assignment. The values below are authoritative for `primary_domain` and `sub_domain`.

| Primary Domain | Name |
|---|---|
| SD-01 | Governance, Risk & Compliance |
| SD-02 | Assets, Data & Privacy |
| SD-03 | Identity, Access & Privilege |
| SD-04 | Infrastructure, Network & Cloud |
| SD-05 | Applications, Development & Change |
| SD-06 | Detection, Monitoring & Vulnerability |
| SD-07 | Response, Recovery & Resilience |
| SD-08 | People, Third Parties & Physical |


### 5.1 Complete Sub-Domain Reference
| Primary | Sub-Domain | Name |
|---|---|---|
| SD-01 | SD-01.01 | Cybersecurity Strategy & Governance |
| SD-01 | SD-01.02 | Policies, Standards & Exceptions |
| SD-01 | SD-01.03 | Security Risk Management |
| SD-01 | SD-01.04 | Compliance, Audit & Assurance |
| SD-01 | SD-01.05 | Security Program Management & Metrics |
| SD-02 | SD-02.01 | Asset Inventory & Management |
| SD-02 | SD-02.02 | Software & License Management |
| SD-02 | SD-02.03 | Data Classification & Ownership |
| SD-02 | SD-02.04 | Data Protection & Encryption |
| SD-02 | SD-02.05 | Privacy, Retention & Disposal |
| SD-03 | SD-03.01 | Identity Lifecycle Management |
| SD-03 | SD-03.02 | Authentication & Credential Management |
| SD-03 | SD-03.03 | Authorization & Access Management |
| SD-03 | SD-03.04 | Privileged Access Management |
| SD-03 | SD-03.05 | Remote & External Access |
| SD-04 | SD-04.01 | Network & Communications Security |
| SD-04 | SD-04.02 | Systems, Servers & Endpoint Security |
| SD-04 | SD-04.03 | Configuration & Security Hardening |
| SD-04 | SD-04.04 | Cloud & Virtual Platform Security |
| SD-04 | SD-04.05 | Email, Web & Digital Communications |
| SD-05 | SD-05.01 | Application Security Governance & SDLC |
| SD-05 | SD-05.02 | Application & API Security Testing |
| SD-05 | SD-05.03 | Code, Components & Software Supply Chain |
| SD-05 | SD-05.04 | Change & Release Management |
| SD-05 | SD-05.05 | Database & Critical Application Security |
| SD-06 | SD-06.01 | Logging & Security Monitoring |
| SD-06 | SD-06.02 | Threat Detection & Alerts |
| SD-06 | SD-06.03 | Vulnerability & Patch Management |
| SD-06 | SD-06.04 | Security Testing & Assessments |
| SD-06 | SD-06.05 | Threat Intelligence & IoCs |
| SD-07 | SD-07.01 | Incident Management |
| SD-07 | SD-07.02 | Digital Forensics & Evidence |
| SD-07 | SD-07.03 | Backup & Restore |
| SD-07 | SD-07.04 | Business Continuity & Disaster Recovery |
| SD-07 | SD-07.05 | Crisis Management & Communication |
| SD-08 | SD-08.01 | Awareness, Training & Security Culture |
| SD-08 | SD-08.02 | HR Security & Employee Lifecycle |
| SD-08 | SD-08.03 | Supplier & Third-Party Management |
| SD-08 | SD-08.04 | Physical & Environmental Security |
| SD-08 | SD-08.05 | Acceptable Use & Professional Conduct |


## 6. Validation Rules
| Rule | Requirement |
|---|---|
| USACM-VAL-001 | All controlled fields must use the enumerated values defined in this document. |
| USACM-VAL-002 | `sub_domain` must belong to the selected `primary_domain`; for example `SD-03.02` requires `primary_domain = SD-03`. |
| USACM-VAL-003 | `ART-CTR` and `ART-CTE` require `control_nature`, `control_function`, and `testability`. |
| USACM-VAL-004 | `ART-REQ` requires non-null `requirement_type`. |
| USACM-VAL-005 | Do not merge implementation, verification, effectiveness, or exception status into a single field. |
| USACM-VAL-006 | `ART-EXC` requires `exception_approval_date` and `exception_expiry_date`. |
| USACM-VAL-007 | `ART-AST` requires `asset_type` and `asset_criticality`. |
| USACM-VAL-008 | `ART-RSK` should include at least one remediation action. |
| USACM-VAL-009 | `classification_confidence <= 0.70` requires `requires_human_review = true` and `ai_review_status = AIR-HUMAN-REVIEW`. |
| USACM-VAL-010 | AI-generated records with `classification_confidence` must include non-empty `classification_rationale`. |
| USACM-VAL-011 | Relationships must not point to missing target artifacts. |
| USACM-VAL-012 | `REL-CNF` requires `resolution_status` and `resolution_note`. |
| USACM-VAL-013 | Framework mappings require `framework`, `version`, `reference`, and `mapping_strength`. |
| USACM-VAL-014 | Framework mappings with `mapping_strength` other than `DIRECT` require non-empty `rationale`. |
| USACM-VAL-015 | `mapping_strength` must be one of `DIRECT`, `INDIRECT`, `PARTIAL`, or `INFORMATIVE`. |
| USACM-VAL-016 | `priority_weight` must match `priority`: critical=10, high=7, medium=4, low=1. |
| USACM-VAL-017 | Tags must follow SDT controlled tag taxonomy and use one approved `tag_type`. |
| USACM-VAL-018 | Published `ART-POL`, `ART-STD`, and `ART-PRC` records must include `effective_date`. |
| USACM-VAL-019 | Records with `review_frequency` other than `AD-HOC` must include `next_review_date`. |
| USACM-VAL-020 | SQLite storage must be normalized for repeatable collections; do not duplicate arrays as JSON columns in `security_artifacts`. |
| USACM-VAL-021 | `applicability_scope` must use the defined properties and reject additional properties. |
| USACM-VAL-022 | Cost estimates must be non-negative, and `cost_estimate_max` must be greater than or equal to `cost_estimate_min` when both are present. |


## 7. Normative JSON Schema

The following JSON Schema is normative for API exchange, AI output validation, import validation, and mobile synchronization payloads. SQLite remains normalized even where the API schema exposes arrays for convenience.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "USACM v2.2.1 Security Artifact Record",
  "type": "object",
  "required": [
    "id",
    "type",
    "title_en",
    "primary_domain",
    "sub_domain",
    "abstraction_level",
    "source",
    "source_type",
    "obligation_level",
    "granularity_level",
    "priority",
    "priority_weight",
    "implementation_status",
    "verification_status",
    "effectiveness",
    "exception_status",
    "publication_status",
    "source_document",
    "version",
    "is_active"
  ],
  "properties": {
    "id": {
      "type": "string",
      "pattern": "^[A-Z0-9][A-Z0-9_-]{2,80}$"
    },
    "source_artifact_id": {
      "type": [
        "string",
        "null"
      ]
    },
    "temp_id": {
      "type": [
        "string",
        "null"
      ]
    },
    "type": {
      "type": "string",
      "enum": [
        "ART-REQ",
        "ART-OBJ",
        "ART-PRI",
        "ART-POL",
        "ART-STD",
        "ART-CTR",
        "ART-CTE",
        "ART-PRO",
        "ART-PRC",
        "ART-PRG",
        "ART-PLN",
        "ART-TSK",
        "ART-CFG",
        "ART-RUL",
        "ART-EVD",
        "ART-MET",
        "ART-EXC",
        "ART-RSK",
        "ART-AST",
        "ART-THR",
        "ART-VUL",
        "ART-OWN"
      ]
    },
    "title_en": {
      "type": "string",
      "minLength": 1
    },
    "title_ar": {
      "type": [
        "string",
        "null"
      ]
    },
    "description_en": {
      "type": [
        "string",
        "null"
      ]
    },
    "description_ar": {
      "type": [
        "string",
        "null"
      ]
    },
    "primary_domain": {
      "type": "string",
      "enum": [
        "SD-01",
        "SD-02",
        "SD-03",
        "SD-04",
        "SD-05",
        "SD-06",
        "SD-07",
        "SD-08"
      ]
    },
    "sub_domain": {
      "type": "string",
      "pattern": "^SD-0[1-8]\\.0[1-5]$"
    },
    "abstraction_level": {
      "type": "string",
      "enum": [
        "ABS-GOV",
        "ABS-RIS",
        "ABS-POL",
        "ABS-CTR",
        "ABS-PRO",
        "ABS-TEC",
        "ABS-EVM"
      ]
    },
    "source": {
      "type": "string",
      "enum": [
        "SRC-REG",
        "SRC-LEG",
        "SRC-CON",
        "SRC-STD",
        "SRC-INT",
        "SRC-BST",
        "SRC-RSK"
      ]
    },
    "source_type": {
      "type": "string",
      "enum": [
        "DOCUMENT",
        "SYSTEM",
        "TOOL",
        "INTERVIEW",
        "OBSERVATION",
        "STANDARD",
        "REGULATION"
      ]
    },
    "source_location": {
      "type": [
        "string",
        "null"
      ]
    },
    "obligation_level": {
      "type": "string",
      "enum": [
        "OBL-MND",
        "OBL-CON",
        "OBL-REC",
        "OBL-OPT"
      ]
    },
    "requirement_type": {
      "type": "string",
      "enum": [
        "RQT-GOV",
        "RQT-REG",
        "RQT-LEG",
        "RQT-CON",
        "RQT-STD",
        "RQT-INT",
        "RQT-RSK"
      ]
    },
    "granularity_level": {
      "type": "string",
      "enum": [
        "GRN-HIGH",
        "GRN-MEDIUM",
        "GRN-DETAILED",
        "GRN-EXECUTABLE",
        "GRN-TECHNICAL",
        "GRN-EVIDENTIARY",
        "GRN-METRIC"
      ]
    },
    "control_nature": {
      "type": [
        "string",
        "null"
      ],
      "enum": [
        "NAT-ORG",
        "NAT-HUM",
        "NAT-PHY",
        "NAT-TEC",
        null
      ]
    },
    "control_function": {
      "type": [
        "string",
        "null"
      ],
      "enum": [
        "FUN-PRE",
        "FUN-DET",
        "FUN-COR",
        "FUN-REC",
        "FUN-DRR",
        "FUN-COM",
        null
      ]
    },
    "testability": {
      "type": [
        "string",
        "null"
      ],
      "enum": [
        "TST-AUTO",
        "TST-MAN",
        "TST-DOC",
        "TST-INT",
        "TST-NA",
        null
      ]
    },
    "scope": {
      "type": [
        "string",
        "null"
      ]
    },
    "owner_role": {
      "type": [
        "string",
        "null"
      ]
    },
    "priority": {
      "type": "string",
      "enum": [
        "PRI-CRITICAL",
        "PRI-HIGH",
        "PRI-MEDIUM",
        "PRI-LOW"
      ]
    },
    "priority_weight": {
      "type": "integer",
      "minimum": 1,
      "maximum": 10
    },
    "implementation_status": {
      "type": "string",
      "enum": [
        "STS-NOT-APPLIED",
        "STS-PARTIAL",
        "STS-FULL",
        "STS-PLANNED",
        "STS-NEEDS-IMPROVEMENT"
      ]
    },
    "verification_status": {
      "type": "string",
      "enum": [
        "VER-NOT-VERIFIED",
        "VER-PASS",
        "VER-FAIL"
      ]
    },
    "effectiveness": {
      "type": "string",
      "enum": [
        "EFF-LOW",
        "EFF-MEDIUM",
        "EFF-HIGH",
        "EFF-UNKNOWN"
      ]
    },
    "exception_status": {
      "type": "string",
      "enum": [
        "EXC-NONE",
        "EXC-NOT-APPLICABLE",
        "EXC-RISK-ACCEPTED",
        "EXC-DEFERRED",
        "EXC-UNAVAILABLE"
      ]
    },
    "exception_approval_date": {
      "type": [
        "string",
        "null"
      ],
      "format": "date"
    },
    "exception_expiry_date": {
      "type": [
        "string",
        "null"
      ],
      "format": "date"
    },
    "review_frequency": {
      "type": [
        "string",
        "null"
      ],
      "enum": [
        "DAILY",
        "WEEKLY",
        "MONTHLY",
        "QUARTERLY",
        "SEMI-ANNUAL",
        "ANNUAL",
        "BIENNIAL",
        "AD-HOC",
        "CONTINUOUS",
        null
      ]
    },
    "last_review_date": {
      "type": [
        "string",
        "null"
      ],
      "format": "date"
    },
    "next_review_date": {
      "type": [
        "string",
        "null"
      ],
      "format": "date"
    },
    "publication_status": {
      "type": "string",
      "enum": [
        "DRAFT",
        "UNDER_REVIEW",
        "APPROVED",
        "PUBLISHED",
        "DEPRECATED",
        "WITHDRAWN"
      ]
    },
    "publication_date": {
      "type": [
        "string",
        "null"
      ],
      "format": "date"
    },
    "effective_date": {
      "type": [
        "string",
        "null"
      ],
      "format": "date"
    },
    "asset_type": {
      "type": [
        "string",
        "null"
      ],
      "enum": [
        "HARDWARE",
        "SOFTWARE",
        "DATA",
        "SERVICE",
        "FACILITY",
        "PERSONNEL",
        "NETWORK",
        "CLOUD_INSTANCE",
        "DOCUMENT",
        "INTELLECTUAL_PROPERTY",
        null
      ]
    },
    "asset_criticality": {
      "type": [
        "string",
        "null"
      ],
      "enum": [
        "CRITICAL",
        "HIGH",
        "MEDIUM",
        "LOW",
        null
      ]
    },
    "required_maturity_level": {
      "type": [
        "string",
        "null"
      ],
      "enum": [
        "INITIAL",
        "REPEATABLE",
        "DEFINED",
        "MANAGED",
        "OPTIMIZED",
        null
      ]
    },
    "cost_category": {
      "type": [
        "string",
        "null"
      ],
      "enum": [
        "LOW",
        "MEDIUM",
        "HIGH",
        "VERY_HIGH",
        null
      ]
    },
    "cost_estimate_currency": {
      "type": [
        "string",
        "null"
      ],
      "pattern": "^[A-Z]{3}$"
    },
    "cost_estimate": {
      "type": [
        "number",
        "null"
      ],
      "minimum": 0
    },
    "cost_estimate_min": {
      "type": [
        "number",
        "null"
      ],
      "minimum": 0
    },
    "cost_estimate_max": {
      "type": [
        "number",
        "null"
      ],
      "minimum": 0
    },
    "effort_estimate": {
      "type": [
        "integer",
        "null"
      ],
      "minimum": 0
    },
    "applicability_scope": {
      "type": [
        "object",
        "null"
      ],
      "properties": {
        "organization_size": {
          "type": "array",
          "items": {
            "type": "string",
            "enum": [
              "SMALL",
              "MEDIUM",
              "LARGE",
              "ENTERPRISE"
            ]
          },
          "uniqueItems": true
        },
        "industry": {
          "type": "array",
          "items": {
            "type": "string",
            "enum": [
              "GENERAL",
              "FINANCE",
              "HEALTHCARE",
              "GOVERNMENT",
              "TECHNOLOGY",
              "RETAIL",
              "ENERGY",
              "EDUCATION",
              "OTHER"
            ]
          },
          "uniqueItems": true
        },
        "geographic_regions": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "uniqueItems": true
        },
        "business_units": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "uniqueItems": true
        },
        "entity_types": {
          "type": "array",
          "items": {
            "type": "string",
            "enum": [
              "LEGAL_ENTITY",
              "DEPARTMENT",
              "TEAM",
              "ROLE"
            ]
          },
          "uniqueItems": true
        },
        "regulatory_scope": {
          "type": "array",
          "items": {
            "type": "string",
            "enum": [
              "GDPR",
              "PCI",
              "HIPAA",
              "NCA",
              "PDPL",
              "OTHER"
            ]
          },
          "uniqueItems": true
        },
        "regulatory_jurisdictions": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "uniqueItems": true
        },
        "exclusions": {
          "type": [
            "string",
            "null"
          ]
        }
      },
      "additionalProperties": false
    },
    "classification_confidence": {
      "type": [
        "number",
        "null"
      ],
      "minimum": 0,
      "maximum": 1
    },
    "classification_rationale": {
      "type": [
        "string",
        "null"
      ],
      "minLength": 1
    },
    "requires_human_review": {
      "type": "boolean"
    },
    "ai_review_status": {
      "type": "string",
      "enum": [
        "AIR-AUTO-ACCEPTED",
        "AIR-HUMAN-REVIEW",
        "AIR-HUMAN-APPROVED",
        "AIR-HUMAN-REJECTED"
      ]
    },
    "import_status": {
      "type": [
        "string",
        "null"
      ],
      "enum": [
        "NEW",
        "IMPORTED",
        "UPDATED",
        "MERGED",
        "CONFLICT",
        "REJECTED",
        null
      ]
    },
    "import_source": {
      "type": [
        "string",
        "null"
      ]
    },
    "import_date": {
      "type": [
        "string",
        "null"
      ],
      "format": "date-time"
    },
    "import_version": {
      "type": [
        "string",
        "null"
      ]
    },
    "self_assessment": {
      "type": [
        "object",
        "null"
      ],
      "properties": {
        "status": {
          "type": "string",
          "enum": [
            "NOT_ASSESSED",
            "IN_PROGRESS",
            "COMPLETED",
            "NEEDS_REVIEW"
          ]
        },
        "score": {
          "type": [
            "integer",
            "null"
          ],
          "minimum": 0,
          "maximum": 100
        },
        "assessment_date": {
          "type": [
            "string",
            "null"
          ],
          "format": "date"
        },
        "assessed_by": {
          "type": [
            "string",
            "null"
          ]
        },
        "comments": {
          "type": [
            "string",
            "null"
          ]
        }
      },
      "required": [
        "status"
      ],
      "additionalProperties": false
    },
    "technical_dependencies": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "dependency_type",
          "dependency_name",
          "dependency_status"
        ],
        "properties": {
          "dependency_type": {
            "type": "string",
            "enum": [
              "SYSTEM",
              "PLATFORM",
              "VENDOR",
              "SKILL",
              "BUDGET"
            ]
          },
          "dependency_name": {
            "type": "string"
          },
          "dependency_status": {
            "type": "string",
            "enum": [
              "AVAILABLE",
              "NOT_AVAILABLE",
              "PARTIAL",
              "PLANNED"
            ]
          }
        },
        "additionalProperties": false
      }
    },
    "verification_tools": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "tool_name",
          "tool_type",
          "verification_method"
        ],
        "properties": {
          "tool_name": {
            "type": "string"
          },
          "tool_type": {
            "type": "string",
            "enum": [
              "SIEM",
              "EDR",
              "IAM",
              "VULNERABILITY",
              "CSPM",
              "MANUAL"
            ]
          },
          "verification_method": {
            "type": "string",
            "enum": [
              "API",
              "LOG",
              "REPORT",
              "INTERVIEW",
              "OBSERVATION"
            ]
          }
        },
        "additionalProperties": false
      }
    },
    "stakeholders": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "role",
          "responsibility"
        ],
        "properties": {
          "role": {
            "type": "string"
          },
          "responsibility": {
            "type": "string",
            "enum": [
              "OWNER",
              "REVIEWER",
              "APPROVER",
              "CONSULTED",
              "INFORMED"
            ]
          }
        },
        "additionalProperties": false
      }
    },
    "remediation_actions": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "action",
          "priority",
          "responsible_role"
        ],
        "properties": {
          "action": {
            "type": "string"
          },
          "priority": {
            "type": "string",
            "enum": [
              "PRI-CRITICAL",
              "PRI-HIGH",
              "PRI-MEDIUM",
              "PRI-LOW"
            ]
          },
          "effort_estimate": {
            "type": [
              "integer",
              "null"
            ],
            "minimum": 0
          },
          "responsible_role": {
            "type": "string"
          }
        },
        "additionalProperties": false
      }
    },
    "external_references": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "type",
          "title"
        ],
        "properties": {
          "type": {
            "type": "string",
            "enum": [
              "ARTICLE",
              "BLOG",
              "TOOL",
              "VIDEO",
              "STUDY",
              "BENCHMARK"
            ]
          },
          "title": {
            "type": "string"
          },
          "url": {
            "type": [
              "string",
              "null"
            ],
            "format": "uri"
          },
          "description": {
            "type": [
              "string",
              "null"
            ]
          }
        },
        "additionalProperties": false
      }
    },
    "tags": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "tag_type",
          "tag_value"
        ],
        "properties": {
          "tag_type": {
            "type": "string",
            "enum": [
              "Technology",
              "Framework",
              "Concept",
              "Context",
              "Threat",
              "Data",
              "Party"
            ]
          },
          "tag_value": {
            "type": "string"
          }
        },
        "additionalProperties": false
      }
    },
    "framework_mappings": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "framework",
          "version",
          "reference",
          "mapping_strength"
        ],
        "properties": {
          "framework": {
            "type": "string"
          },
          "version": {
            "type": "string"
          },
          "reference": {
            "type": "string"
          },
          "category": {
            "type": [
              "string",
              "null"
            ]
          },
          "mapping_strength": {
            "type": "string",
            "enum": [
              "DIRECT",
              "INDIRECT",
              "PARTIAL",
              "INFORMATIVE"
            ]
          },
          "rationale": {
            "type": [
              "string",
              "null"
            ],
            "minLength": 1
          }
        },
        "allOf": [
          {
            "if": {
              "properties": {
                "mapping_strength": {
                  "not": {
                    "const": "DIRECT"
                  }
                }
              },
              "required": [
                "mapping_strength"
              ]
            },
            "then": {
              "required": [
                "rationale"
              ],
              "properties": {
                "rationale": {
                  "type": "string",
                  "minLength": 1
                }
              }
            }
          }
        ],
        "additionalProperties": false
      }
    },
    "relationships": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "type",
          "target_id"
        ],
        "properties": {
          "type": {
            "type": "string",
            "enum": [
              "REL-DER",
              "REL-SAT",
              "REL-SUP",
              "REL-SPL",
              "REL-IMP",
              "REL-VER",
              "REL-MEA",
              "REL-MIT",
              "REL-AFF",
              "REL-EXC",
              "REL-DEP",
              "REL-CNF"
            ]
          },
          "target_id": {
            "type": "string"
          },
          "description": {
            "type": [
              "string",
              "null"
            ]
          },
          "resolution_note": {
            "type": [
              "string",
              "null"
            ]
          },
          "resolution_status": {
            "type": [
              "string",
              "null"
            ],
            "enum": [
              "PENDING",
              "RESOLVED",
              "ACCEPTED",
              "REJECTED",
              null
            ]
          },
          "resolution_date": {
            "type": [
              "string",
              "null"
            ],
            "format": "date"
          },
          "resolved_by": {
            "type": [
              "string",
              "null"
            ]
          }
        },
        "allOf": [
          {
            "if": {
              "properties": {
                "type": {
                  "const": "REL-CNF"
                }
              },
              "required": [
                "type"
              ]
            },
            "then": {
              "required": [
                "resolution_status",
                "resolution_note"
              ],
              "properties": {
                "resolution_status": {
                  "type": "string",
                  "enum": [
                    "PENDING",
                    "RESOLVED",
                    "ACCEPTED",
                    "REJECTED"
                  ]
                },
                "resolution_note": {
                  "type": "string",
                  "minLength": 1
                }
              }
            }
          }
        ],
        "additionalProperties": false
      }
    },
    "source_document": {
      "type": "string"
    },
    "source_section": {
      "type": [
        "string",
        "null"
      ]
    },
    "extraction_date": {
      "type": [
        "string",
        "null"
      ],
      "format": "date"
    },
    "created_at": {
      "type": [
        "string",
        "null"
      ],
      "format": "date-time"
    },
    "updated_at": {
      "type": [
        "string",
        "null"
      ],
      "format": "date-time"
    },
    "version": {
      "type": "integer",
      "minimum": 1
    },
    "is_custom": {
      "type": "boolean"
    },
    "is_active": {
      "type": "boolean"
    }
  },
  "allOf": [
    {
      "if": {
        "properties": {
          "sub_domain": {
            "pattern": "^SD-01\\."
          }
        },
        "required": [
          "sub_domain"
        ]
      },
      "then": {
        "properties": {
          "primary_domain": {
            "const": "SD-01"
          }
        }
      }
    },
    {
      "if": {
        "properties": {
          "sub_domain": {
            "pattern": "^SD-02\\."
          }
        },
        "required": [
          "sub_domain"
        ]
      },
      "then": {
        "properties": {
          "primary_domain": {
            "const": "SD-02"
          }
        }
      }
    },
    {
      "if": {
        "properties": {
          "sub_domain": {
            "pattern": "^SD-03\\."
          }
        },
        "required": [
          "sub_domain"
        ]
      },
      "then": {
        "properties": {
          "primary_domain": {
            "const": "SD-03"
          }
        }
      }
    },
    {
      "if": {
        "properties": {
          "sub_domain": {
            "pattern": "^SD-04\\."
          }
        },
        "required": [
          "sub_domain"
        ]
      },
      "then": {
        "properties": {
          "primary_domain": {
            "const": "SD-04"
          }
        }
      }
    },
    {
      "if": {
        "properties": {
          "sub_domain": {
            "pattern": "^SD-05\\."
          }
        },
        "required": [
          "sub_domain"
        ]
      },
      "then": {
        "properties": {
          "primary_domain": {
            "const": "SD-05"
          }
        }
      }
    },
    {
      "if": {
        "properties": {
          "sub_domain": {
            "pattern": "^SD-06\\."
          }
        },
        "required": [
          "sub_domain"
        ]
      },
      "then": {
        "properties": {
          "primary_domain": {
            "const": "SD-06"
          }
        }
      }
    },
    {
      "if": {
        "properties": {
          "sub_domain": {
            "pattern": "^SD-07\\."
          }
        },
        "required": [
          "sub_domain"
        ]
      },
      "then": {
        "properties": {
          "primary_domain": {
            "const": "SD-07"
          }
        }
      }
    },
    {
      "if": {
        "properties": {
          "sub_domain": {
            "pattern": "^SD-08\\."
          }
        },
        "required": [
          "sub_domain"
        ]
      },
      "then": {
        "properties": {
          "primary_domain": {
            "const": "SD-08"
          }
        }
      }
    },
    {
      "if": {
        "properties": {
          "type": {
            "enum": [
              "ART-CTR",
              "ART-CTE"
            ]
          }
        },
        "required": [
          "type"
        ]
      },
      "then": {
        "required": [
          "control_nature",
          "control_function",
          "testability"
        ],
        "properties": {
          "control_nature": {
            "type": "string",
            "enum": [
              "NAT-ORG",
              "NAT-HUM",
              "NAT-PHY",
              "NAT-TEC"
            ]
          },
          "control_function": {
            "type": "string",
            "enum": [
              "FUN-PRE",
              "FUN-DET",
              "FUN-COR",
              "FUN-REC",
              "FUN-DRR",
              "FUN-COM"
            ]
          },
          "testability": {
            "type": "string",
            "enum": [
              "TST-AUTO",
              "TST-MAN",
              "TST-DOC",
              "TST-INT",
              "TST-NA"
            ]
          }
        }
      }
    },
    {
      "if": {
        "properties": {
          "type": {
            "const": "ART-REQ"
          }
        },
        "required": [
          "type"
        ]
      },
      "then": {
        "required": [
          "requirement_type"
        ],
        "properties": {
          "requirement_type": {
            "type": "string",
            "enum": [
              "RQT-GOV",
              "RQT-REG",
              "RQT-LEG",
              "RQT-CON",
              "RQT-STD",
              "RQT-INT",
              "RQT-RSK"
            ]
          }
        }
      }
    },
    {
      "if": {
        "properties": {
          "type": {
            "const": "ART-EXC"
          }
        },
        "required": [
          "type"
        ]
      },
      "then": {
        "required": [
          "exception_approval_date",
          "exception_expiry_date"
        ],
        "properties": {
          "exception_approval_date": {
            "type": "string",
            "format": "date"
          },
          "exception_expiry_date": {
            "type": "string",
            "format": "date"
          }
        }
      }
    },
    {
      "if": {
        "properties": {
          "type": {
            "const": "ART-AST"
          }
        },
        "required": [
          "type"
        ]
      },
      "then": {
        "required": [
          "asset_type",
          "asset_criticality"
        ],
        "properties": {
          "asset_type": {
            "type": "string",
            "enum": [
              "HARDWARE",
              "SOFTWARE",
              "DATA",
              "SERVICE",
              "FACILITY",
              "PERSONNEL",
              "NETWORK",
              "CLOUD_INSTANCE",
              "DOCUMENT",
              "INTELLECTUAL_PROPERTY"
            ]
          },
          "asset_criticality": {
            "type": "string",
            "enum": [
              "CRITICAL",
              "HIGH",
              "MEDIUM",
              "LOW"
            ]
          }
        }
      }
    },
    {
      "if": {
        "properties": {
          "type": {
            "const": "ART-RSK"
          }
        },
        "required": [
          "type"
        ]
      },
      "then": {
        "required": [
          "remediation_actions"
        ],
        "properties": {
          "remediation_actions": {
            "minItems": 1
          }
        }
      }
    },
    {
      "if": {
        "properties": {
          "classification_confidence": {
            "type": "number",
            "maximum": 0.7
          }
        },
        "required": [
          "classification_confidence"
        ]
      },
      "then": {
        "properties": {
          "requires_human_review": {
            "const": true
          },
          "ai_review_status": {
            "const": "AIR-HUMAN-REVIEW"
          }
        }
      }
    },
    {
      "if": {
        "properties": {
          "classification_confidence": {
            "type": "number"
          }
        },
        "required": [
          "classification_confidence"
        ]
      },
      "then": {
        "required": [
          "classification_rationale"
        ],
        "properties": {
          "classification_rationale": {
            "type": "string",
            "minLength": 1
          }
        }
      }
    },
    {
      "if": {
        "properties": {
          "review_frequency": {
            "type": "string",
            "not": {
              "const": "AD-HOC"
            }
          }
        },
        "required": [
          "review_frequency"
        ]
      },
      "then": {
        "required": [
          "next_review_date"
        ],
        "properties": {
          "next_review_date": {
            "type": "string",
            "format": "date"
          }
        }
      }
    },
    {
      "if": {
        "properties": {
          "type": {
            "enum": [
              "ART-POL",
              "ART-STD",
              "ART-PRC"
            ]
          },
          "publication_status": {
            "const": "PUBLISHED"
          }
        },
        "required": [
          "type",
          "publication_status"
        ]
      },
      "then": {
        "required": [
          "effective_date"
        ],
        "properties": {
          "effective_date": {
            "type": "string",
            "format": "date"
          }
        }
      }
    },
    {
      "if": {
        "properties": {
          "priority": {
            "const": "PRI-CRITICAL"
          }
        },
        "required": [
          "priority"
        ]
      },
      "then": {
        "properties": {
          "priority_weight": {
            "const": 10
          }
        }
      }
    },
    {
      "if": {
        "properties": {
          "priority": {
            "const": "PRI-HIGH"
          }
        },
        "required": [
          "priority"
        ]
      },
      "then": {
        "properties": {
          "priority_weight": {
            "const": 7
          }
        }
      }
    },
    {
      "if": {
        "properties": {
          "priority": {
            "const": "PRI-MEDIUM"
          }
        },
        "required": [
          "priority"
        ]
      },
      "then": {
        "properties": {
          "priority_weight": {
            "const": 4
          }
        }
      }
    },
    {
      "if": {
        "properties": {
          "priority": {
            "const": "PRI-LOW"
          }
        },
        "required": [
          "priority"
        ]
      },
      "then": {
        "properties": {
          "priority_weight": {
            "const": 1
          }
        }
      }
    },
    {
      "if": {
        "properties": {
          "cost_estimate_min": {
            "type": "number"
          },
          "cost_estimate_max": {
            "type": "number"
          }
        },
        "required": [
          "cost_estimate_min",
          "cost_estimate_max"
        ]
      },
      "then": {
        "properties": {
          "cost_estimate_max": {
            "minimum": 0
          }
        }
      }
    }
  ],
  "additionalProperties": false
}
```


## 8. Normative SQLite Data Model

SQLite is the normative storage model for mobile and embedded deployments. Repeatable structures are normalized into child tables; `security_artifacts` must not store `applicability_scope_json`, `self_assessment_json`, or other duplicated array JSON columns.

```sql

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS security_artifacts (
    id TEXT PRIMARY KEY,
    source_artifact_id TEXT,
    temp_id TEXT,
    type TEXT NOT NULL,
    title_en TEXT NOT NULL,
    title_ar TEXT,
    description_en TEXT,
    description_ar TEXT,
    primary_domain TEXT NOT NULL,
    sub_domain TEXT NOT NULL,
    abstraction_level TEXT NOT NULL,
    source TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_location TEXT,
    obligation_level TEXT NOT NULL,
    requirement_type TEXT,
    granularity_level TEXT NOT NULL,
    control_nature TEXT,
    control_function TEXT,
    testability TEXT,
    scope TEXT,
    owner_role TEXT,
    priority TEXT NOT NULL DEFAULT 'PRI-MEDIUM',
    priority_weight INTEGER NOT NULL DEFAULT 4,
    implementation_status TEXT NOT NULL DEFAULT 'STS-NOT-APPLIED',
    verification_status TEXT NOT NULL DEFAULT 'VER-NOT-VERIFIED',
    effectiveness TEXT NOT NULL DEFAULT 'EFF-UNKNOWN',
    exception_status TEXT NOT NULL DEFAULT 'EXC-NONE',
    exception_approval_date TEXT,
    exception_expiry_date TEXT,
    review_frequency TEXT,
    last_review_date TEXT,
    next_review_date TEXT,
    publication_status TEXT NOT NULL DEFAULT 'DRAFT',
    publication_date TEXT,
    effective_date TEXT,
    asset_type TEXT,
    asset_criticality TEXT,
    required_maturity_level TEXT,
    cost_category TEXT,
    cost_estimate_currency TEXT,
    cost_estimate REAL,
    cost_estimate_min REAL,
    cost_estimate_max REAL,
    effort_estimate INTEGER,
    classification_confidence REAL,
    classification_rationale TEXT,
    ai_review_status TEXT NOT NULL DEFAULT 'AIR-HUMAN-REVIEW',
    requires_human_review INTEGER NOT NULL DEFAULT 1,
    import_status TEXT,
    import_source TEXT,
    import_date TEXT,
    import_version TEXT,
    source_document TEXT NOT NULL,
    source_section TEXT,
    extraction_date TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    version INTEGER NOT NULL DEFAULT 1,
    is_custom INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    CHECK (type IN ('ART-REQ','ART-OBJ','ART-PRI','ART-POL','ART-STD','ART-CTR','ART-CTE','ART-PRO','ART-PRC','ART-PRG','ART-PLN','ART-TSK','ART-CFG','ART-RUL','ART-EVD','ART-MET','ART-EXC','ART-RSK','ART-AST','ART-THR','ART-VUL','ART-OWN')),
    CHECK (primary_domain IN ('SD-01','SD-02','SD-03','SD-04','SD-05','SD-06','SD-07','SD-08')),
    CHECK (sub_domain GLOB 'SD-0[1-8].0[1-5]' AND substr(sub_domain,1,5) = primary_domain),
    CHECK (abstraction_level IN ('ABS-GOV','ABS-RIS','ABS-POL','ABS-CTR','ABS-PRO','ABS-TEC','ABS-EVM')),
    CHECK (source IN ('SRC-REG','SRC-LEG','SRC-CON','SRC-STD','SRC-INT','SRC-BST','SRC-RSK')),
    CHECK (source_type IN ('DOCUMENT','SYSTEM','TOOL','INTERVIEW','OBSERVATION','STANDARD','REGULATION')),
    CHECK (obligation_level IN ('OBL-MND','OBL-CON','OBL-REC','OBL-OPT')),
    CHECK (type <> 'ART-REQ' OR requirement_type IN ('RQT-GOV','RQT-REG','RQT-LEG','RQT-CON','RQT-STD','RQT-INT','RQT-RSK')),
    CHECK (type = 'ART-REQ' OR requirement_type IS NULL),
    CHECK (granularity_level IN ('GRN-HIGH','GRN-MEDIUM','GRN-DETAILED','GRN-EXECUTABLE','GRN-TECHNICAL','GRN-EVIDENTIARY','GRN-METRIC')),
    CHECK (type NOT IN ('ART-CTR','ART-CTE') OR (control_nature IN ('NAT-ORG','NAT-HUM','NAT-PHY','NAT-TEC') AND control_function IN ('FUN-PRE','FUN-DET','FUN-COR','FUN-REC','FUN-DRR','FUN-COM') AND testability IN ('TST-AUTO','TST-MAN','TST-DOC','TST-INT','TST-NA'))),
    CHECK (priority IN ('PRI-CRITICAL','PRI-HIGH','PRI-MEDIUM','PRI-LOW')),
    CHECK ((priority = 'PRI-CRITICAL' AND priority_weight = 10) OR (priority = 'PRI-HIGH' AND priority_weight = 7) OR (priority = 'PRI-MEDIUM' AND priority_weight = 4) OR (priority = 'PRI-LOW' AND priority_weight = 1)),
    CHECK (implementation_status IN ('STS-NOT-APPLIED','STS-PARTIAL','STS-FULL','STS-PLANNED','STS-NEEDS-IMPROVEMENT')),
    CHECK (verification_status IN ('VER-NOT-VERIFIED','VER-PASS','VER-FAIL')),
    CHECK (effectiveness IN ('EFF-LOW','EFF-MEDIUM','EFF-HIGH','EFF-UNKNOWN')),
    CHECK (exception_status IN ('EXC-NONE','EXC-NOT-APPLICABLE','EXC-RISK-ACCEPTED','EXC-DEFERRED','EXC-UNAVAILABLE')),
    CHECK (type <> 'ART-EXC' OR (exception_approval_date IS NOT NULL AND exception_expiry_date IS NOT NULL)),
    CHECK (review_frequency IS NULL OR review_frequency IN ('DAILY','WEEKLY','MONTHLY','QUARTERLY','SEMI-ANNUAL','ANNUAL','BIENNIAL','AD-HOC','CONTINUOUS')),
    CHECK (review_frequency IS NULL OR review_frequency = 'AD-HOC' OR next_review_date IS NOT NULL),
    CHECK (publication_status IN ('DRAFT','UNDER_REVIEW','APPROVED','PUBLISHED','DEPRECATED','WITHDRAWN')),
    CHECK (type NOT IN ('ART-POL','ART-STD','ART-PRC') OR publication_status <> 'PUBLISHED' OR effective_date IS NOT NULL),
    CHECK (type <> 'ART-AST' OR (asset_type IN ('HARDWARE','SOFTWARE','DATA','SERVICE','FACILITY','PERSONNEL','NETWORK','CLOUD_INSTANCE','DOCUMENT','INTELLECTUAL_PROPERTY') AND asset_criticality IN ('CRITICAL','HIGH','MEDIUM','LOW'))),
    CHECK (required_maturity_level IS NULL OR required_maturity_level IN ('INITIAL','REPEATABLE','DEFINED','MANAGED','OPTIMIZED')),
    CHECK (cost_category IS NULL OR cost_category IN ('LOW','MEDIUM','HIGH','VERY_HIGH')),
    CHECK (cost_estimate_currency IS NULL OR cost_estimate_currency GLOB '[A-Z][A-Z][A-Z]'),
    CHECK (cost_estimate IS NULL OR cost_estimate >= 0),
    CHECK (cost_estimate_min IS NULL OR cost_estimate_min >= 0),
    CHECK (cost_estimate_max IS NULL OR cost_estimate_max >= 0),
    CHECK (cost_estimate_min IS NULL OR cost_estimate_max IS NULL OR cost_estimate_max >= cost_estimate_min),
    CHECK (effort_estimate IS NULL OR effort_estimate >= 0),
    CHECK (classification_confidence IS NULL OR (classification_confidence >= 0 AND classification_confidence <= 1)),
    CHECK (classification_confidence IS NULL OR classification_rationale IS NOT NULL),
    CHECK (classification_confidence IS NULL OR classification_confidence > 0.70 OR (requires_human_review = 1 AND ai_review_status = 'AIR-HUMAN-REVIEW')),
    CHECK (ai_review_status IN ('AIR-AUTO-ACCEPTED','AIR-HUMAN-REVIEW','AIR-HUMAN-APPROVED','AIR-HUMAN-REJECTED')),
    CHECK (requires_human_review IN (0,1)),
    CHECK (import_status IS NULL OR import_status IN ('NEW','IMPORTED','UPDATED','MERGED','CONFLICT','REJECTED')),
    CHECK (is_custom IN (0,1)),
    CHECK (is_active IN (0,1))
);

CREATE TABLE IF NOT EXISTS artifact_tags (
    artifact_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    tag_type TEXT NOT NULL,
    tag_value TEXT NOT NULL,
    PRIMARY KEY (artifact_id, tag_type, tag_value),
    CHECK (tag_type IN ('Technology','Framework','Concept','Context','Threat','Data','Party'))
);

CREATE TABLE IF NOT EXISTS artifact_relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    target_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE RESTRICT,
    relation_type TEXT NOT NULL,
    description TEXT,
    resolution_note TEXT,
    resolution_status TEXT,
    resolution_date TEXT,
    resolved_by TEXT,
    owner_role TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (source_id, target_id, relation_type),
    CHECK (relation_type IN ('REL-DER','REL-SAT','REL-SUP','REL-SPL','REL-IMP','REL-VER','REL-MEA','REL-MIT','REL-AFF','REL-EXC','REL-DEP','REL-CNF')),
    CHECK (resolution_status IS NULL OR resolution_status IN ('PENDING','RESOLVED','ACCEPTED','REJECTED')),
    CHECK (relation_type <> 'REL-CNF' OR (resolution_status IS NOT NULL AND resolution_note IS NOT NULL))
);

CREATE TABLE IF NOT EXISTS framework_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    framework TEXT NOT NULL,
    version TEXT NOT NULL,
    reference TEXT NOT NULL,
    category TEXT,
    mapping_strength TEXT NOT NULL DEFAULT 'DIRECT',
    rationale TEXT,
    UNIQUE (artifact_id, framework, version, reference),
    CHECK (mapping_strength IN ('DIRECT','INDIRECT','PARTIAL','INFORMATIVE')),
    CHECK (mapping_strength = 'DIRECT' OR (rationale IS NOT NULL AND length(trim(rationale)) > 0))
);

CREATE TABLE IF NOT EXISTS artifact_applicability_scope (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    scope_type TEXT NOT NULL,
    scope_value TEXT NOT NULL,
    UNIQUE (artifact_id, scope_type, scope_value),
    CHECK (scope_type IN ('ORGANIZATION_SIZE','INDUSTRY','GEOGRAPHIC_REGION','BUSINESS_UNIT','ENTITY_TYPE','REGULATORY_SCOPE','REGULATORY_JURISDICTION','EXCLUSION'))
);

CREATE TABLE IF NOT EXISTS artifact_self_assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'NOT_ASSESSED',
    score INTEGER,
    assessment_date TEXT,
    assessed_by TEXT,
    comments TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    CHECK (status IN ('NOT_ASSESSED','IN_PROGRESS','COMPLETED','NEEDS_REVIEW')),
    CHECK (score IS NULL OR (score >= 0 AND score <= 100))
);

CREATE TABLE IF NOT EXISTS technical_dependencies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    dependency_type TEXT NOT NULL,
    dependency_name TEXT NOT NULL,
    dependency_status TEXT NOT NULL,
    CHECK (dependency_type IN ('SYSTEM','PLATFORM','VENDOR','SKILL','BUDGET')),
    CHECK (dependency_status IN ('AVAILABLE','NOT_AVAILABLE','PARTIAL','PLANNED'))
);

CREATE TABLE IF NOT EXISTS verification_tools (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    tool_name TEXT NOT NULL,
    tool_type TEXT NOT NULL,
    verification_method TEXT NOT NULL,
    CHECK (tool_type IN ('SIEM','EDR','IAM','VULNERABILITY','CSPM','MANUAL')),
    CHECK (verification_method IN ('API','LOG','REPORT','INTERVIEW','OBSERVATION'))
);

CREATE TABLE IF NOT EXISTS stakeholders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    responsibility TEXT NOT NULL,
    CHECK (responsibility IN ('OWNER','REVIEWER','APPROVER','CONSULTED','INFORMED'))
);

CREATE TABLE IF NOT EXISTS remediation_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    action TEXT NOT NULL,
    priority TEXT NOT NULL,
    effort_estimate INTEGER,
    responsible_role TEXT NOT NULL,
    CHECK (priority IN ('PRI-CRITICAL','PRI-HIGH','PRI-MEDIUM','PRI-LOW')),
    CHECK (effort_estimate IS NULL OR effort_estimate >= 0)
);

CREATE TABLE IF NOT EXISTS external_references (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT,
    description TEXT,
    CHECK (type IN ('ARTICLE','BLOG','TOOL','VIDEO','STUDY','BENCHMARK'))
);

CREATE INDEX IF NOT EXISTS idx_artifacts_type ON security_artifacts(type);
CREATE INDEX IF NOT EXISTS idx_artifacts_domain ON security_artifacts(primary_domain, sub_domain);
CREATE INDEX IF NOT EXISTS idx_artifacts_status ON security_artifacts(implementation_status, verification_status, effectiveness);
CREATE INDEX IF NOT EXISTS idx_artifacts_priority ON security_artifacts(priority, priority_weight);
CREATE INDEX IF NOT EXISTS idx_artifacts_review ON security_artifacts(next_review_date, review_frequency);
CREATE INDEX IF NOT EXISTS idx_artifacts_publication ON security_artifacts(publication_status, effective_date);
CREATE INDEX IF NOT EXISTS idx_artifacts_exception ON security_artifacts(exception_status, exception_expiry_date);
CREATE INDEX IF NOT EXISTS idx_artifacts_maturity ON security_artifacts(required_maturity_level);
CREATE INDEX IF NOT EXISTS idx_artifacts_ai_review ON security_artifacts(ai_review_status, requires_human_review);
CREATE INDEX IF NOT EXISTS idx_artifacts_import ON security_artifacts(import_status, import_source);
CREATE INDEX IF NOT EXISTS idx_tags_value ON artifact_tags(tag_type, tag_value);
CREATE INDEX IF NOT EXISTS idx_scope ON artifact_applicability_scope(scope_type, scope_value);
CREATE INDEX IF NOT EXISTS idx_self_assessment ON artifact_self_assessments(status, score);
CREATE INDEX IF NOT EXISTS idx_rel_source ON artifact_relationships(source_id);
CREATE INDEX IF NOT EXISTS idx_rel_target ON artifact_relationships(target_id);
CREATE INDEX IF NOT EXISTS idx_mapping_ref ON framework_mappings(framework, version, reference);

```


## 9. SQLite Migration Script from v2.1.1/v2.2.0

This script is additive for existing deployments. For strict enforcement of new `CHECK` constraints, rebuild the table into the normative v2.2.1 schema during a controlled maintenance migration. The migration now creates all auxiliary tables used by the normalized model.

```sql

PRAGMA foreign_keys = OFF;
BEGIN TRANSACTION;

-- Additive columns for v2.2.1. Existing SQLite deployments should ignore duplicate-column errors if rerun by a migration runner.
ALTER TABLE security_artifacts ADD COLUMN source_artifact_id TEXT;
ALTER TABLE security_artifacts ADD COLUMN temp_id TEXT;
ALTER TABLE security_artifacts ADD COLUMN source_type TEXT DEFAULT 'DOCUMENT';
ALTER TABLE security_artifacts ADD COLUMN source_location TEXT;
ALTER TABLE security_artifacts ADD COLUMN priority_weight INTEGER DEFAULT 4;
ALTER TABLE security_artifacts ADD COLUMN exception_approval_date TEXT;
ALTER TABLE security_artifacts ADD COLUMN exception_expiry_date TEXT;
ALTER TABLE security_artifacts ADD COLUMN review_frequency TEXT;
ALTER TABLE security_artifacts ADD COLUMN last_review_date TEXT;
ALTER TABLE security_artifacts ADD COLUMN next_review_date TEXT;
ALTER TABLE security_artifacts ADD COLUMN publication_status TEXT DEFAULT 'DRAFT';
ALTER TABLE security_artifacts ADD COLUMN publication_date TEXT;
ALTER TABLE security_artifacts ADD COLUMN effective_date TEXT;
ALTER TABLE security_artifacts ADD COLUMN asset_type TEXT;
ALTER TABLE security_artifacts ADD COLUMN asset_criticality TEXT;
ALTER TABLE security_artifacts ADD COLUMN required_maturity_level TEXT;
ALTER TABLE security_artifacts ADD COLUMN cost_category TEXT;
ALTER TABLE security_artifacts ADD COLUMN cost_estimate_currency TEXT;
ALTER TABLE security_artifacts ADD COLUMN cost_estimate REAL;
ALTER TABLE security_artifacts ADD COLUMN cost_estimate_min REAL;
ALTER TABLE security_artifacts ADD COLUMN cost_estimate_max REAL;
ALTER TABLE security_artifacts ADD COLUMN effort_estimate INTEGER;
ALTER TABLE security_artifacts ADD COLUMN import_status TEXT;
ALTER TABLE security_artifacts ADD COLUMN import_source TEXT;
ALTER TABLE security_artifacts ADD COLUMN import_date TEXT;
ALTER TABLE security_artifacts ADD COLUMN import_version TEXT;

-- Rebuild into the normative v2.2.1 schema during controlled production migration to enforce new CHECK constraints.

CREATE TABLE IF NOT EXISTS artifact_applicability_scope (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    scope_type TEXT NOT NULL,
    scope_value TEXT NOT NULL,
    UNIQUE (artifact_id, scope_type, scope_value),
    CHECK (scope_type IN ('ORGANIZATION_SIZE','INDUSTRY','GEOGRAPHIC_REGION','BUSINESS_UNIT','ENTITY_TYPE','REGULATORY_SCOPE','REGULATORY_JURISDICTION','EXCLUSION'))
);

CREATE TABLE IF NOT EXISTS artifact_self_assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'NOT_ASSESSED',
    score INTEGER,
    assessment_date TEXT,
    assessed_by TEXT,
    comments TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    CHECK (status IN ('NOT_ASSESSED','IN_PROGRESS','COMPLETED','NEEDS_REVIEW')),
    CHECK (score IS NULL OR (score >= 0 AND score <= 100))
);

CREATE TABLE IF NOT EXISTS technical_dependencies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    dependency_type TEXT NOT NULL,
    dependency_name TEXT NOT NULL,
    dependency_status TEXT NOT NULL,
    CHECK (dependency_type IN ('SYSTEM','PLATFORM','VENDOR','SKILL','BUDGET')),
    CHECK (dependency_status IN ('AVAILABLE','NOT_AVAILABLE','PARTIAL','PLANNED'))
);

CREATE TABLE IF NOT EXISTS verification_tools (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    tool_name TEXT NOT NULL,
    tool_type TEXT NOT NULL,
    verification_method TEXT NOT NULL,
    CHECK (tool_type IN ('SIEM','EDR','IAM','VULNERABILITY','CSPM','MANUAL')),
    CHECK (verification_method IN ('API','LOG','REPORT','INTERVIEW','OBSERVATION'))
);

CREATE TABLE IF NOT EXISTS stakeholders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    responsibility TEXT NOT NULL,
    CHECK (responsibility IN ('OWNER','REVIEWER','APPROVER','CONSULTED','INFORMED'))
);

CREATE TABLE IF NOT EXISTS remediation_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    action TEXT NOT NULL,
    priority TEXT NOT NULL,
    effort_estimate INTEGER,
    responsible_role TEXT NOT NULL,
    CHECK (priority IN ('PRI-CRITICAL','PRI-HIGH','PRI-MEDIUM','PRI-LOW')),
    CHECK (effort_estimate IS NULL OR effort_estimate >= 0)
);

CREATE TABLE IF NOT EXISTS external_references (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT,
    description TEXT,
    CHECK (type IN ('ARTICLE','BLOG','TOOL','VIDEO','STUDY','BENCHMARK'))
);

UPDATE security_artifacts SET implementation_status = 'STS-NOT-APPLIED' WHERE implementation_status = 'STS-NA';
UPDATE security_artifacts SET implementation_status = 'STS-PARTIAL' WHERE implementation_status = 'STS-PART';
UPDATE security_artifacts SET implementation_status = 'STS-PLANNED' WHERE implementation_status = 'STS-PLAN';
UPDATE security_artifacts SET implementation_status = 'STS-NEEDS-IMPROVEMENT' WHERE implementation_status = 'STS-NI';
UPDATE security_artifacts SET exception_status = 'EXC-NONE' WHERE exception_status = 'EXC-NON';
UPDATE security_artifacts SET exception_status = 'EXC-UNAVAILABLE' WHERE exception_status = 'EXC-NA';
UPDATE security_artifacts SET exception_status = 'EXC-RISK-ACCEPTED' WHERE exception_status = 'EXC-RA';
UPDATE security_artifacts SET exception_status = 'EXC-DEFERRED' WHERE exception_status = 'EXC-DEF';
UPDATE security_artifacts SET effectiveness = 'EFF-HIGH' WHERE effectiveness = 'EFF-HGH';
UPDATE security_artifacts SET effectiveness = 'EFF-UNKNOWN' WHERE effectiveness = 'EFF-UNK';
UPDATE security_artifacts SET verification_status = 'VER-NOT-VERIFIED' WHERE verification_status = 'VER-NA';
UPDATE security_artifacts SET priority = 'PRI-CRITICAL' WHERE priority = 'PRI-CRIT';
UPDATE security_artifacts SET priority = 'PRI-MEDIUM' WHERE priority = 'PRI-MED';
UPDATE security_artifacts SET priority_weight = CASE priority WHEN 'PRI-CRITICAL' THEN 10 WHEN 'PRI-HIGH' THEN 7 WHEN 'PRI-MEDIUM' THEN 4 WHEN 'PRI-LOW' THEN 1 ELSE 4 END;
UPDATE security_artifacts SET ai_review_status = 'AIR-HUMAN-REVIEW' WHERE ai_review_status IS NULL;
UPDATE security_artifacts SET requires_human_review = 1 WHERE classification_confidence IS NOT NULL AND classification_confidence <= 0.70;
UPDATE security_artifacts SET ai_review_status = 'AIR-HUMAN-REVIEW' WHERE classification_confidence IS NOT NULL AND classification_confidence <= 0.70;

ALTER TABLE framework_mappings ADD COLUMN mapping_strength TEXT DEFAULT 'DIRECT';
UPDATE framework_mappings SET mapping_strength = 'DIRECT' WHERE mapping_strength IS NULL;

CREATE INDEX IF NOT EXISTS idx_artifacts_publication ON security_artifacts(publication_status, effective_date);
CREATE INDEX IF NOT EXISTS idx_artifacts_exception ON security_artifacts(exception_status, exception_expiry_date);
CREATE INDEX IF NOT EXISTS idx_artifacts_maturity ON security_artifacts(required_maturity_level);
CREATE INDEX IF NOT EXISTS idx_scope ON artifact_applicability_scope(scope_type, scope_value);
CREATE INDEX IF NOT EXISTS idx_self_assessment ON artifact_self_assessments(status, score);

COMMIT;
PRAGMA foreign_keys = ON;

```


## 10. AI Classification Workflow

| Step | Owner | Input | Output | Error Handling |
|---|---|---|---|---|
| 1. Extract candidate artifact | AI | Source text and metadata | Candidate title, source, section, original text, `temp_id` | If extraction is ambiguous, create draft with `AIR-HUMAN-REVIEW`. |
| 2. Determine artifact type | AI | Candidate text | One ART-* code | If multiple types are plausible, store alternatives and route to review. |
| 3. Determine requirement type | AI/Human | Candidate ART-REQ artifact | One RQT-* code | Required for ART-REQ; reject record if missing. |
| 4. Determine abstraction level | AI | Artifact type and content | One ABS-* code | Route to review if confidence is below threshold. |
| 5. Classify domain | AI | Artifact text and SDT rules | `primary_domain`, `sub_domain`, rationale | Apply tie-breakers; record rejected alternatives. |
| 6. Assign obligation and lifecycle fields | AI/Human | Source, publication status, context | SRC, source_type, OBL, publication_status, review dates | If source evidence is weak, keep draft and route to review. |
| 7. Assign operational status fields | AI/Human | Implementation data | implementation, verification, effectiveness, exception status | If operational status is unknown, use explicit unknown values only where allowed. |
| 8. Produce rationale | AI | Classification decisions | Plain English rationale | Reject AI-generated record if rationale is empty. |
| 9. Apply confidence threshold | System | confidence score | ai_review_status and requires_human_review | Confidence <= 0.70 must route to human review. |
| 10. Create relationships and mappings | AI/Human | Artifact graph context | REL-* and framework mappings | Reject relationships to missing artifacts; non-DIRECT mappings require rationale. |
| 11. Validate schema and SQLite constraints | System | Complete artifact record | Pass/fail validation result | Reject invalid enum values, inconsistent domain/sub-domain pairs, and missing lifecycle fields. |
| 12. Human review | Human | Review queue item | Approved, rejected, or revised record | Record reviewer, decision, timestamp, and reason. |
| 13. Publish approved record | System | Validated approved record | Active artifact | Write audit log and preserve version history. |

## 11. Relationship Governance

| Relationship | Direction | Typical Cardinality | Notes |
|---|---|---|---|
| REL-DER | Source derives from target | N:1 or N:M | Requirement or control may derive from multiple sources. |
| REL-SAT | Source satisfies target | N:M | Multiple controls can satisfy one requirement. |
| REL-SUP | Source supports target | N:M | Support is weaker than satisfaction. |
| REL-SPL | Source specifies target | 1:N | Standards and procedures specify policies or controls. |
| REL-IMP | Source implements target | N:1 | Configurations and rules implement controls. |
| REL-VER | Source verifies target | N:1 | Evidence verifies one or more controls. |
| REL-MEA | Source measures target | N:M | Metrics may measure multiple controls. |
| REL-MIT | Source mitigates target | N:M | Controls or actions mitigate risks/vulnerabilities. |
| REL-AFF | Source affects target | N:M | Risks, threats, or changes affect assets/services. |
| REL-EXC | Source exempts target | N:1 | Exceptions exempt one requirement or control. |
| REL-DEP | Source depends on target | N:M | Used for technical or operational dependency. |
| REL-CNF | Source conflicts with target | N:M | Requires `resolution_status` and `resolution_note`. |

### 11.1 Cascade Rules for SQLite

| Event | Rule |
|---|---|
| Delete source artifact | Child tags, source relationships, mappings, applicability records, assessments, dependencies, tools, stakeholders, references, and remediation actions are deleted. |
| Delete target artifact | Restricted when referenced as target by a relationship; resolve or delete relationships first. |
| Deprecate artifact | Prefer setting `publication_status = DEPRECATED` and `is_active = 0` instead of physical deletion. |
| Merge duplicate artifacts | Preserve old IDs in `source_artifact_id` or external reference records and create `REL-DER`/`REL-SUP` relationships as needed. |

## 12. Complete Artifact Examples

### 12.1 Published Policy Example

```json
{
  "id": "POL-MFA-ADMIN-001",
  "type": "ART-POL",
  "title_en": "Administrative MFA Policy",
  "primary_domain": "SD-03",
  "sub_domain": "SD-03.02",
  "abstraction_level": "ABS-POL",
  "source": "SRC-INT",
  "source_type": "DOCUMENT",
  "obligation_level": "OBL-MND",
  "granularity_level": "GRN-DETAILED",
  "priority": "PRI-HIGH",
  "priority_weight": 7,
  "implementation_status": "STS-FULL",
  "verification_status": "VER-PASS",
  "effectiveness": "EFF-HIGH",
  "exception_status": "EXC-NONE",
  "review_frequency": "ANNUAL",
  "next_review_date": "2027-07-10",
  "publication_status": "PUBLISHED",
  "effective_date": "2026-07-10",
  "classification_confidence": 0.94,
  "classification_rationale": "The artifact governs MFA for administrative authentication and therefore belongs to authentication and credential management.",
  "requires_human_review": false,
  "ai_review_status": "AIR-AUTO-ACCEPTED",
  "source_document": "Internal IAM Policy",
  "version": 1,
  "is_active": true
}
```

### 12.2 Low-Confidence Classification Example

```json
{
  "id": "CTR-LEGACY-SERVER-001",
  "type": "ART-CTR",
  "title_en": "Legacy Server Protection Control",
  "primary_domain": "SD-04",
  "sub_domain": "SD-04.02",
  "abstraction_level": "ABS-CTR",
  "source": "SRC-RSK",
  "source_type": "OBSERVATION",
  "obligation_level": "OBL-CON",
  "granularity_level": "GRN-MEDIUM",
  "control_nature": "NAT-TEC",
  "control_function": "FUN-PRE",
  "testability": "TST-MAN",
  "priority": "PRI-MEDIUM",
  "priority_weight": 4,
  "implementation_status": "STS-PARTIAL",
  "verification_status": "VER-NOT-VERIFIED",
  "effectiveness": "EFF-UNKNOWN",
  "exception_status": "EXC-NONE",
  "classification_confidence": 0.58,
  "classification_rationale": "The scope mentions legacy server protection but does not clearly distinguish endpoint hardening, vulnerability management, or compensating controls.",
  "requires_human_review": true,
  "ai_review_status": "AIR-HUMAN-REVIEW",
  "source_document": "Legacy Infrastructure Assessment",
  "version": 1,
  "is_active": true
}
```

## 13. Version History

| Version | Date | Changes |
|---|---|---|
| 2.0 | 2026-07-10 | Added namespaces and SDT v2.0 domain taxonomy. |
| 2.1.1 | 2026-07-10 | Added Requirement Type, mapping strength, AI review status, expanded examples, migration script, and relationship governance improvements. |
| 2.2.0 | 2026-07-10 | Switched normative database to SQLite and added lifecycle/review/import/self-assessment/maturity/cost fields. |
| 2.2.1 | 2026-07-10 | Removed SQLite JSON duplication for repeatable collections, fully specified `applicability_scope`, added review/publication schema conditions, created all migration child tables, and added cost/effort planning fields. |
