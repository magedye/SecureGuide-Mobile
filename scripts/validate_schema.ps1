$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$dbPath = Join-Path $projectRoot 'secureguide_test.db'
$schemaPath = Join-Path $projectRoot 'migrations\001_initial_schema.sql'

function Invoke-Sqlite([string]$sql) {
    # Pipe SQL to sqlite3 to avoid nested-quote issues
    $sql | & sqlite3 $dbPath 2>&1
}

if (Test-Path $dbPath) { Remove-Item $dbPath -Force }

Write-Host "Creating database and applying schema..."
Get-Content -Raw $schemaPath | & sqlite3 $dbPath
if ($LASTEXITCODE -ne 0) { throw "Failed to create schema." }

Write-Host "Running Integrity Check..."
$integrity = Invoke-Sqlite "PRAGMA integrity_check;"
if ($integrity -ne 'ok') { throw "Integrity check failed: $integrity" }

Write-Host "Testing valid inserts..."
Invoke-Sqlite "INSERT INTO source_catalogs (id, name) VALUES ('cat-1', 'CIS');"
Invoke-Sqlite "INSERT INTO security_artifacts (id, source_catalog_id, title_short, definition_short, type, primary_domain, sub_domain) VALUES ('art-1', 'cat-1', 'Title', 'Def', 'ART-CTR', 'SD-01', 'SD-01.01');"
Invoke-Sqlite "INSERT INTO enterprise_profiles (id, name) VALUES ('prof-1', 'My Org');"
Invoke-Sqlite "INSERT INTO profile_artifacts (id, profile_id, artifact_id, implementation_status) VALUES ('pa-1', 'prof-1', 'art-1', 'STS-FULL');"

Write-Host "Testing invalid enums (should fail)..."
$err1 = Invoke-Sqlite "INSERT INTO security_artifacts (id, source_catalog_id, title_short, definition_short, type, primary_domain, sub_domain) VALUES ('art-2', 'cat-1', 'T', 'D', 'ART-INVALID', 'SD-01', 'SD-01.01');"
if ($err1 -notmatch "CHECK constraint failed") { throw "Failed to catch invalid type: $err1" }

$err2 = Invoke-Sqlite "INSERT INTO artifact_tags (artifact_id, tag_type, tag_value) VALUES ('art-1', 'INVALID_TAG', 'Val');"
if ($err2 -notmatch "CHECK constraint failed") { throw "Failed to catch invalid tag_type: $err2" }

$err3 = Invoke-Sqlite "INSERT INTO security_artifacts (id, source_catalog_id, title_short, definition_short, type, primary_domain, sub_domain) VALUES ('art-3', 'cat-1', 'T', 'D', 'ART-REQ', 'SD-01', 'SD-01.99');"
if ($err3 -notmatch "CHECK constraint failed") { throw "Failed to catch invalid sub_domain: $err3" }

Write-Host "Validation Passed Successfully!"
