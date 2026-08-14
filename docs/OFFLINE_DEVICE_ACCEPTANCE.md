# Offline device acceptance

This gate qualifies the standalone Android runtime on a real device or Android
emulator. A host-side widget test is not device acceptance, and a successful
compile is not proof that the workflow survives Airplane Mode.

## Preconditions

- Flutter 3.41.1 and Android platform tools are on `PATH`.
- The target appears as `device` in `adb devices` (not `offline` or
  `unauthorized`).
- The operator accepts a temporary change to Airplane Mode, Wi-Fi, and mobile
  data. The runner records and restores their prior values in `finally`.
- Use a disposable emulator or a test device. Do not run this gate on a device
  carrying production-only data.

## Automated run

From the repository root:

```powershell
mobile\tool\run_offline_acceptance.ps1 -DeviceId <adb-device-id>
```

The runner first proves the mobile tree contains no Python runtime, loopback
sidecar endpoint, Dart HTTP client, or Android `INTERNET` permission. It then
enforces Airplane Mode with Wi-Fi and mobile data disabled and runs
`integration_test/app_test.dart` through `flutter drive --keep-app-running` on
the selected device. It then installs the normal debug application over the
test target without deleting package data, force-stops it, launches a fresh
process, and verifies that process renders the persisted profile while the
device is still offline.

The device test covers:

1. cold application launch from the bundled SQLite catalog;
2. enterprise-profile creation and activation;
3. governed catalog selection;
4. profile-scoped assessment and immutable assessment history;
5. local evidence copy, SHA-256 verification, and evidence rendering;
6. application-root restart and persistence of profile, assessment, and
   evidence rows;
7. normal-application replacement without data deletion and process-level
   `force-stop`/relaunch persistence.

The runner writes a timestamped log and JSON result under
`mobile/build/offline-acceptance/`. A passing JSON record must show all three
offline settings and `passed: true`. These generated files are acceptance
evidence and must not be treated as source files.

The generated JSON must also report `processRestart.passed: true`, the exact
application ID, and the persisted `Offline acceptance ...` profile name. Use
`-PackageName` when qualifying a build whose application ID differs from the
debug default.

## Failure handling

- A failure is a failed acceptance, even when the UI appears usable.
- Preserve the log and JSON summary before retrying.
- Confirm the runner restored the original radio settings. If ADB disconnected
  before `finally` completed, restore them manually before further testing.
- Do not mark T214 complete until an actual emulator/device run and the
  process-level restart check both pass.
