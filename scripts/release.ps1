$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$composeFile = Join-Path $projectRoot "docker-compose.prod.yml"

& (Join-Path $PSScriptRoot "validate-env.ps1")
$running = @(docker compose -f $composeFile ps --services --status running)
if ("postgres" -in $running) { & (Join-Path $PSScriptRoot "backup.ps1") }

docker compose -f $composeFile config --quiet
docker compose -f $composeFile pull postgres redis cubestore cube
docker compose -f $composeFile build --pull airflow-init backend frontend
docker compose -f $composeFile up -d --remove-orphans
& (Join-Path $PSScriptRoot "verify-release.ps1")
