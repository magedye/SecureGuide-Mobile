# Security Domain Taxonomy (SDT) v2.2.1
## Self-Contained Reference for Security Domain Classification

| Field | Value |
|---|---|
| Document Title | Security Domain Taxonomy (SDT) v2.2.1 |
| Version | 2.2.1 |
| Status | Production Baseline - Corrective Release |
| Date | 2026-07-10 |
| Purpose | Provide a stable two-level domain taxonomy for classifying security artifacts and linking them to typical risks, controlled tags, AI confidence handling, and mobile implementation controls. |
| Target Audience | AI agents, developers, mobile application teams, security architects, GRC teams, auditors, control owners, and risk owners. |
| Compatibility | USACM v2.2.1, SQLite, NIST CSF 2.0, ISO/IEC 27002:2022, CIS Controls v8.1, PCI DSS v4.0, NIST SP 800-53 Rev.5. |
| Supersedes | SDT v2.2.0 |

## 1. Executive Purpose

SDT v2.2.1 defines the mandatory security domain taxonomy for classifying security artifacts. It provides 8 primary domains and 40 sub-domains with deterministic tie-breaker rules, controlled tags, typical risks, confidence handling, and implementation guidance for USACM v2.2.1.

## 2. Design Principles

| Principle | Rule |
|---|---|
| Stability | Primary domains are business and technology agnostic enough to remain stable over time. |
| Comprehensiveness | The 40 sub-domains cover governance, assets, identity, infrastructure, applications, detection, resilience, people, third parties, and physical security. |
| Single classification | Each artifact receives exactly one primary domain and one sub-domain. |
| Tags for secondary context | Secondary concepts such as cloud, Zero Trust, OT, PCI, or ransomware are represented as controlled tags. |
| Human review for ambiguity | Low-confidence or cross-domain artifacts must be routed to human review rather than forced into a weak classification. |
| SQLite implementation alignment | SDT tags and scope values must be stored in normalized USACM v2.2.1 child tables in the mobile database. |

## 3. Primary Domains

| Code | Primary Domain |
|---|---|
| SD-01 | Governance, Risk & Compliance |
| SD-02 | Assets, Data & Privacy |
| SD-03 | Identity, Access & Privilege |
| SD-04 | Infrastructure, Network & Cloud |
| SD-05 | Applications, Development & Change |
| SD-06 | Detection, Monitoring & Vulnerability |
| SD-07 | Response, Recovery & Resilience |
| SD-08 | People, Third Parties & Physical |


## 4. Sub-Domain Reference


### SD-01: Governance, Risk & Compliance
| Code | Sub-Domain |
|---|---|
| SD-01.01 | Cybersecurity Strategy & Governance |
| SD-01.02 | Policies, Standards & Exceptions |
| SD-01.03 | Security Risk Management |
| SD-01.04 | Compliance, Audit & Assurance |
| SD-01.05 | Security Program Management & Metrics |


### SD-02: Assets, Data & Privacy
| Code | Sub-Domain |
|---|---|
| SD-02.01 | Asset Inventory & Management |
| SD-02.02 | Software & License Management |
| SD-02.03 | Data Classification & Ownership |
| SD-02.04 | Data Protection & Encryption |
| SD-02.05 | Privacy, Retention & Disposal |


### SD-03: Identity, Access & Privilege
| Code | Sub-Domain |
|---|---|
| SD-03.01 | Identity Lifecycle Management |
| SD-03.02 | Authentication & Credential Management |
| SD-03.03 | Authorization & Access Management |
| SD-03.04 | Privileged Access Management |
| SD-03.05 | Remote & External Access |


### SD-04: Infrastructure, Network & Cloud
| Code | Sub-Domain |
|---|---|
| SD-04.01 | Network & Communications Security |
| SD-04.02 | Systems, Servers & Endpoint Security |
| SD-04.03 | Configuration & Security Hardening |
| SD-04.04 | Cloud & Virtual Platform Security |
| SD-04.05 | Email, Web & Digital Communications |


### SD-05: Applications, Development & Change
| Code | Sub-Domain |
|---|---|
| SD-05.01 | Application Security Governance & SDLC |
| SD-05.02 | Application & API Security Testing |
| SD-05.03 | Code, Components & Software Supply Chain |
| SD-05.04 | Change & Release Management |
| SD-05.05 | Database & Critical Application Security |


### SD-06: Detection, Monitoring & Vulnerability
| Code | Sub-Domain |
|---|---|
| SD-06.01 | Logging & Security Monitoring |
| SD-06.02 | Threat Detection & Alerts |
| SD-06.03 | Vulnerability & Patch Management |
| SD-06.04 | Security Testing & Assessments |
| SD-06.05 | Threat Intelligence & IoCs |


