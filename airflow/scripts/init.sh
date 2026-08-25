#!/usr/bin/env bash
set -euo pipefail

mkdir -p /opt/airflow/config /opt/airflow/dags /opt/airflow/logs /opt/airflow/plugins

python - <<'PY'
import json
import os
from pathlib import Path

username = os.environ.get("INITIAL_ADMIN_USERNAME", "admin")
password = os.environ.get("INITIAL_ADMIN_PASSWORD", "")
if len(password) < 12:
    raise SystemExit("INITIAL_ADMIN_PASSWORD must contain at least 12 characters")

password_file = Path("/opt/airflow/config/simple_auth_manager_passwords.json")
password_file.write_text(json.dumps({username: password}, ensure_ascii=False), encoding="utf-8")
PY

airflow db migrate
