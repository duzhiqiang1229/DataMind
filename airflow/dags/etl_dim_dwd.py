"""每日 DIM -> DWD -> DWS 数据仓库刷新 DAG。"""

from datetime import timedelta

import pendulum
from airflow import DAG
from airflow.providers.standard.operators.empty import EmptyOperator

from datamind_operators import DorisSQLOperator, DorisSparkSubmitOperator


DORIS_CONN_ID = "doris_fe"
DIM_SQL_DIR = "/opt/etljob/etl/dim"
DWD_JOB_DIR = "/opt/etljob/etl/dwd"
DWS_JOB_DIR = "/opt/etljob/etl/dws"
SPARK_CONN_ID = "spark_default"

DATASOURCE_MAPPING = {
    "ods": "数仓_ods",
    "dim": "数仓_dim",
    "dwd": "数仓_dwd",
    "dws": "数仓_dws",
}

COMMON_DIM_INPUTS = [
    "dim.dim_community",
    "dim.dim_room",
    "dim.dim_customer",
    "dim.dim_costitem",
]

DEFAULT_ARGS = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(hours=2),
}


def dim_task(
    task_id: str,
    sql_file: str,
    input_tables: list[str],
    output_table: str,
) -> DorisSQLOperator:
    return DorisSQLOperator(
        task_id=task_id,
        conn_id=DORIS_CONN_ID,
        sql=sql_file,
        split_statements=True,
        autocommit=True,
        input_tables=input_tables,
        output_tables=[output_table],
        datasource_mapping=DATASOURCE_MAPPING,
    )


def spark_task(
    task_id: str,
    job_dir: str,
    script_file: str,
    common_file: str,
    input_tables: list[str],
    output_table: str,
) -> DorisSparkSubmitOperator:
    return DorisSparkSubmitOperator(
        task_id=task_id,
        conn_id=SPARK_CONN_ID,
        application=f"{job_dir}/{script_file}",
        py_files=f"{job_dir}/{common_file}",
        input_tables=input_tables,
        output_tables=[output_table],
        datasource_mapping=DATASOURCE_MAPPING,
        total_executor_cores=8,
        executor_cores=8,
        driver_memory="4g",
        executor_memory="4g",
        conf={
            "spark.ui.showConsoleProgress": "false",
            "spark.sql.adaptive.enabled": "true",
            "spark.driver.host": "172.21.0.10",
            "spark.driver.bindAddress": "0.0.0.0",
        },
        env_vars={
            "DORIS_SINK_PARTITIONS": "8",
            "DORIS_SINK_BATCH_SIZE": "100000",
        },
        verbose=False,
    )


def dwd_task(
    task_id: str,
    script_file: str,
    source_table: str,
    output_table: str,
    extra_inputs: list[str] | None = None,
) -> DorisSparkSubmitOperator:
    return spark_task(
        task_id,
        DWD_JOB_DIR,
        script_file,
        "_dwd_common.py",
        [source_table, *COMMON_DIM_INPUTS, *(extra_inputs or [])],
        output_table,
    )


def dws_task(
    task_id: str,
    script_file: str,
    input_tables: list[str],
    output_table: str,
) -> DorisSparkSubmitOperator:
    return spark_task(
        task_id,
        DWS_JOB_DIR,
        script_file,
        "_dws_common.py",
        input_tables,
        output_table,
    )