### SD-07: Response, Recovery & Resilience
| Code | Sub-Domain |
|---|---|
| SD-07.01 | Incident Management |
| SD-07.02 | Digital Forensics & Evidence |
| SD-07.03 | Backup & Restore |
| SD-07.04 | Business Continuity & Disaster Recovery |
| SD-07.05 | Crisis Management & Communication |


### SD-08: People, Third Parties & Physical
| Code | Sub-Domain |
|---|---|
| SD-08.01 | Awareness, Training & Security Culture |
| SD-08.02 | HR Security & Employee Lifecycle |
| SD-08.03 | Supplier & Third-Party Management |
| SD-08.04 | Physical & Environmental Security |
| SD-08.05 | Acceptable Use & Professional Conduct |


## 5. Domain Selection and Tie-Breaker Rules
| Rule | Decision |
|---|---|
| SDT-TB-001 | If the artifact primarily defines governance, accountability, risk, audit, policy lifecycle, or program measurement, classify as SD-01. |
| SDT-TB-002 | If the artifact primarily concerns asset inventory, data classification, encryption, retention, privacy, or disposal, classify as SD-02. |
| SDT-TB-003 | If the artifact primarily concerns accounts, authentication, authorization, privilege, credentials, or remote access, classify as SD-03. |
| SDT-TB-004 | If the artifact primarily concerns networks, endpoints, servers, configuration hardening, cloud platforms, or email/web protections, classify as SD-04. |
| SDT-TB-005 | If the artifact primarily concerns software development, APIs, code, components, release/change, or critical application logic, classify as SD-05. |
| SDT-TB-006 | If the artifact primarily concerns logging, monitoring, alerts, vulnerability management, security assessment, or threat intelligence, classify as SD-06. |
| SDT-TB-007 | If the artifact primarily concerns incidents, forensics, backups, BCP, DR, recovery, or crisis communication, classify as SD-07. |
| SDT-TB-008 | If the artifact primarily concerns training, HR security, suppliers, physical security, or acceptable use, classify as SD-08. |
| SDT-TB-009 | Cloud IAM is SD-03 when the main focus is identity/authentication/authorization; it is SD-04 when the main focus is cloud platform configuration or workload protection. |
| SDT-TB-010 | Application security testing is SD-05. Broad penetration testing, red teaming, or maturity assessment is SD-06. |
| SDT-TB-011 | Legacy ambiguous technology controls must be classified to the most probable SD-04 sub-domain only when confidence is at least 0.70; otherwise route to human review. |


## 6. Controlled Tag Taxonomy

Tags are optional but strongly recommended when the artifact has relevant secondary context. They must not replace the single primary domain and sub-domain decision. Tags must be selected from approved tag types and stored as normalized rows in USACM `artifact_tags`.

| Tag Type | Purpose | Examples |
|---|---|---|
| Technology | Specific technologies or platforms | AWS, Azure, Linux, Kubernetes, iOS |
| Framework | Frameworks, standards, and regulations | NIST CSF, ISO 27001, CIS, PCI DSS, NCA |
| Concept | Security concepts and principles | Zero Trust, Least Privilege, Defense in Depth |
| Context | Operational environments | Production, Dev, OT, IoT, Mobile, SaaS |
| Threat | Threat scenarios or actors | Ransomware, Phishing, Insider Threat |
| Data | Data categories or sensitivity | PII, Cardholder Data, Confidential |
| Party | Internal or external parties | Supplier, Customer, Regulator, Employee |


### 6.1 Tag JSON Example

```json
{
  "tags": [
    {"tag_type": "Technology", "tag_value": "AWS"},
    {"tag_type": "Concept", "tag_value": "Zero Trust"},
    {"tag_type": "Context", "tag_value": "Production"}
  ]
}
```

### 6.2 Tag Governance

| Step | Owner | Decision |
|---|---|---|
| Propose tag | User, AI, or analyst | Candidate tag value and type are submitted. |
| Validate | System | Tag type must be one of the seven approved types. |
| Approve new value | Taxonomy owner or security architect | Add value to approved tag catalog if reusable. |
| Use | AI/Human | Apply approved tag to artifacts as secondary context. |
| Review | Governance team | Retire duplicates, misspellings, and overly narrow tags. |


