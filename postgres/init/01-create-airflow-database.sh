#!/usr/bin/env bash
set -euo pipefail

psql -v ON_ERROR_STOP=1 \
  --username "$DB_USER" \
  --dbname "$DB_NAME" \
  --set=airflow_password="$DB_PASSWORD" <<'SQL'
CREATE ROLE airflow LOGIN PASSWORD :'airflow_password';
SQL

createdb --username "$DB_USER" --owner airflow airflow