with DAG(
    dag_id="etl_dim_to_ads",
    description="每天 07:00 刷新 Doris DIM，并以 8 核依次装载 DWD、DWS",
    default_args=DEFAULT_ARGS,
    start_date=pendulum.datetime(2026, 8, 14, tz="Asia/Shanghai"),
    schedule="0 7 * * *",
    catchup=False,
    max_active_runs=1,
    max_active_tasks=8,
    dagrun_timeout=timedelta(hours=4),
    template_searchpath=[DIM_SQL_DIR],
    tags=["etl", "doris", "dim", "dwd", "dws", "spark", "lineage"],
) as dag:
    start = EmptyOperator(task_id="dim_start")

    dim_tasks = [
        dim_task("dim_costitem", "load_dim_costitem.sql", ["ods.ods_erp_tb_hspr_costitem"], "dim.dim_costitem"),
        dim_task(
            "dim_coststandard",
            "load_dim_coststandard.sql",
            ["ods.ods_erp_tb_hspr_coststandard", "ods.ods_erp_tb_hspr_costitem"],
            "dim.dim_coststandard",
        ),
        dim_task("dim_customer", "load_dim_customer.sql", ["ods.ods_erp_tb_hspr_customer"], "dim.dim_customer"),
        dim_task(
            "dim_incidenttype",
            "load_dim_incidenttype.sql",
            ["ods.ods_erp_tb_hspr_corpincidenttype"],
            "dim.dim_incidenttype",
        ),
        dim_task("dim_parking", "load_dim_parking.sql", ["ods.ods_erp_tb_hspr_parking"], "dim.dim_parking"),
        dim_task(
            "dim_room",
            "load_dim_room.sql",
            ["ods.ods_erp_tb_hspr_room", "ods.ods_erp_tb_hspr_building"],
            "dim.dim_room",
        ),
    ]

    dim_complete = EmptyOperator(task_id="dim_complete")

    dwd_tasks = [
        dwd_task(
            "dwd_fee_fees",
            "load_dwd_fee_fees_df.py",
            "ods.ods_erp_tb_hspr_fees_f_d",
            "dwd.dwd_fee_fees_df",
            ["dim.dim_coststandard", "dim.dim_parking"],
        ),
        dwd_task(
            "dwd_fee_feesdetail",
            "load_dwd_fee_feesdetail_df.py",
            "ods.ods_erp_tb_hspr_feesdetail_f_d",
            "dwd.dwd_fee_feesdetail_df",
        ),
        dwd_task(
            "dwd_fee_precostsdetail",
            "load_dwd_fee_precostsdetail_df.py",
            "ods.ods_erp_tb_hspr_precostsdetail_f_d",
            "dwd.dwd_fee_precostsdetail_df",
        ),
        dwd_task(
            "dwd_fee_offsetpredetail",
            "load_dwd_fee_offsetpredetail_df.py",
            "ods.ods_erp_tb_hspr_offsetpredetail_f_d",
            "dwd.dwd_fee_offsetpredetail_df",
        ),
        dwd_task(
            "dwd_fee_refundfees",
            "load_dwd_fee_refundfees_df.py",
            "ods.ods_erp_tb_hspr_refundfees_f_d",
            "dwd.dwd_fee_refundfees_df",
        ),
        dwd_task(
            "dwd_incident_accept",
            "load_dwd_incident_accept_df.py",
            "ods.ods_erp_tb_hspr_incidentaccept_f_d",
            "dwd.dwd_incident_accept_df",
            ["dim.dim_incidenttype"],
        ),
    ]

    dws_tasks = [
        dws_task(
            "dws_fee_receivable_daily",
            "load_dws_fee_receivable_daily_df.py",
            ["dwd.dwd_fee_fees_df"],
            "dws.dws_fee_receivable_daily_df",
        ),
        dws_task(
            "dws_fee_cashflow_daily",
            "load_dws_fee_cashflow_daily_df.py",
            [
                "dwd.dwd_fee_feesdetail_df",
                "dwd.dwd_fee_precostsdetail_df",
                "dwd.dwd_fee_refundfees_df",
            ],
            "dws.dws_fee_cashflow_daily_df",
        ),
        dws_task(
            "dws_fee_settlement_snapshot",
            "load_dws_fee_settlement_snapshot_df.py",
            [
                "dwd.dwd_fee_fees_df",
                "dwd.dwd_fee_feesdetail_df",
                "dwd.dwd_fee_precostsdetail_df",
                "dwd.dwd_fee_offsetpredetail_df",
                "dwd.dwd_fee_refundfees_df",
            ],
            "dws.dws_fee_settlement_snapshot_df",
        ),
        dws_task(
            "dws_incident_daily",
            "load_dws_incident_daily_df.py",
            ["dwd.dwd_incident_accept_df"],
            "dws.dws_incident_daily_df",
        ),
    ]

    complete = EmptyOperator(task_id="etl_complete")

    start >> dim_tasks >> dim_complete
    dim_complete >> dwd_tasks[0]
    for current_task, next_task in zip(dwd_tasks, dwd_tasks[1:]):
        current_task >> next_task
    dwd_tasks[-1] >> dws_tasks[0]
    for current_task, next_task in zip(dws_tasks, dws_tasks[1:]):
        current_task >> next_task
    dws_tasks[-1] >> complete
