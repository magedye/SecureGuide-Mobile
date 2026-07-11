# Product Requirements Document (PRD)
**Project:** SecureGuide Mobile (Enterprise Reference Platform)
**Version:** 3.0

## 1. Vision & Scope
SecureGuide Mobile is no longer just a standalone mobile utility; it is designed as an **Enterprise Reference Platform** that operates primarily on an offline-first mobile architecture. It allows enterprise security professionals, CISOs, and auditors to map, track, and operationalize a comprehensive Unified Security Artifact Classification Model (USACM v2.2.1).

**Core Philosophy:** 
- **Master Catalog vs. Operational State:** The application separates the immutable global standards (Master Catalog) from the operational posture of specific environments (Enterprise Profiles).
- **Proactive Security:** By integrating Threat Indicators and Information Assets, the platform shifts from static compliance checking to dynamic risk visibility and posture management.

## 2. Target Audience (User Personas)
1. **Security Architect / Master Admin:** Manages the Master Catalog, ingests frameworks (NIST, ISO), and defines the overarching references (`security_artifacts`).
2. **CISO / Enterprise Manager:** Creates and manages `enterprise_profiles` (e.g., "Riyadh Branch", "Cloud Infrastructure"), assigning scopes and reviewing aggregated progress.
3. **Compliance Auditor / Operator:** Works within a specific Profile to update `profile_artifacts` and `profile_assessments`, verifying implementation states and evidence.
4. **SecOps Analyst:** Monitors `threat_indicators` against the configured Information Assets and existing Vulnerabilities to identify proactive mitigation steps.

## 3. Core Features & Capabilities

### 3.1. Enterprise Profile Management
- Support for multiple institutional contexts (Profiles) within a single app instance.
- Decoupling of global security artifacts from profile-specific implementation statuses.
- Profile-level assessments and audit trails.

### 3.2. Information Assets Module
- Cataloging `enterprise_assets` (Hardware, Software, Data, People).
- Mapping assets directly to their mitigating `controls`, the `vulnerabilities` they are susceptible to, and the `threats` that target them.

### 3.3. Threat Indicator & Intelligence Module
- Proactive integration with MITRE ATT&CK.
- Mapping `threat_indicators` (IoCs) to vulnerabilities and the specific detection tools needed to identify them.

### 3.4. The 8 Core Engines
A robust backend system featuring 8 distinct engines: Classification, Priority, Progress, Recommendation, Filter, Indicator, Context, and Data Integrity to process relationships, calculate risk, and guide the user.

### 3.5. Offline-First SQLite Architecture
- 100% functionality without an active internet connection using a highly normalized, constraint-driven SQLite database.
- Synchronization and backup capabilities configured via the Settings page.

## 4. Key Success Metrics
1. **Schema Integrity:** Zero data corruption or invalid classifications (guaranteed by USACM CHECK constraints).
2. **Performance:** Sub-100ms queries for deep hierarchical lookups (e.g., Asset -> Vulnerability -> Control -> Objective) even with 10,000+ artifacts.
3. **Extensibility:** The ability to add new Frameworks without altering the database schema.

## 5. Release Plan (High Level)
- **Phase 1: Foundation:** SQLite Schema, Models, and basic CRUD operations.
- **Phase 2: Logic Layer:** Implementation of the 8 Core Engines and Event Bus.
- **Phase 3: Presentation Layer:** UI/UX implementation including the Profile-aware Home Screen, Assets, Indicators, and comprehensive Settings.
- **Phase 4: Data Intake & Intelligence:** AI Pipelines and JSON batch imports.

## 8. Advanced Architectural NFRs
- **Data Isolation:** Operational data MUST be strictly separated from reference catalog data (Profile Artifacts vs Security Artifacts).
- **Dynamic Asset Intelligence:** The system must dynamically recalculate Asset Risk Scores and Control Coverage percentages whenever a related vulnerability or control state changes.
