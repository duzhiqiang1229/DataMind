"""充电桩端口实时状态抽取并通过 Stream Load 写入 Doris。"""

from datetime import timedelta

import pendulum
from airflow import DAG
from airflow.providers.standard.operators.bash import BashOperator


DEFAULT_ARGS = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(minutes=45),
}


with DAG(
    dag_id="etl_cdz_device_port",
    description="充电桩端口实时状态每小时同步",
    schedule="0 * * * *",
    start_date=pendulum.datetime(2026, 1, 1, tz="Asia/Shanghai"),
    catchup=False,
    max_active_runs=1,
    is_paused_upon_creation=True,
    default_args=DEFAULT_ARGS,
    tags=["ETL", "CDZ", "Doris"],
) as dag:
    extract_device_port = BashOperator(
        task_id="extract_device_port",
        bash_command="""
set -euo pipefail
cd /opt/etljob/py
/usr/local/bin/python3 devList_real.py
test -s /opt/data/devList_real.csv
""",
    )

    load_device_port = BashOperator(
        task_id="load_device_port",
        bash_command="""
set -euo pipefail
test -s /opt/data/devList_real.csv
response=$(curl --silent --show-error --location-trusted \
  -u root: \
  -T /opt/data/devList_real.csv \
  -H 'column_separator:,' \
  -H "label:devList_real_$(date +%Y%m%d%H%M%S)_{{ ti.try_number }}" \
  http://192.168.1.4:8040/api/ods/ods_cdzapi_devportreal_f_d/_stream_load)
printf '%s\n' "$response"
printf '%s' "$response" | grep -Eq '"Status"[[:space:]]*:[[:space:]]*"Success"'
echo 'INFO - ods.ods_cdzapi_devportreal_f_d: load_completed'
""",
    )

    extract_device_port >> load_device_port
