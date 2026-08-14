# SecureGuide mobile release and recovery

## Release identities and versions

The product owner must approve the permanent Android application ID and iOS
bundle ID before the first distributable release. Store identities are durable:
changing one later creates a different application instead of an update.

Every candidate uses a three-component `version_name` and a positive,
strictly increasing build number. The protected Android workflow accepts both
as explicit inputs; the committed `pubspec.yaml` version remains the local
development baseline.

## Android signing

The normal CI workflow compiles an unsigned release and never receives signing
secrets. `.github/workflows/android-release.yml` is a manual candidate workflow
bound to the `release-signing` GitHub environment. Configure required reviewers
and these encrypted environment secrets:

- `ANDROID_KEYSTORE_BASE64`
- `ANDROID_KEYSTORE_PASSWORD`
- `ANDROID_KEY_ALIAS`
- `ANDROID_KEY_PASSWORD`

The workflow rejects partial configuration and `com.example.*`, materializes
the keystore only under the runner's temporary directory, and never uploads it.
It builds APK and AAB artifacts, verifies the APK with `apksigner`, verifies the
AAB with `jarsigner`, checks package/version metadata, and publishes SHA-256
evidence with the candidate. The Gradle release configuration has no debug-key
fallback.

The upload key must be held outside the repository and backed up through the
organization's approved secret-management process. For Google Play, keep the
upload key distinct from the app-signing key when the owner selects Play App
Signing.

## Installation qualification

Download the protected workflow artifact and verify it on a disposable Android
device or emulator:

```powershell
mobile\tool\verify_android_install.ps1 `
  -SignedApk <absolute-apk-path> `
  -ApplicationId <owner-approved-application-id> `
  -ExpectedCertificateSha256 <approved-certificate-sha256> `
  -DeviceId <adb-device-id>
```

The script verifies the APK signature and matches its signing-certificate
SHA-256 and application ID before installation. It then installs with `adb
install -r`, confirms the package path and launchable activity, launches it,
and records the artifact hash and device evidence under
`mobile/build/installation-evidence/`. Complete the offline acceptance gate in
`docs/OFFLINE_DEVICE_ACCEPTANCE.md` against the same candidate before approval.

## iOS boundary

General CI compiles `Runner.app` with `--no-codesign` on macOS. A distributable
iOS archive additionally requires an owner-approved bundle ID, Apple Developer
team, distribution certificate, provisioning profile, and the chosen App Store
or enterprise distribution channel. Those external identities are not stored
in this repository. Do not describe the unsigned CI output as an installable
or signed iOS release.

## Non-destructive upgrade and recovery

Before installing an update:

1. Create a database backup from Profile Settings and keep it outside the
   device with access controls appropriate to its evidence and assessment data.
2. Record the installed application ID, version/build, APK SHA-256, signing
   certificate SHA-256, database schema version, and backup SHA-256.
3. Retain the previously qualified APK and its signature evidence.
4. Install the candidate as an update only when the application ID and signing
   certificate match the installed package.
5. Run the offline workflow and open a sample of evidence after restart.

If the update fails, preserve the live data and the pre-update backup. Do not
uninstall or clear application data as an automatic rollback step. SecureGuide
migrations are forward-only; an older binary might not understand a database
already migrated by a newer build. Qualify schema compatibility first. When it
is not proven, install the prior binary in an isolated test context, validate a
copy of the pre-update backup there, and restore through the application's
validated restore control only after explicit owner authorization.

Loss or suspected compromise of an upload/signing key is an external security
incident. Stop release, revoke or rotate through the selected store process,
and do not create an unrelated replacement key and present it as a compatible
update.
