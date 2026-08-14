param(
    [Parameter(Mandatory = $true)]
    [string]$SignedApk,
    [Parameter(Mandatory = $true)]
    [string]$ApplicationId,
    [Parameter(Mandatory = $true)]
    [string]$ExpectedCertificateSha256,
    [string]$DeviceId,
    [string]$EvidenceDirectory = ""
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$apkPath = [System.IO.Path]::GetFullPath($SignedApk)
if (-not (Test-Path -LiteralPath $apkPath -PathType Leaf)) {
    throw "Signed APK not found: $apkPath"
}
if ($ApplicationId -notmatch '^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z][A-Za-z0-9_]*)+$') {
    throw 'ApplicationId is invalid.'
}
$expectedCertificate = ($ExpectedCertificateSha256 -replace ':', '').ToLowerInvariant()
if ($expectedCertificate -notmatch '^[0-9a-f]{64}$') {
    throw 'ExpectedCertificateSha256 must be exactly 32 SHA-256 bytes in hexadecimal.'
}
if ([string]::IsNullOrWhiteSpace($EvidenceDirectory)) {
    $EvidenceDirectory = Join-Path $PSScriptRoot '..\build\installation-evidence'
}
$evidenceRoot = [System.IO.Path]::GetFullPath($EvidenceDirectory)
New-Item -ItemType Directory -Path $evidenceRoot -Force | Out-Null

$sdkRoot = $env:ANDROID_SDK_ROOT
if ([string]::IsNullOrWhiteSpace($sdkRoot)) { $sdkRoot = $env:ANDROID_HOME }
if ([string]::IsNullOrWhiteSpace($sdkRoot)) {
    $localProperties = Join-Path $PSScriptRoot '..\android\local.properties'
    if (Test-Path -LiteralPath $localProperties -PathType Leaf) {
        $sdkProperty = Get-Content -LiteralPath $localProperties |
            Where-Object { $_ -match '^sdk\.dir=' } |
            Select-Object -First 1
        if ($null -ne $sdkProperty) {
            $sdkRoot = ($sdkProperty -replace '^sdk\.dir=', '') -replace '\\\\', '\'
        }
    }
}
if ([string]::IsNullOrWhiteSpace($sdkRoot) -or -not (Test-Path -LiteralPath $sdkRoot -PathType Container)) {
    throw 'A valid Android SDK is required through ANDROID_SDK_ROOT, ANDROID_HOME, or android/local.properties.'
}
$buildTools = Get-ChildItem -LiteralPath (Join-Path $sdkRoot 'build-tools') -Directory |
    Sort-Object { [version]$_.Name } -Descending
if ($buildTools.Count -eq 0) { throw 'Android SDK build-tools are unavailable.' }
$apksigner = Join-Path $buildTools[0].FullName 'apksigner.bat'
if (-not (Test-Path -LiteralPath $apksigner)) {
    $apksigner = Join-Path $buildTools[0].FullName 'apksigner'
}
if (-not (Test-Path -LiteralPath $apksigner)) { throw 'apksigner is unavailable.' }
$apkanalyzer = Join-Path $sdkRoot 'cmdline-tools\latest\bin\apkanalyzer.bat'
if (-not (Test-Path -LiteralPath $apkanalyzer -PathType Leaf)) {
    $apkanalyzer = Get-ChildItem -LiteralPath (Join-Path $sdkRoot 'cmdline-tools') `
        -Recurse -File -Filter 'apkanalyzer*' -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -in @('apkanalyzer', 'apkanalyzer.bat') } |
        Sort-Object FullName -Descending |
        Select-Object -First 1 -ExpandProperty FullName
}
if ([string]::IsNullOrWhiteSpace($apkanalyzer) -or -not (Test-Path -LiteralPath $apkanalyzer -PathType Leaf)) {
    throw 'apkanalyzer is unavailable.'
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

$stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
$signaturePath = Join-Path $evidenceRoot "signature-$stamp.txt"
$summaryPath = Join-Path $evidenceRoot "installation-$stamp.json"
$signatureOutput = @(& $apksigner verify --verbose --print-certs $apkPath 2>&1)
$signatureExit = $LASTEXITCODE
$signatureOutput | Set-Content -LiteralPath $signaturePath -Encoding utf8
if ($signatureExit -ne 0) { throw 'APK signature verification failed.' }
$certificateMatch = [regex]::Match(
    ($signatureOutput -join "`n"),
    '(?im)^Signer #\d+ certificate SHA-256 digest:\s*([0-9a-f:]+)\s*$'
)
if (-not $certificateMatch.Success) { throw 'APK signing certificate SHA-256 could not be read.' }
$actualCertificate = ($certificateMatch.Groups[1].Value -replace ':', '').ToLowerInvariant()
if ($actualCertificate -cne $expectedCertificate) {
    throw "APK certificate SHA-256 '$actualCertificate' does not match the approved certificate."
}

$applicationIdOutput = @(& $apkanalyzer manifest application-id $apkPath 2>&1)
$applicationIdExit = $LASTEXITCODE
$apkApplicationId = $applicationIdOutput |
    ForEach-Object { $_.ToString().Trim() } |
    Where-Object { $_ -match '^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z][A-Za-z0-9_]*)+$' } |
    Select-Object -Last 1
if ($applicationIdExit -ne 0 -or [string]::IsNullOrWhiteSpace($apkApplicationId)) {
    throw 'APK application ID could not be read.'
}
if ($apkApplicationId -cne $ApplicationId) {
    throw "APK application ID '$apkApplicationId' does not match expected '$ApplicationId'."
}

$beforePath = (& adb -s $DeviceId shell pm path $ApplicationId 2>$null | Out-String).Trim()
& adb -s $DeviceId install -r $apkPath
if ($LASTEXITCODE -ne 0) { throw 'APK installation failed.' }
$afterPath = (& adb -s $DeviceId shell pm path $ApplicationId | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $afterPath -notmatch '^package:') {
    throw 'Installed package could not be verified.'
}
& adb -s $DeviceId shell am force-stop $ApplicationId | Out-Null
$resolvedActivity = (& adb -s $DeviceId shell cmd package resolve-activity --brief $ApplicationId 2>&1 | Out-String).Trim()
$escapedApplicationId = [regex]::Escape($ApplicationId)
if ($LASTEXITCODE -ne 0 -or $resolvedActivity -notmatch "^$escapedApplicationId/") {
    throw 'Installed application has no launchable activity for the expected package.'
}
$launchOutput = (& adb -s $DeviceId shell am start -W -n $resolvedActivity 2>&1 | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $launchOutput -notmatch '(?m)^Status:\s+ok\s*$') {
    throw 'Installed application could not be launched successfully.'
}

$hash = (Get-FileHash -LiteralPath $apkPath -Algorithm SHA256).Hash.ToLowerInvariant()
[ordered]@{
    applicationId = $ApplicationId
    deviceId = $DeviceId
    verifiedAtUtc = (Get-Date).ToUniversalTime().ToString('o')
    apkPath = $apkPath
    apkSha256 = $hash
    apkApplicationId = $apkApplicationId
    certificateSha256 = $actualCertificate
    packageBeforeInstall = $beforePath
    packageAfterInstall = $afterPath
    resolvedActivity = $resolvedActivity
    signatureEvidence = $signaturePath
    installationPassed = $true
} | ConvertTo-Json -Depth 3 | Set-Content -Path $summaryPath -Encoding utf8

Write-Host "Signed installation verified. Evidence: $summaryPath"
