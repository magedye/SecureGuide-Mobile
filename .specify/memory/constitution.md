# SecureGuide Constitution

## Core Operating Principles

1. **Standalone Offline-First Application**: SecureGuide Mobile is a standalone, offline-first application.
2. **No Python in Production**: Production mobile runtime must not depend on Python.
3. **No Sidecars**: No Python sidecar is permitted for core runtime operation.
4. **Offline Assessment**: Core assessment workflows must not depend on HTTP or Internet access.
5. **SQLite Datastore**: SQLite is the authoritative local runtime datastore.
6. **Data Separation**: Reference/security-catalog data must remain separated from operational/profile-specific data.
7. **Behavioral Parity**: Business logic migrated from Python to Dart requires behavioral/parity verification.
8. **Data Preservation**: Supported database upgrades must preserve user operational data.
9. **Local Evidence Integrity**: Evidence must be stored and managed locally with integrity metadata.
10. **Multi-Platform Support**: Android and iOS remain supported target platforms.
11. **Localization**: Arabic and English, including RTL (Right-to-Left), are first-class requirements.
12. **Simplicity First**: Implementation should prefer the simplest production-suitable architecture.
13. **Avoid Unnecessary Complexity**: Do not introduce unnecessary infrastructure or security complexity.
14. **Definition of Done**: A task is complete only when implementation and applicable verification pass.
15. **Unhindered Progress**: External platform dependencies must not block unrelated implementation.
16. **Specification Supremacy**: Repository specifications and verified implementation evidence take precedence over assumptions.
