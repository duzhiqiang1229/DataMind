#!/usr/bin/env sh
set -eu

project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
compose_file="$project_root/docker-compose.prod.yml"
env_file="$project_root/.env"
backup_dir=${1:-"$project_root/backups"}
db_user=$(sed -n 's/^DB_USER=//p' "$env_file" | tail -n 1)
stamp=$(date '+%Y%m%d-%H%M%S')
backup_file="$backup_dir/datamind-$stamp.sql"

mkdir -p "$backup_dir"
docker compose -f "$compose_file" ps --services --status running | grep -qx postgres || {
  echo "PostgreSQL service is not running." >&2
  exit 1
}
docker compose -f "$compose_file" exec -T postgres \
  pg_dumpall --clean --if-exists --username "$db_user" > "$backup_file"
test "$(wc -c < "$backup_file")" -ge 1024 || {
  rm -f "$backup_file"
  echo "PostgreSQL backup failed." >&2
  exit 1
}
(cd "$backup_dir" && sha256sum "$(basename "$backup_file")" > "$(basename "$backup_file").sha256")
echo "Backup created: $backup_file"
