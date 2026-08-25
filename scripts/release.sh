#!/usr/bin/env sh
set -eu

project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
compose_file="$project_root/docker-compose.prod.yml"

sh "$project_root/scripts/validate-env.sh"
if docker compose -f "$compose_file" ps --services --status running | grep -qx postgres; then
  sh "$project_root/scripts/backup.sh"
fi
docker compose -f "$compose_file" config --quiet
docker compose -f "$compose_file" pull postgres redis cubestore cube
docker compose -f "$compose_file" build --pull airflow-init backend frontend
docker compose -f "$compose_file" up -d --remove-orphans
sh "$project_root/scripts/verify-release.sh"
