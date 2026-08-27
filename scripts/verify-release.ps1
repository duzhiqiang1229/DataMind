$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$composeFile = Join-Path $projectRoot "docker-compose.prod.yml"
$envPath = Join-Path $projectRoot ".env"

& (Join-Path $PSScriptRoot "validate-env.ps1")
docker compose -f $composeFile config --quiet
if ($LASTEXITCODE -ne 0) { throw "Docker Compose configuration validation failed." }

$requiredServices = @(
    "postgres", "redis", "backend", "mcp-server", "executor", "frontend",
    "cubestore", "cube", "airflow-api-server", "airflow-scheduler",
    "airflow-dag-processor", "airflow-triggerer"
)
$running = @(docker compose -f $composeFile ps --services --status running)
$missing = @($requiredServices | Where-Object { $_ -notin $running })
if ($missing.Count) { throw "Services not running: $($missing -join ', ')" }

$values = @{}
foreach ($line in Get-Content -LiteralPath $envPath -Encoding utf8) {
    if ($line -match '^([A-Za-z_][A-Za-z0-9_]*)=(.*)$') { $values[$matches[1]] = $matches[2].Trim() }
}
function Env-Port([string]$Name, [int]$Default) {
    if ($values.ContainsKey($Name) -and $values[$Name]) { return [int]$values[$Name] }
    return $Default
}

$checks = @(
    @{ Name = "frontend"; Url = "http://127.0.0.1:$(Env-Port 'DATAMIND_HTTP_PORT' 80)/" },
    @{ Name = "backend"; Url = "http://127.0.0.1:$(Env-Port 'BACKEND_PORT' 8000)/health" },
    @{ Name = "mcp"; Url = "http://127.0.0.1:$(Env-Port 'MCP_PORT' 8001)/health" },
    @{ Name = "cube"; Url = "http://127.0.0.1:$(Env-Port 'CUBE_PORT' 4000)/livez" },
    @{ Name = "airflow"; Url = "http://127.0.0.1:$(Env-Port 'AIRFLOW_PORT' 8082)/api/v2/monitor/health" }
)
foreach ($check in $checks) {
    $response = $null
    $lastError = $null
    for ($attempt = 1; $attempt -le 18; $attempt++) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $check.Url -TimeoutSec 15
            if ($response.StatusCode -eq 200) { break }
        } catch {
            $lastError = $_
        }
        Start-Sleep -Seconds 5
    }
    if ($null -eq $response -or $response.StatusCode -ne 200) {
        throw "$($check.Name) health check failed after 90 seconds: $lastError"
    }
    Write-Host "[OK] $($check.Name) $($check.Url)"
}

$migration = (docker exec backend sh -lc "cd /app && alembic current" 2>&1 | Out-String)
if ($LASTEXITCODE -ne 0 -or $migration -notmatch '\(head\)') {
    throw "DataMind database migration is not at Alembic head."
}

docker exec airflow-scheduler sh -lc "airflow providers list | grep -q apache-airflow-providers-openlineage"
if ($LASTEXITCODE -ne 0) { throw "Airflow OpenLineage provider is not installed." }
docker exec airflow-scheduler sh -lc 'test -r "$SPARK_OPENLINEAGE_JAR"'
if ($LASTEXITCODE -ne 0) { throw "Spark OpenLineage listener JAR is missing." }
docker exec airflow-scheduler python -c 'import sys; sys.path.insert(0, "/opt/airflow/plugins"); from datamind_operators import DorisSQLOperator, DorisSparkSubmitOperator'
if ($LASTEXITCODE -ne 0) { throw "DataMind Doris OpenLineage operators cannot be imported." }
$lineageNamespace = (docker exec airflow-scheduler airflow config get-value openlineage namespace 2>&1 | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $lineageNamespace -ne "datamind-airflow") {
    throw "Airflow OpenLineage namespace is not configured."
}
$lineageDisabled = (docker exec airflow-scheduler airflow config get-value openlineage disabled 2>&1 | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $lineageDisabled -ne "False") {
    throw "Airflow OpenLineage listener is disabled."
}
docker exec airflow-scheduler python -c 'import json, os, urllib.request; request = urllib.request.Request("http://backend:8000/api/v1/internal/openlineage/health", headers={"Authorization": "Bearer " + os.environ["LINEAGE_EVENT_TOKEN"]}); assert json.load(urllib.request.urlopen(request, timeout=10))["status"] == "ok"'
if ($LASTEXITCODE -ne 0) { throw "Airflow cannot authenticate to the DataMind OpenLineage receiver." }

$version = (Get-Content -LiteralPath (Join-Path $projectRoot "VERSION") -Raw).Trim()
$health = Invoke-RestMethod -Uri "http://127.0.0.1:$(Env-Port 'BACKEND_PORT' 8000)/health" -TimeoutSec 15
if ($health.version -ne $version) { throw "Backend version $($health.version) does not match release $version." }
Write-Host "DataMind release $version verification passed." -ForegroundColor Green
