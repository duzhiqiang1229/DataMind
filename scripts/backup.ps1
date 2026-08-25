param(
    [string]$BackupDirectory = ""
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$composeFile = Join-Path $projectRoot "docker-compose.prod.yml"
$envPath = Join-Path $projectRoot ".env"
if (-not $BackupDirectory) { $BackupDirectory = Join-Path $projectRoot "backups" }

$dbUser = "datamind"
foreach ($line in Get-Content -LiteralPath $envPath -Encoding utf8) {
    if ($line -match '^DB_USER=(.+)$') { $dbUser = $matches[1].Trim() }
}

New-Item -ItemType Directory -Force -Path $BackupDirectory | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupFile = Join-Path $BackupDirectory "datamind-$stamp.sql"

$running = docker compose -f $composeFile ps --services --status running
if ($running -notcontains "postgres") { throw "PostgreSQL service is not running." }

docker compose -f $composeFile exec -T postgres pg_dumpall --clean --if-exists --username $dbUser |
    Set-Content -LiteralPath $backupFile -Encoding utf8
if ($LASTEXITCODE -ne 0 -or (Get-Item -LiteralPath $backupFile).Length -lt 1024) {
    Remove-Item -LiteralPath $backupFile -ErrorAction SilentlyContinue
    throw "PostgreSQL backup failed."
}

$hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $backupFile).Hash.ToLowerInvariant()
"$hash  $([IO.Path]::GetFileName($backupFile))" |
    Set-Content -LiteralPath "$backupFile.sha256" -Encoding ascii
Write-Host "Backup created: $backupFile" -ForegroundColor Green
