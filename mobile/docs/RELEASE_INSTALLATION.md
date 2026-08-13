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
  -SignedApk <apk-path> `
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

## Catalog-content upgrade behavior

On an existing installation, startup does not replace the user's database with
the bundled catalog. SecureGuide instead:

1. extracts the bundled `assets/catalog.db` to a temporary candidate;
2. creates a same-filesystem recovery copy of the installed database;
3. migrates the installed database and candidate to the embedded schema;
4. transactionally merges governed catalog tables while preserving stable IDs;
5. proves that profiles, selected ضوابط, assessments, evidence, exceptions,
   blueprints, and tasks have the same operational snapshot before and after;
6. verifies catalog closure, SQLite integrity, and foreign keys;
7. deletes the recovery copy only after success.

Any failure after the recovery copy is created restores that copy. A failure
before the copy exists leaves the live database untouched. Reapplying the same
candidate is idempotent. The qualified predecessor fixture upgrades from four
to 1,227 catalog ضوابط while preserving two profiles, three selected items, one
assessment, one evidence record, and one exception. The measured host-side
upgrade took 6,743.899 ms; device timing remains part of device acceptance.

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
