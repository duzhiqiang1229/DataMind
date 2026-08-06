"""
Spark job config generator.
Generates Spark submission configuration from DataMind task config stored in PostgreSQL.
Does NOT execute Spark — execution is delegated to Airflow DAG.

Supports two modes:
1. SQL mode: Execute Spark SQL files (ODS->DWD->DWS->ADS transformations)
2. PySpark mode: Execute PySpark script files
"""
from typing import Any
from loguru import logger


class SparkConfigGenerator:
    """
    Generates Spark submission config from DataMind task configuration.

    The generated config is stored in the database and passed to Airflow DAG
    at trigger time. Airflow DAG calls spark-submit with these parameters.
    """

    def generate_sql_config(
        self,
        sql_file_path: str,
        target_table: str,
        spark_options: dict,
        variables: dict | None = None,
    ) -> dict:
        """
        Generate config for Spark SQL execution.

        Args:
            sql_file_path: Path to the .sql file on the Spark worker
            target_table: Target Doris table for result (e.g. 'dwd.dwd_user_fact')
            spark_options: {
                "master": "spark://spark-master:7077",
                "deploy_mode": "client",
                "executor_memory": "2g",
                "executor_cores": 2,
                "num_executors": 3,
                "jars": "/opt/spark/jars/doris-spark-connector.jar",
                "conf": {"spark.sql.shuffle.partitions": "200"}
            }
            variables: Variable substitution map for SQL (e.g. {"run_date": "2026-08-06"})

        Returns:
            Spark submission config dict (stored in DB, passed to Airflow DAG)
        """
        config = {
            "mode": "sql",
            "master": spark_options.get("master", "spark://spark-master:7077"),
            "deploy_mode": spark_options.get("deploy_mode", "client"),
            "sql_file": sql_file_path,
            "target_table": target_table,
            "variables": variables or {},
            "executor_memory": spark_options.get("executor_memory", "2g"),
            "executor_cores": spark_options.get("executor_cores", 2),
            "num_executors": spark_options.get("num_executors", 3),
            "jars": spark_options.get("jars", ""),
            "conf": spark_options.get("conf", {}),
        }
        logger.info(f"Spark SQL config generated: {sql_file_path} -> {target_table}")
        return config

    def generate_pyspark_config(
        self,
        script_file_path: str,
        spark_options: dict,
        script_args: dict | None = None,
    ) -> dict:
        """
        Generate config for PySpark script execution.

        Args:
            script_file_path: Path to the .py file on the Spark worker
            spark_options: Same as generate_sql_config
            script_args: Arguments passed to the PySpark script

        Returns:
            Spark submission config dict
        """
        config = {
            "mode": "pyspark",
            "master": spark_options.get("master", "spark://spark-master:7077"),
            "deploy_mode": spark_options.get("deploy_mode", "client"),
            "script_file": script_file_path,
            "script_args": script_args or {},
            "executor_memory": spark_options.get("executor_memory", "2g"),
            "executor_cores": spark_options.get("executor_cores", 2),
            "num_executors": spark_options.get("num_executors", 3),
            "jars": spark_options.get("jars", ""),
            "conf": spark_options.get("conf", {}),
            "py_files": spark_options.get("py_files", []),
        }
        logger.info(f"PySpark config generated: {script_file_path}")
        return config


# Singleton
spark_config_gen = SparkConfigGenerator()
