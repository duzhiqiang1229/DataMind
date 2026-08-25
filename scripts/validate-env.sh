#!/usr/bin/env sh
set -eu

project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
env_file="$project_root/.env"
test -f "$env_file" || { echo "Missing .env. Copy .env.example to .env first." >&2; exit 1; }

required='APP_VERSION DATAMIND_VERSION INITIAL_ADMIN_PASSWORD EXECUTOR_TOKEN LINEAGE_EVENT_TOKEN JWT_SECRET_KEY ENCRYPTION_KEY CUBE_API_SECRET DB_PASSWORD REDIS_PASSWORD CUBEJS_DB_HOST CUBEJS_DB_USER'
failed=0
for key in $required; do
  value=$(sed -n "s/^${key}=//p" "$env_file" | tail -n 1)
  if [ -z "$value" ]; then
    echo "- $key is empty" >&2
    failed=1
  elif echo "$value" | grep -q '^change-me'; then
    echo "- $key still uses a change-me placeholder" >&2
    failed=1
  fi
done

release_version=$(tr -d '\r\n' < "$project_root/VERSION")
app_version=$(sed -n 's/^APP_VERSION=//p' "$env_file" | tail -n 1)
image_version=$(sed -n 's/^DATAMIND_VERSION=//p' "$env_file" | tail -n 1)
if [ "$app_version" != "$release_version" ] || [ "$image_version" != "$release_version" ]; then
  echo "- APP_VERSION and DATAMIND_VERSION must both match VERSION ($release_version)" >&2
  failed=1
fi

for key in INITIAL_ADMIN_PASSWORD EXECUTOR_TOKEN LINEAGE_EVENT_TOKEN; do
  value=$(sed -n "s/^${key}=//p" "$env_file" | tail -n 1)
  minimum=24
  [ "$key" = "INITIAL_ADMIN_PASSWORD" ] && minimum=12
  length=$(printf '%s' "$value" | wc -c | tr -d ' ')
  if [ "$length" -lt "$minimum" ]; then
    echo "- $key must contain at least $minimum characters" >&2
    failed=1
  fi
done

[ "$failed" -eq 0 ] || { echo "Configuration validation failed." >&2; exit 1; }
echo "Configuration validation passed."
