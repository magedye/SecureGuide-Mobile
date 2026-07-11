# Technical Architecture Document (TAD)
**Project:** SecureGuide Mobile (Enterprise Reference Platform)
**Version:** 3.0

## 1. High-Level Architecture Overview
SecureGuide Mobile v3.0 utilizes a **5-Layer Offline-First Architecture** designed to isolate data logic from presentation, ensuring high performance, maintainability, and data integrity.

### 1.1 The 5 Layers
1. **Presentation (UI) Layer:** The visual components (Flutter/React Native) that render the Profile-aware Home Screen, Asset Catalog, and Indicators.
2. **Service & State Layer:** Orchestrates data flow between the UI and the underlying Engines using an **Event Bus**. Manages application state (e.g., active `enterprise_profile_id`).
3. **Core Engines Layer:** The brain of the application containing 8 specialized processing units (detailed below).
4. **Data Access Layer (DAL):** Repositories and DAOs that interface with SQLite, managing deep hierarchical queries and caching.
5. **Storage Layer:** The highly normalized SQLite database acting as the single source of truth for both the Master Catalog and Enterprise Profiles.

## 2. The 8 Core Engines

The system's logic is distributed across 8 specialized engines:

1. **Classification Engine:** Enforces the USACM v2.2.1 taxonomy (`SD-01` to `SD-08`) and validates `type` (e.g., ART-OBJ, ART-REQ, ART-CTR) when artifacts are ingested or created.
2. **Priority & Weighting Engine:** Calculates the relative importance of artifacts and controls based on their relationships to critical Information Assets and active Threat Indicators.
3. **Progress Tracking Engine:** Computes completion percentages by rolling up `profile_assessments` from the leaf nodes (e.g., ART-CTR) up to the root nodes (e.g., ART-OBJ) within a specific Enterprise Profile.
4. **Recommendation Engine:** Suggests specific controls to implement or vulnerabilities to patch based on the user's active Profile and associated Information Assets.
5. **Filter & Search Engine:** Provides high-speed querying using FTS (Full-Text Search) across the SQLite database, allowing users to filter by domain, tag, or implementation status.
6. **Indicator & Threat Engine:** Processes `threat_indicators` (IoCs) and maps them to `enterprise_assets` to highlight proactive mitigation steps (based on MITRE ATT&CK).
7. **Institutional Context Engine:** Manages the active `enterprise_profile`. Ensures that when an operator views a control, they see the implementation status relevant ONLY to their active profile context (e.g., "Riyadh Branch").
8. **Data Integrity & Sync Engine:** Manages JSON batch imports, verifies SQLite `CHECK` constraints (e.g., valid `lifecycle_state`), handles checksums (`artifact_hash`), and manages cloud synchronization when online.

## 3. Communication & Event Bus
To prevent tight coupling between the UI and the 8 Engines, SecureGuide employs an **Event Bus**.
- **Publishers:** UI components or background sync processes emit events (e.g., `ProfileSelectedEvent`, `AssessmentUpdatedEvent`).
- **Subscribers:** Relevant Engines listen to these events. For example, when an `AssessmentUpdatedEvent` is fired, the **Progress Tracking Engine** recalculates completion percentages, and the **Recommendation Engine** updates its suggested next steps.

## 4. Concept Relationship Model
The foundation of the architecture relies on a strict hierarchical relationship between artifacts, mapping from abstract goals to technical implementations:
- **ART-OBJ** (Objectives: E.g., "Ensure Data Privacy")
- **ART-REQ** (Requirements: E.g., "Encrypt Data at Rest")
- **ART-CTR** (Controls: E.g., "AES-256 Encryption Policy")
- **ART-PRC / ART-CFG** (Procedures / Configurations: E.g., "How to configure AES-256 on AWS S3")

This hierarchy is connected to the **Information Assets** and **Threat Indicators**, providing a holistic view of the enterprise security posture.


## 6. Comprehensive Concept Relationship Model (Incorporated)

### 6.1 Entity Hierarchy (USACM v2.2.1)


### 6.2 Relationship Mapping