## 7. Typical Risks by Domain
| Domain | Typical Risks | Typical Mitigations |
|---|---|---|
| SD-01 | Weak accountability; policy gaps; unmanaged risk acceptance | Governance forums, risk register, policy lifecycle, KPIs/KRIs |
| SD-02 | Unknown assets; sensitive data exposure; retention violations | Asset inventory, data classification, encryption, DLP, retention rules |
| SD-03 | Account takeover; excessive privilege; weak authentication | MFA, access reviews, RBAC, PAM, credential management |
| SD-04 | Network intrusion; insecure hardening; exposed cloud services | Segmentation, secure baselines, EDR, CSPM, email/web protection |
| SD-05 | Vulnerable applications; insecure APIs; software supply-chain compromise | Secure SDLC, SAST, DAST, SCA, SBOM, release controls |
| SD-06 | Undetected attacks; unpatched vulnerabilities; weak intelligence | SIEM, EDR/NDR alerts, vulnerability SLAs, threat intelligence |
| SD-07 | Slow incident response; data loss; failed recovery | Playbooks, forensics, immutable backup, BCP/DR tests, crisis communications |
| SD-08 | Human error; supplier compromise; physical access breach | Awareness, HR security, third-party risk management, physical controls |


## 8. Classification Examples
| Artifact | Primary Domain | Sub-Domain | Confidence | Rationale |
|---|---|---|---|---|
| Representative Governance, Risk & Compliance artifact | SD-01 | SD-01.01 | High | Primary focus aligns to Governance, Risk & Compliance. |
| Representative Assets, Data & Privacy artifact | SD-02 | SD-02.01 | High | Primary focus aligns to Assets, Data & Privacy. |
| Representative Identity, Access & Privilege artifact | SD-03 | SD-03.01 | High | Primary focus aligns to Identity, Access & Privilege. |
| Representative Infrastructure, Network & Cloud artifact | SD-04 | SD-04.01 | High | Primary focus aligns to Infrastructure, Network & Cloud. |
| Representative Applications, Development & Change artifact | SD-05 | SD-05.01 | High | Primary focus aligns to Applications, Development & Change. |
| Representative Detection, Monitoring & Vulnerability artifact | SD-06 | SD-06.01 | High | Primary focus aligns to Detection, Monitoring & Vulnerability. |
| Representative Response, Recovery & Resilience artifact | SD-07 | SD-07.01 | High | Primary focus aligns to Response, Recovery & Resilience. |
| Representative People, Third Parties & Physical artifact | SD-08 | SD-08.01 | High | Primary focus aligns to People, Third Parties & Physical. |
| Cloud IAM policy for privileged users | SD-03 | SD-03.04 | High | Identity and privilege focus overrides cloud platform context. |
| Public S3 bucket prevention baseline | SD-04 | SD-04.04 | High | Cloud platform configuration focus. |
| API penetration testing requirement | SD-05 | SD-05.02 | High | Application/API testing focus. |
| Enterprise red team exercise | SD-06 | SD-06.04 | High | Broad security assessment rather than application-specific testing. |
| Low-confidence legacy server protection control | SD-04 | SD-04.02 | Low | Confidence 0.58; requires human review due to ambiguous scope. |
| Supplier VPN access rule | SD-03 | SD-03.05 | Medium | Remote/external access focus; tag as Supplier. |


## 9. AI Output Format

```json
{
  "artifact_id": "CTR-LEGACY-SERVER-001",
  "primary_domain": "SD-04",
  "sub_domain": "SD-04.02",
  "confidence": 0.58,
  "requires_human_review": true,
  "rationale": "The text refers to legacy server protection but does not clearly distinguish hardening, vulnerability remediation, or compensating controls.",
  "rejected_alternatives": [
    {"sub_domain": "SD-04.03", "reason": "Hardening is possible but not explicit."},
    {"sub_domain": "SD-06.03", "reason": "Patch/vulnerability management is possible but not explicit."}
  ],
  "tags": [
    {"tag_type": "Context", "tag_value": "Legacy"}
  ]
}
```

## 10. Implementation Requirements

| Requirement | Implementation Rule |
|---|---|
| Domain validation | `sub_domain` must begin with the selected `primary_domain`. |
| Tag validation | `tag_type` must be one of Technology, Framework, Concept, Context, Threat, Data, or Party. |
| Low confidence | Confidence below or equal to 0.70 must create a human review item. |
| Migration | Apply the USACM v2.2.1 SQLite migration and use normalized child tables for tags, applicability scope, self-assessments, dependencies, verification tools, stakeholders, remediation actions, and external references. |
| Mobile storage | Store SDT reference data locally to support offline classification and filtering. |
| Governance | Taxonomy owner approval is required for any new primary domain, sub-domain, or controlled tag type. |

## 11. Version History

| Version | Date | Changes |
|---|---|---|
| 2.0 | 2026-07-10 | Restructured to 8 primary domains and 40 sub-domains. |
| 2.1.1 | 2026-07-10 | Added production validation, AI confidence handling, controlled tags, examples, and tag governance. |
| 2.2.0 | 2026-07-10 | Added typical risks, tag JSON example, low-confidence example, migration requirement, and mobile/SQLite readiness. |
| 2.2.1 | 2026-07-10 | Aligned implementation requirements with USACM v2.2.1 normalized SQLite storage and clarified low-confidence legacy classification handling. |

