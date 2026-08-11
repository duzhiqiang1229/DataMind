# DataMind Airflow DAG

当前业务调度中心只保留 `etl_dim_to_ads`。该 DAG 由业务 Airflow 主机上的
`/home/airflow/dags/etl_dim_dwd.py` 管理，不再从本仓库批量部署 DataX 或 Spark
模板，避免被删除的任务在执行“部署 DAG 模板”后重新出现。
