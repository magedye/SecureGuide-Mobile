# SecureGuide Mobile: installation and recovery

## Release boundary

The APK produced by the ordinary CI compile is unsigned diagnostic evidence. It
is not a distributable release candidate. Install only an artifact produced by
the protected `Android signed release candidate` workflow after the product
owner has approved its permanent application ID, version/build number, and
signing-certificate SHA-256.

Keep signing keys and passwords outside the repository. A candidate must use a
three-component version name and a positive, strictly increasing build number.

## Verify before installing

Use a disposable Android device or emulator first. The verifier rejects an
invalid signature, an unexpected certificate, or an unexpected application ID
before it changes the installed application:

```powershell
mobile\tool\verify_android_install.ps1 `
  -SignedApk <absolute-apk-path> `
  -ApplicationId <owner-approved-application-id> `
  -ExpectedCertificateSha256 <approved-certificate-sha256> `
  -DeviceId <adb-device-id>
```

Preserve the generated installation evidence and then run the offline device
acceptance workflow against the same candidate.

## Safe upgrade

Before an update:

1. Create a validated database backup from Profile Settings and store it in an
   access-controlled location.
2. Record the current application ID, version/build, APK SHA-256, signing
   certificate SHA-256, database schema version, and backup SHA-256.
3. Retain the previously qualified signed APK and its verification evidence.
4. Install with update semantics only when the application ID and certificate
   match the installed package.
5. Re-run offline acceptance and open a sample of profile evidence after the
   process restart.

## Non-destructive recovery

Do not uninstall the application or clear its storage as an automatic recovery
step: both actions can destroy enterprise profiles, assessments, exceptions,
and evidence. SecureGuide migrations are forward-only, so an older binary may
not understand a database already upgraded by a newer build.

On failure, preserve the live data and pre-update backup. Validate a copy of the
backup in an isolated test context, qualify schema compatibility, and restore
only through the application's validated restore control after explicit owner
authorization. Treat loss or suspected compromise of a signing key as an
external security incident and stop the release until the selected store's
rotation or revocation process is complete.

The fuller operational procedure is in
[`docs/RELEASE_AND_RECOVERY.md`](../../docs/RELEASE_AND_RECOVERY.md).
