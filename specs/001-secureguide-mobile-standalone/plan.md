# Implementation Plan: SecureGuide Mobile Standalone

## 1. Architectural Overview

The application architecture transitions from a client-server (Flutter + Python sidecar) model to a fully native offline-first mobile architecture.

```text
Flutter UI
    ↓
Dart application/domain layer
    ↓
LocalSecureGuideClient / repositories
    ↓
SQLite + local file/evidence storage
```

**Python Deprecation**: Python remains exclusively as a build-time utility for importing reference data, schema generation, and catalog preparation. The released mobile runtime (Android/iOS) will no longer package or require Python.

## 2. Structural Implementation

### 2.1. Flutter Platform Structure
- Maintain and enhance the `mobile/` directory as a fully structured Flutter project for Android and iOS.
- Remove localhost/HTTP networking dependencies targeting the Python server.
- Configure iOS (`Runner`) and Android (`app`) build settings for isolated runtime execution.

### 2.2. SQLite Lifecycle & First-Run Initialization
- Ship a pre-compiled `catalog.db` built by Python scripts within the app bundle (assets).
- On the first application launch, perform a secure file copy of the reference database from the asset bundle into the writable app documents directory.
- Initialize `PRAGMA foreign_keys = ON`.
- Ensure migrations strictly preserve user-generated operational data (Enterprise Profiles, Assessments, Evidence).

### 2.3. Dart Repositories and Services
- Implement `LocalSecureGuideClient` as a drop-in replacement for `HttpSecureGuideClient`.
- Mirror the domain and DTO structures in Dart to interact directly with SQLite via `sqflite` (or similar).

### 2.4. Business-Rule Migration and Parity
- Re-implement catalog querying, filtering, template selection, and assessment score calculation logic natively in Dart.
- **Parity Testing**: Conduct explicit parity checks comparing the new Dart logic output with the existing Python `read-model-v1` golden samples to prevent behavioral drift.

### 2.5. Local Evidence Storage
- Implement an evidence repository that copies/moves user-selected files into an app-sandboxed local directory.
- Store metadata (file hash, path, timestamp, size) in the SQLite `profile_evidence` table linked securely to the active enterprise profile context.

### 2.6. Reporting and Localization
- Ensure the reporting generation logic parses the local SQLite schema and emits HTML/JSON locally.
- Integrate Flutter localization (L10n) mechanisms providing immediate toggles between English and Arabic (RTL).

## 3. Validation and CI
- Build automated Flutter unit and integration tests executing against a test SQLite database.
- CI pipelines must execute golden sample parity tests and compile release binaries for Android and iOS to verify that the absence of Python does not break the build.
- Perform offline end-to-end (E2E) testing demonstrating app launch, profile creation, and assessment execution in Airplane Mode.
