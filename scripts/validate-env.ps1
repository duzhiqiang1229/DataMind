$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $projectRoot ".env"
if (-not (Test-Path -LiteralPath $envPath)) {
    throw "Missing .env. Copy .env.example to .env first."
}

$values = @{}
foreach ($line in Get-Content -LiteralPath $envPath -Encoding utf8) {
    if ($line -match '^([A-Za-z_][A-Za-z0-9_]*)=(.*)$') {
        $values[$matches[1]] = $matches[2].Trim()
    }
}

$required = @(
    "APP_VERSION", "DATAMIND_VERSION", "INITIAL_ADMIN_PASSWORD", "EXECUTOR_TOKEN",
    "LINEAGE_EVENT_TOKEN", "JWT_SECRET_KEY", "ENCRYPTION_KEY", "CUBE_API_SECRET",
    "DB_PASSWORD", "REDIS_PASSWORD", "CUBEJS_DB_HOST", "CUBEJS_DB_USER"
)

$errors = @()
foreach ($key in $required) {
    $value = $values[$key]
    if ([string]::IsNullOrWhiteSpace($value)) {
        $errors += "$key is empty"
    } elseif ($value -like "change-me*") {
        $errors += "$key still uses a change-me placeholder"
    }
}

$adminPassword = [string]$values["INITIAL_ADMIN_PASSWORD"]
$executorToken = [string]$values["EXECUTOR_TOKEN"]
$lineageToken = [string]$values["LINEAGE_EVENT_TOKEN"]
if ($adminPassword.Length -lt 12) {
    $errors += "INITIAL_ADMIN_PASSWORD must contain at least 12 characters"
}
if ($executorToken.Length -lt 24) {
    $errors += "EXECUTOR_TOKEN must contain at least 24 characters"
}
if ($lineageToken.Length -lt 24) {
    $errors += "LINEAGE_EVENT_TOKEN must contain at least 24 characters"
}

$versionPath = Join-Path $projectRoot "VERSION"
$releaseVersion = (Get-Content -LiteralPath $versionPath -Raw).Trim()
if ($values["APP_VERSION"] -ne $releaseVersion -or $values["DATAMIND_VERSION"] -ne $releaseVersion) {
    $errors += "APP_VERSION and DATAMIND_VERSION must both match VERSION ($releaseVersion)"
}

$fernetKeys = @("ENCRYPTION_KEY")
foreach ($key in $fernetKeys) {
    $value = $values[$key]
    try {
        $decoded = [Convert]::FromBase64String($value.Replace('-', '+').Replace('_', '/'))
        if ($decoded.Length -ne 32) { $errors += "$key is not a valid 32-byte Fernet key" }
    } catch {
        $errors += "$key is not a valid URL-safe Base64 Fernet key"
    }
}
if ($errors.Count) {
    Write-Host "Configuration validation failed:" -ForegroundColor Red
    $errors | ForEach-Object { Write-Host "- $_" -ForegroundColor Red }
    exit 1
}

Write-Host "Configuration validation passed." -ForegroundColor Green
