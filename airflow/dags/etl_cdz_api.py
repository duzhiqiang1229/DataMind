"""充电桩接口数据抽取并通过 Stream Load 写入 Doris。"""

from datetime import timedelta

import pendulum
from airflow import DAG
from airflow.providers.standard.operators.bash import BashOperator


PYTHON_BIN = "/usr/local/bin/python3"
SCRIPT_DIR = "/opt/etljob/py"
DATA_DIR = "/opt/data"
DORIS_STREAM_LOAD = "http://192.168.1.4:8040/api"

DEFAULT_ARGS = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(minutes=50),
}

JOBS = [
    ("charge_order", "chargeOrder.py", "chargeOrder.csv", "ods/ods_cdzapi_cdorders_i_d"),
    (
        "charge_order_week_statistics",
        "chargeOrderWeekStatistics.py",
        "chargeOrderWeekStatistics.csv",
        "ods/ods_cdzapi_chargeOrderWeekStatistics_i_d",
    ),
    ("device_list", "devList.py", "devList.csv", "ods/ods_cdzapi_dev_f_d"),
    ("recharge_order", "rechargeOrder.py", "rechargeOrder.csv", "ods/ods_cdzapi_czorders_i_d"),
    ("user_balance", "userBalanceList.py", "userBalanceList.csv", "ods/ods_cdzapi_users_i_d"),
    ("user_list", "userList.py", "userList.csv", "ods/ods_cdzapi_users_i_d"),
]


def extract_command(script: str, csv_file: str) -> str:
    return f"""
set -euo pipefail
cd {SCRIPT_DIR}
{PYTHON_BIN} {script}
test -s {DATA_DIR}/{csv_file}
"""


def load_command(csv_file: str, table: str) -> str:
    label_prefix = csv_file.removesuffix(".csv")
    return f"""
set -euo pipefail
test -s {DATA_DIR}/{csv_file}
response=$(curl --silent --show-error --location-trusted \
  -u root: \
  -T {DATA_DIR}/{csv_file} \
  -H 'column_separator:,' \
  -H "label:{label_prefix}_$(date +%Y%m%d%H%M%S)_{{{{ ti.try_number }}}}" \
  {DORIS_STREAM_LOAD}/{table}/_stream_load)
printf '%s\n' "$response"
printf '%s' "$response" | grep -Eq '"Status"[[:space:]]*:[[:space:]]*"Success"'
echo 'INFO - {table.replace('/', '.')}: load_completed'
"""


with DAG(
    dag_id="etl_cdz_api",
    description="充电桩订单、设备、充值和用户数据同步",
    schedule="0 8,10,13,15,17 * * *",
    start_date=pendulum.datetime(2026, 1, 1, tz="Asia/Shanghai"),
    catchup=False,
    max_active_runs=1,
    is_paused_upon_creation=True,
    default_args=DEFAULT_ARGS,
    tags=["ETL", "CDZ", "Doris"],
) as dag:
    previous = None
    for task_name, script, csv_file, table in JOBS:
        extract = BashOperator(
            task_id=f"extract_{task_name}",
            bash_command=extract_command(script, csv_file),
        )
        load = BashOperator(
            task_id=f"load_{task_name}",
            bash_command=load_command(csv_file, table),
        )
        extract >> load
        if previous is not None:
            previous >> extract
        previous = load
