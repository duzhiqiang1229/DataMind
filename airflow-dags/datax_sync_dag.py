"""
DataMind DataX 同步 DAG 模板
放置位置: Airflow dags 目录 (如 /opt/airflow/dags/datax_sync_dag.py)

工作原理:
1. DataMind 后端调用 Airflow REST API POST /api/v1/dags/datax_sync/dagRuns
   传递 conf = {"task_id": "uuid", "job_json": {...DataX配置...}}
2. Airflow 解析 DAG,执行 datax_sync_task
3. datax_sync_task 将 job_json 写入临时文件,执行 datax.py
4. 执行完成后将统计信息写入 XCom
"""
from datetime import datetime, timedelta
import json
import os
import subprocess
import tempfile

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

# --- DAG 默认参数 ---
default_args = {
    "owner": "datamind",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
    "email_on_failure": False,
    "email_on_retry": False,
}

# --- DAG 定义 ---
dag = DAG(
    dag_id="datax_sync",
    default_args=default_args,
    description="DataMind DataX 数据同步任务 (由 DataMind 平台触发)",
    schedule=None,  # 不自动调度,由 DataMind REST API 触发
    start_date=days_ago(1),
    catchup=False,
    tags=["datamind", "datax", "sync"],
    params={  # 默认参数(DataMind触发时会覆盖)
        "task_id": "",
        "job_json": {},
    },
)


def execute_datax_sync(**context):
    """
    执行 DataX 同步任务。
    从 DAG run conf 中获取 job_json,写入临时文件,执行 datax.py。

    conf 结构:
    {
        "task_id": "uuid (DataMind任务ID)",
        "job_json": { ...DataX job配置... }
    }
    """
    conf = context["dag_run"].conf or {}
    job_json = conf.get("job_json", {})

    if not job_json:
        raise ValueError("Missing job_json in DAG run conf")

    # 1. 将 job_json 写入临时文件
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, prefix="datax_job_"
    ) as f:
        json.dump(job_json, f, ensure_ascii=False)
        job_file_path = f.name

    print(f"[DataX] Job file created: {job_file_path}")
    print(f"[DataX] Source -> Target: {job_json.get('job', {}).get('content', [{}])[0].get('reader', {}).get('parameter', {}).get('connection', [{}])[0].get('table', ['?'])[0]} -> {job_json.get('job', {}).get('content', [{}])[0].get('writer', {}).get('parameter', {}).get('connection', {}).get('table', '?')}")

    # 2. 执行 datax.py
    datax_home = os.environ.get("DATAX_HOME", "/opt/datax")
    datax_cmd = [f"{datax_home}/bin/datax.py", job_file_path]

    print(f"[DataX] Executing: {' '.join(datax_cmd)}")

    try:
        result = subprocess.run(
            datax_cmd,
            capture_output=True,
            text=True,
            timeout=3600,  # 1小时超时
        )

        print(f"[DataX] Return code: {result.returncode}")
        print(f"[DataX] stdout (last 2000 chars):\n{result.stdout[-2000:]}")
        if result.stderr:
            print(f"[DataX] stderr (last 1000 chars):\n{result.stderr[-1000:]}")

        # 解析 DataX 输出统计
        stats = _parse_datax_stats(result.stdout)

        # 将统计信息写入 XCom (DataMind 可通过 task instance API 获取)
        context["ti"].xcom_push(key="datax_stats", value=stats)
        context["ti"].xcom_push(key="job_file", value=job_file_path)

        if result.returncode != 0:
            raise RuntimeError(f"DataX execution failed with code {result.returncode}")

        print("[DataX] Sync completed successfully")

    finally:
        # 3. 清理临时文件
        if os.path.exists(job_file_path):
            os.unlink(job_file_path)
            print(f"[DataX] Cleaned up: {job_file_path}")


def _parse_datax_stats(stdout: str) -> dict:
    """从 DataX 输出中解析统计信息。"""
    stats = {"rows_read": 0, "rows_written": 0, "bytes_written": 0}

    for line in stdout.split("\n"):
        if "读出记录数" in line or "Total Read" in line:
            # 尝试提取数字
            import re
            nums = re.findall(r"[\d,]+", line)
            if nums:
                stats["rows_read"] = int(nums[0].replace(",", ""))

        if "写入记录数" in line or "Total Write" in line:
            import re
            nums = re.findall(r"[\d,]+", line)
            if nums:
                stats["rows_written"] = int(nums[0].replace(",", ""))

        if "写入字节" in line or "Total Write Bytes" in line:
            import re
            nums = re.findall(r"[\d,]+", line)
            if nums:
                stats["bytes_written"] = int(nums[0].replace(",", ""))

    return stats


# --- Task 定义 ---
datax_sync_task = PythonOperator(
    task_id="datax_sync_task",
    python_callable=execute_datax_sync,
    dag=dag,
)
