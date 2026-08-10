"""
DataMind Spark 作业 DAG 模板
放置位置: Airflow dags 目录 (如 /opt/airflow/dags/spark_job_dag.py)

工作原理:
1. DataMind 后端调用 Airflow REST API POST /api/v1/dags/spark_job/dagRuns
   传递 conf = {"task_id": "uuid", "spark_config": {...Spark提交配置...}}
2. Airflow 根据 conf.mode 选择执行 SQL 或 PySpark
3. SQL 模式: spark-sql 执行 .sql 文件,结果写入 Doris
4. PySpark 模式: spark-submit 执行 .py 脚本
"""
from datetime import timedelta
import json
import os
import subprocess

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

default_args = {
    "owner": "datamind",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
    "email_on_retry": False,
}

dag = DAG(
    dag_id="spark_job",
    default_args=default_args,
    description="DataMind Spark 数据加工任务 (由 DataMind 平台触发)",
    schedule=None,
    start_date=days_ago(1),
    catchup=False,
    tags=["datamind", "spark", "transform"],
    params={
        "task_id": "",
        "spark_config": {},
    },
)


def execute_spark_job(**context):
    """
    执行 Spark 作业。
    根据 spark_config.mode 选择执行模式:
    - sql:     spark-sql 执行 SQL 文件,结果写入 Doris
    - pyspark: spark-submit 执行 PySpark 脚本

    conf 结构:
    {
        "task_id": "uuid (DataMind任务ID)",
        "spark_config": {
            "mode": "sql" | "pyspark",
            "master": "spark://spark-master:7077",
            "deploy_mode": "client",
            "sql_file": "/path/to/transform.sql",     # sql 模式
            "script_file": "/path/to/job.py",          # pyspark 模式
            "target_table": "dwd.dwd_user_fact",
            "variables": {"run_date": "2026-08-06"},
            "executor_memory": "2g",
            "executor_cores": 2,
            "num_executors": 3,
            "jars": "/opt/spark/jars/doris-spark-connector.jar",
            "conf": {"spark.sql.shuffle.partitions": "200"},
            "script_args": {"arg1": "val1"},           # pyspark 模式
            "py_files": []
        }
    }
    """
    conf = context["dag_run"].conf or {}
    spark_config = conf.get("spark_config", {})

    if not spark_config:
        raise ValueError("Missing spark_config in DAG run conf")

    mode = spark_config.get("mode", "sql")
    master = spark_config.get("master", "spark://spark-master:7077")
    deploy_mode = spark_config.get("deploy_mode", "client")
    executor_memory = spark_config.get("executor_memory", "2g")
    executor_cores = spark_config.get("executor_cores", 2)
    num_executors = spark_config.get("num_executors", 3)
    jars = spark_config.get("jars", "")
    spark_conf = spark_config.get("conf", {})

    # --- 构建 spark-submit 基础命令 ---
    spark_home = os.environ.get("SPARK_HOME", "/home/spark")
    cmd = [f"{spark_home}/bin/spark-submit"]

    # Master & deploy mode
    cmd.extend(["--master", master])
    if deploy_mode:
        cmd.extend(["--deploy-mode", deploy_mode])

    # Resource config
    cmd.extend([
        f"--executor-memory", executor_memory,
        f"--executor-cores", str(executor_cores),
        f"--num-executors", str(num_executors),
    ])

    # Jars
    if jars:
        cmd.extend(["--jars", jars])

    # Spark conf
    for key, value in spark_conf.items():
        cmd.extend(["--conf", f"{key}={value}"])

    if mode == "sql":
        # --- SQL 模式: 使用 spark-sql ---
        sql_file = spark_config["sql_file"]
        target_table = spark_config.get("target_table", "")
        variables = spark_config.get("variables", {})

        if not os.path.exists(sql_file):
            raise FileNotFoundError(f"SQL file not found: {sql_file}")

        # 读取 SQL 内容
        with open(sql_file, "r", encoding="utf-8") as f:
            sql_content = f.read()

        # 变量替换
        for key, value in variables.items():
            sql_content = sql_content.replace(f"${{{key}}}", str(value))

        print(f"[Spark] SQL mode: {sql_file} -> {target_table}")

        # 写入处理后的 SQL 到临时文件
        import tempfile
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".sql", delete=False, prefix="spark_job_"
        ) as f:
            f.write(sql_content)
            tmp_sql = f.name

        # 使用 spark-sql 执行
        cmd = [f"{spark_home}/bin/spark-sql"]
        cmd.extend(["--master", master])
        if deploy_mode:
            cmd.extend(["--deploy-mode", deploy_mode])
        cmd.extend([
            f"--executor-memory", executor_memory,
            f"--executor-cores", str(executor_cores),
            f"--num-executors", str(num_executors),
        ])
        if jars:
            cmd.extend(["--jars", jars])
        for key, value in spark_conf.items():
            cmd.extend(["--conf", f"{key}={value}"])
        cmd.extend(["-f", tmp_sql])

        print(f"[Spark] Executing: {' '.join(cmd)}")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=7200)
            print(f"[Spark] Return code: {result.returncode}")
            print(f"[Spark] stdout (last 2000):\n{result.stdout[-2000:]}")
            if result.stderr:
                print(f"[Spark] stderr (last 1000):\n{result.stderr[-1000:]}")

            if result.returncode != 0:
                raise RuntimeError(f"Spark SQL failed with code {result.returncode}")
        finally:
            os.unlink(tmp_sql)

    elif mode == "pyspark":
        # --- PySpark 模式: spark-submit 执行 .py ---
        script_file = spark_config["script_file"]
        script_args = spark_config.get("script_args", {})
        py_files = spark_config.get("py_files", [])

        if not os.path.exists(script_file):
            raise FileNotFoundError(f"Script file not found: {script_file}")

        if py_files:
            cmd.extend(["--py-files", ",".join(py_files)])

        cmd.append(script_file)

        # 传入参数
        for key, value in script_args.items():
            cmd.extend([f"--{key}", str(value)])

        print(f"[Spark] PySpark mode: {script_file}")
        print(f"[Spark] Executing: {' '.join(cmd)}")

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=7200)
        print(f"[Spark] Return code: {result.returncode}")
        print(f"[Spark] stdout (last 2000):\n{result.stdout[-2000:]}")
        if result.stderr:
            print(f"[Spark] stderr (last 1000):\n{result.stderr[-1000:]}")

        if result.returncode != 0:
            raise RuntimeError(f"PySpark failed with code {result.returncode}")
    else:
        raise ValueError(f"Unsupported Spark mode: {mode}")

    print("[Spark] Job completed successfully")

    # 将结果写入 XCom
    context["ti"].xcom_push(key="spark_result", value={
        "mode": mode,
        "return_code": result.returncode,
    })


# --- Task 定义 ---
spark_job_task = PythonOperator(
    task_id="spark_job_task",
    python_callable=execute_spark_job,
    dag=dag,
)
