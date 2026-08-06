# DataMind Airflow DAG 模板

## 模板文件

| 文件 | DAG ID | 用途 | 触发方式 |
|------|--------|------|---------|
| `datax_sync_dag.py` | `datax_sync` | DataX 数据同步 | DataMind REST API 传参触发 |
| `spark_job_dag.py` | `spark_job` | Spark 数据加工 | DataMind REST API 传参触发 |

## 触发方式

DataMind 后端通过 Airflow REST API 触发:

```python
# DataX 同步
airflow.trigger_dag_run(
    dag_id="datax_sync",
    conf={
        "task_id": "datamind-uuid",
        "job_json": { ...DataX job JSON... }
    }
)

# Spark 加工 (SQL 模式)
airflow.trigger_dag_run(
    dag_id="spark_job",
    conf={
        "task_id": "datamind-uuid",
        "spark_config": {
            "mode": "sql",
            "master": "spark://spark-master:7077",
            "sql_file": "/opt/spark/jobs/ods_to_dwd.sql",
            "target_table": "dwd.dwd_user_fact",
            "variables": {"run_date": "2026-08-06"},
            "executor_memory": "2g",
            ...
        }
    }
)

# Spark 加工 (PySpark 模式)
airflow.trigger_dag_run(
    dag_id="spark_job",
    conf={
        "task_id": "datamind-uuid",
        "spark_config": {
            "mode": "pyspark",
            "script_file": "/opt/spark/jobs/user_analysis.py",
            "script_args": {"date": "2026-08-06"},
            ...
        }
    }
)
```

## 执行链路

```
DataMind 配置任务 → 生成 job_json/spark_config 存入 PostgreSQL
  ↓
DataMind 调用 Airflow REST API trigger_dag_run(dag_id, conf)
  ↓
Airflow DAG 执行 datax_sync_task / spark_job_task
  ↓
Airflow 返回 dag_run_id
  ↓
DataMind 定时轮询 get_dag_run_state(dag_id, dag_run_id)
  ↓
任务完成 → DataMind 更新 task_instances.status
```

## 环境变量

DAG 文件依赖以下环境变量:

| 变量 | 默认值 | 用途 |
|------|--------|------|
| `DATAX_HOME` | `/opt/datax` | DataX 安装目录 |
| `SPARK_HOME` | `/opt/spark` | Spark 安装目录 |

## 部署

将 DAG 文件复制到 Airflow 的 dags 目录:
```bash
cp datax_sync_dag.py spark_job_dag.py /opt/airflow/dags/
```

Airflow 会自动检测并加载这两个 DAG。DataMind 通过 REST API 触发,不需要 Airflow 自动调度。
