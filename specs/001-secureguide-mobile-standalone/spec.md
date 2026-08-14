# Specification: SecureGuide Mobile Standalone

## 1. Product Objective
Develop SecureGuide Mobile (SGM) into an offline-first, standalone application that provides a unified security knowledge and assessment platform for enterprise environments. The app must empower organizations to select relevant templates, track security implementation, verify evidence, manage gaps, and evaluate progress locally.

## 2. Target Users and Use Cases
- **Security Officers & Compliance Auditors**: Conduct offline security posture reviews, select appropriate templates, and map controls to enterprise profiles.
- **IT Administrators**: Track configuration implementation, document exceptions, and record verification evidence without needing continuous server access.
- **Project Managers**: Manage task backlogs, blue-print assignments, and gap remediation tracking in offline or disconnected environments.

## 3. Core Behaviors

### 3.1. Standalone Mobile Operation & Offline-First Behavior
- The mobile application must operate completely offline, without reliance on a backend server, Python sidecar (`127.0.0.1`), or internet connection for its core workflows.
- All catalogs, enterprise profiles, rules, assessments, evidence, and exceptions are processed and persisted locally.

### 3.2. Enterprise Profiles vs Security Catalog
- **Master Catalog**: Immutable, standardized security elements (USACM and SDT classified).
- **Enterprise Profiles**: A distinct operational state representing a specific organization, system, or audit scope.
- State implementation (`implementation_status`, `verification_status`, etc.) exists strictly within the context of an Enterprise Profile.

### 3.3. Assessments, Evidence, and Exceptions
- Users can evaluate controls and document the implementation state.
- Evidence (images, documents, notes) is stored securely on the local filesystem with integrity metadata linked in the local datastore.
- Risk acceptances and exceptions are explicitly tracked per profile with associated justifications and lifecycle states.

### 3.4. Blueprints and Tasks
- Users can adopt security blueprints (templates) that map controls and requirements to their profiles.
- Tasks are derived from blueprints and gaps, managed entirely on the device.

### 3.5. Reporting
- Built-in generation of compliance, gap, and summary reports locally on the device based strictly on profile state.

### 3.6. Cross-Platform & Localization
- **Platforms**: Natively compiled for Android and iOS targets.
- **Localization**: Full support for English and Arabic, including robust Right-to-Left (RTL) layout capabilities as first-class citizens.

## 4. Local Persistence
- SQLite serves as the authoritative datastore.
- A pre-packaged reference catalog database must be safely copied on the first run, shielding it from operational changes.
- Subsequent migrations must preserve all operational data (profiles, assessments, exceptions).

## 5. Acceptance Criteria
- App runs completely offline post-installation.
- Creation of enterprise profiles and assessments functions accurately without a Python backend.
- Evidence attachment and viewing work flawlessly via the local filesystem.
- Arabic (RTL) and English languages toggle seamlessly with correct layout rendering.
- No Python sidecar process is required or active during standard app usage.

## 6. Out of Scope
- Real-time cloud synchronization or collaborative multi-user editing.
- Complex threat graphs or SIEM/EDR automated integrations.
- Automated remote evidence collection.
- Advanced predictive risk scoring algorithms.
