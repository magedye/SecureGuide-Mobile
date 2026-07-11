# Implementation Plan and Roadmap
**Project:** SecureGuide Mobile (Enterprise Reference Platform)
**Version:** 3.0

## 1. Developer Roadmap Overview
This roadmap is designed for the mobile development team to execute the Enterprise Reference Platform vision incrementally.

### Phase 1: Database Foundation (Weeks 1-2)
- **Objective:** Establish the offline-first SQLite database and enforce all USACM constraints.
- **Tasks:**
  1. Write the SQLite schema definition (DDL) for all 4 modules (Master Catalog, Profiles, Assets, Indicators).
  2. Implement all `CHECK` constraints (e.g., `primary_domain IN ('SD-01', ..., 'SD-08')`).
  3. Create DAOs (Data Access Objects) for standard CRUD operations.
  4. Build the JSON batch importer script to seed the `Master Catalog` from the AI Pipeline outputs.
- **Deliverable:** A populated, fully constrained SQLite database running on the mobile emulator.

### Phase 2: Core Engines & Logic (Weeks 3-4)
- **Objective:** Implement the 8 Engines and the Event Bus.
- **Tasks:**
  1. Implement the Event Bus (e.g., using RxDart/Provider in Flutter or Redux/Context in React Native).
  2. Build the `Institutional Context Engine` to manage the active profile state.
  3. Build the `Progress Tracking Engine` to recursively calculate completion percentages.
  4. Build the `Filter & Search Engine` (FTS5 integration).
- **Deliverable:** Unit-tested business logic layer capable of responding to state changes without UI dependency.

### Phase 3: UI/UX & Presentation (Weeks 5-7)
- **Objective:** Build the 5 core screens.
- **Tasks:**
  1. Implement the Global App Bar with the Profile Selector.
  2. Build the Dashboard (Home Screen) wiring up the Progress and Recommendation engines.
  3. Build the hierarchical Master Catalog viewer.
  4. Build the Information Assets and Threat Indicators screens.
  5. Build the 10-section Settings Page.
- **Deliverable:** Fully navigable mobile application with functional data binding.

### Phase 4: Proactive Security & Intelligence (Weeks 8+)
- **Objective:** Integrate MITRE ATT&CK mappings and Advanced Analytics.
- **Tasks:**
  1. Import the Threat Indicators JSON feed.
  2. Enable the `Indicator & Threat Engine` to flag vulnerable `enterprise_assets`.
  3. Implement data export features for audit reporting.
- **Deliverable:** Version 3.0 Release Candidate.

## 4. Advanced Refinement (Based on Architectural Deep Dive)
- **Phase 1b (Database Expansion):** Implement the separated 4-Tier Information Asset tables and Enterprise Profiles mapping logic.
- **Phase 2b (Advanced UI Screens):** Build the Profile Comparison Dashboard, Asset Intelligence UI, and Threat Indicator mapping views.

