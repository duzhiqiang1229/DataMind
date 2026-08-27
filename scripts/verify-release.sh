#!/usr/bin/env sh
set -eu

project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
compose_file="$project_root/docker-compose.prod.yml"
env_file="$project_root/.env"

sh "$project_root/scripts/validate-env.sh"
docker compose -f "$compose_file" config --quiet

running=$(docker compose -f "$compose_file" ps --services --status running)
for service in postgres redis backend mcp-server executor frontend cubestore cube airflow-api-server airflow-scheduler airflow-dag-processor airflow-triggerer; do
  echo "$running" | grep -qx "$service" || { echo "Service not running: $service" >&2; exit 1; }
done

env_value() { sed -n "s/^$1=//p" "$env_file" | tail -n 1; }
http_port=$(env_value DATAMIND_HTTP_PORT); http_port=${http_port:-80}
backend_port=$(env_value BACKEND_PORT); backend_port=${backend_port:-8000}
mcp_port=$(env_value MCP_PORT); mcp_port=${mcp_port:-8001}
cube_port=$(env_value CUBE_PORT); cube_port=${cube_port:-4000}
airflow_port=$(env_value AIRFLOW_PORT); airflow_port=${airflow_port:-8082}

for url in \
  "http://127.0.0.1:$http_port/" \
  "http://127.0.0.1:$backend_port/health" \
  "http://127.0.0.1:$mcp_port/health" \
  "http://127.0.0.1:$cube_port/livez" \
  "http://127.0.0.1:$airflow_port/api/v2/monitor/health"; do
  attempt=0
  until curl --fail --silent --show-error --max-time 15 "$url" >/dev/null; do
    attempt=$((attempt + 1))
    [ "$attempt" -lt 18 ] || { echo "Health check failed after 90 seconds: $url" >&2; exit 1; }
    sleep 5
  done
  echo "[OK] $url"
done

docker exec backend sh -lc 'cd /app && alembic current' | grep -q '(head)'
docker exec airflow-scheduler sh -lc 'airflow providers list | grep -q apache-airflow-providers-openlineage'
docker exec airflow-scheduler sh -lc 'test -r "$SPARK_OPENLINEAGE_JAR"'
docker exec airflow-scheduler python -c 'import sys; sys.path.insert(0, "/opt/airflow/plugins"); from datamind_operators import DorisSQLOperator, DorisSparkSubmitOperator'
docker exec airflow-scheduler sh -lc 'test "$(airflow config get-value openlineage namespace)" = datamind-airflow'
docker exec airflow-scheduler sh -lc 'test "$(airflow config get-value openlineage disabled)" = False'
docker exec airflow-scheduler python -c 'import json, os, urllib.request; request = urllib.request.Request("http://backend:8000/api/v1/internal/openlineage/health", headers={"Authorization": "Bearer " + os.environ["LINEAGE_EVENT_TOKEN"]}); assert json.load(urllib.request.urlopen(request, timeout=10))["status"] == "ok"'
version=$(tr -d '\r\n' < "$project_root/VERSION")
curl --fail --silent "http://127.0.0.1:$backend_port/health" | grep -q "\"version\":\"$version\""
echo "DataMind release $version verification passed."
