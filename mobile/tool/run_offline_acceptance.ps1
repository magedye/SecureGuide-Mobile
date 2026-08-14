param(
    [string]$DeviceId,
    [string]$PackageName = 'com.example.secureguide_mobile',
    [string]$EvidenceDirectory = ""
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

if ($PackageName -notmatch '^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)+$') {
    throw "Invalid Android application ID: '$PackageName'."
}

$mobileRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$repositoryRoot = [System.IO.Path]::GetFullPath((Join-Path $mobileRoot '..'))
if ([string]::IsNullOrWhiteSpace($EvidenceDirectory)) {
    $EvidenceDirectory = Join-Path $mobileRoot 'build\offline-acceptance'
}
$evidenceRoot = [System.IO.Path]::GetFullPath($EvidenceDirectory)
New-Item -ItemType Directory -Path $evidenceRoot -Force | Out-Null

$pythonCommand = 'python'
$pythonPrefix = @()
if (-not (Get-Command $pythonCommand -ErrorAction SilentlyContinue)) {
    if (-not (Get-Command 'py' -ErrorAction SilentlyContinue)) {
        throw 'Python is required, but neither python nor py is available on PATH.'
    }
    $pythonCommand = 'py'
    $pythonPrefix = @('-3')
}

if ([string]::IsNullOrWhiteSpace($DeviceId)) {
    $connected = @(
        & adb devices |
            Select-String "`tdevice$" |
            ForEach-Object { ($_.Line -split "`t")[0] }
    )
    if ($connected.Count -ne 1) {
        throw "Specify -DeviceId; expected exactly one connected Android device, found $($connected.Count)."
    }
    $DeviceId = $connected[0]
}

$deviceAbi = (& adb -s $DeviceId shell getprop ro.product.cpu.abi).Trim()
if ($LASTEXITCODE -ne 0) { throw "Unable to read the CPU ABI from $DeviceId." }
$flutterTargetPlatform = switch ($deviceAbi) {
    'x86_64' { 'android-x64' }
    'arm64-v8a' { 'android-arm64' }
    'armeabi-v7a' { 'android-arm' }
    default { throw "Unsupported Android device ABI for Flutter acceptance: '$deviceAbi'." }
}

function Get-DeviceSetting([string]$Namespace, [string]$Name) {
    $value = (& adb -s $DeviceId shell settings get $Namespace $Name).Trim()
    if ($LASTEXITCODE -ne 0) { throw "Unable to read $Namespace/$Name from $DeviceId." }
    return $value
}

function Set-AirplaneMode([string]$State) {
    $action = if ($State -eq '1') { 'enable' } else { 'disable' }
    $result = (& adb -s $DeviceId shell cmd connectivity airplane-mode $action 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -eq 0 -and $result -notmatch 'Unknown command|SecurityException') {
        return
    }
    & adb -s $DeviceId shell settings put global airplane_mode_on $State | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Unable to set airplane mode on $DeviceId." }
}

function Set-Radio([string]$Radio, [string]$State) {
    $action = if ($State -eq '1') { 'enable' } else { 'disable' }
    & adb -s $DeviceId shell svc $Radio $action | Out-Null
}

$initialAirplane = Get-DeviceSetting 'global' 'airplane_mode_on'
$initialWifi = Get-DeviceSetting 'global' 'wifi_on'
$initialData = Get-DeviceSetting 'global' 'mobile_data'
foreach ($setting in @($initialAirplane, $initialWifi, $initialData)) {
    if ($setting -notin @('0', '1')) {
        throw "Cannot safely preserve an unexpected Android radio setting: '$setting'."
    }
}
$stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
$logPath = Join-Path $evidenceRoot "offline-acceptance-$stamp.log"
$summaryPath = Join-Path $evidenceRoot "offline-acceptance-$stamp.json"
$normalApkForRestart = Join-Path ([System.IO.Path]::GetTempPath()) "secureguide-normal-$stamp.apk"
$testPassed = $false
$processRestartPassed = $false
$profileName = $null

[ordered]@{
    deviceId = $DeviceId
    startedAtUtc = (Get-Date).ToUniversalTime().ToString('o')
    passed = $false
    phase = 'STARTED_NETWORK_STATE_RECORDED'
    originalState = [ordered]@{
        airplaneMode = $initialAirplane
        wifi = $initialWifi
        mobileData = $initialData
    }
    log = $logPath
} | ConvertTo-Json -Depth 4 | Set-Content -Path $summaryPath -Encoding utf8

# Preserve a normal application APK before flutter drive overwrites app-debug.apk
# with the integration-test entrypoint. Building happens before radio changes so
# an interrupted build cannot strand the device offline.
Push-Location $mobileRoot
try {
    & flutter build apk `
        --debug `
        --target lib/main.dart `
        --target-platform $flutterTargetPlatform `
        --no-pub 2>&1 |
        Tee-Object -FilePath $logPath -Append
    if ($LASTEXITCODE -ne 0) { throw 'Normal debug application build failed.' }

    $normalApk = Join-Path $mobileRoot 'build\app\outputs\flutter-apk\app-debug.apk'
    if (-not (Test-Path -LiteralPath $normalApk -PathType Leaf)) {
        throw "Normal debug APK was not produced at $normalApk."
    }
    Copy-Item -LiteralPath $normalApk -Destination $normalApkForRestart -Force
}
finally {
    Pop-Location
}

try {
    Set-AirplaneMode '1'
    Set-Radio 'wifi' '0'
    Set-Radio 'data' '0'
    Start-Sleep -Seconds 2

    $observedAirplane = Get-DeviceSetting 'global' 'airplane_mode_on'
    $observedWifi = Get-DeviceSetting 'global' 'wifi_on'
    $observedData = Get-DeviceSetting 'global' 'mobile_data'
    if ($observedAirplane -ne '1' -or $observedWifi -ne '0' -or $observedData -ne '0') {
        throw "Offline precondition failed: airplane=$observedAirplane wifi=$observedWifi data=$observedData."
    }

    Push-Location $repositoryRoot
    try {
        & $pythonCommand @pythonPrefix -m scripts.verify_mobile_runtime_boundary 2>&1 |
            Tee-Object -FilePath $logPath -Append
        if ($LASTEXITCODE -ne 0) { throw 'Static runtime-boundary verification failed.' }
    }
    finally {
        Pop-Location
    }

    Push-Location $mobileRoot
    try {
        & flutter drive `
            --driver=test_driver/integration_test_driver.dart `
            --target=integration_test/app_test.dart `
            -d $DeviceId `
            --keep-app-running 2>&1 |
            Tee-Object -FilePath $logPath -Append
        if ($LASTEXITCODE -ne 0) { throw 'Device integration test drive failed.' }

        $profileMatch = Select-String -Path $logPath -Pattern 'OFFLINE_ACCEPTANCE_PROFILE=(.+)$' |
            Select-Object -Last 1
        if ($null -eq $profileMatch -or $profileMatch.Matches.Count -eq 0) {
            throw 'The integration test did not emit its persisted profile identity.'
        }
        $profileName = $profileMatch.Matches[0].Groups[1].Value.Trim()

        # Replace the integration-test target with the preserved normal
        # application while retaining package data, then prove a fresh process
        # can read it.
        & adb -s $DeviceId install -r $normalApkForRestart 2>&1 |
            Tee-Object -FilePath $logPath -Append
        if ($LASTEXITCODE -ne 0) { throw 'Normal debug application install failed.' }

        $installedPath = (& adb -s $DeviceId shell pm path $PackageName 2>&1 | Out-String).Trim()
        if ($LASTEXITCODE -ne 0 -or $installedPath -notmatch '^package:') {
            throw "Expected application package '$PackageName' is not installed."
        }
        & adb -s $DeviceId shell am force-stop $PackageName | Out-Null
        & adb -s $DeviceId shell monkey -p $PackageName -c android.intent.category.LAUNCHER 1 2>&1 |
            Tee-Object -FilePath $logPath -Append
        if ($LASTEXITCODE -ne 0) { throw 'Fresh-process application launch failed.' }

        $restartDumpPath = '/sdcard/secureguide-restart.xml'
        for ($attempt = 0; $attempt -lt 20; $attempt++) {
            Start-Sleep -Seconds 1
            & adb -s $DeviceId shell uiautomator dump $restartDumpPath 2>&1 | Out-Null
            if ($LASTEXITCODE -ne 0) { continue }
            $restartXml = (& adb -s $DeviceId shell cat $restartDumpPath 2>&1 | Out-String)
            if ($LASTEXITCODE -eq 0 -and $restartXml.Contains($profileName)) {
                $processRestartPassed = $true
                break
            }
        }
        if (-not $processRestartPassed) {
            throw "Fresh process did not render persisted profile '$profileName'."
        }
    }
    finally {
        Pop-Location
    }
    $testPassed = $true
}
finally {
    Set-AirplaneMode $initialAirplane
    Set-Radio 'wifi' $initialWifi
    Set-Radio 'data' $initialData
    if (Test-Path -LiteralPath $normalApkForRestart -PathType Leaf) {
        [System.IO.File]::Delete($normalApkForRestart)
    }

    [ordered]@{
        deviceId = $DeviceId
        completedAtUtc = (Get-Date).ToUniversalTime().ToString('o')
        passed = $testPassed
        phase = 'COMPLETED_AND_NETWORK_RESTORED'
        offlineState = [ordered]@{
            airplaneMode = 1
            wifi = 0
            mobileData = 0
        }
        restoredState = [ordered]@{
            airplaneMode = $initialAirplane
            wifi = $initialWifi
            mobileData = $initialData
        }
        originalState = [ordered]@{
            airplaneMode = $initialAirplane
            wifi = $initialWifi
            mobileData = $initialData
        }
        processRestart = [ordered]@{
            passed = $processRestartPassed
            packageName = $PackageName
            profileName = $profileName
            deviceAbi = $deviceAbi
            flutterTargetPlatform = $flutterTargetPlatform
        }
        log = $logPath
    } | ConvertTo-Json -Depth 4 | Set-Content -Path $summaryPath -Encoding utf8
}

if (-not $testPassed) { throw "Offline acceptance failed. Evidence: $summaryPath" }
Write-Host "Offline acceptance passed. Evidence: $summaryPath"
