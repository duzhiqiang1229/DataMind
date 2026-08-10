"""ETL script service: CRUD + multi-engine execution."""
import json
import uuid
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import EtlScript
from app.schemas.etl_script import EtlScriptCreate, EtlScriptUpdate


async def list_scripts(
    db: AsyncSession, page: int, page_size: int,
    language: Optional[str] = None, keyword: Optional[str] = None,
) -> tuple[list[dict], int]:
    query = select(EtlScript)
    count_q = select(func.count(EtlScript.id))
    if language:
        query = query.where(EtlScript.language == language)
        count_q = count_q.where(EtlScript.language == language)
    if keyword:
        kw = f"%{keyword}%"
        query = query.where(EtlScript.script_name.ilike(kw))
        count_q = count_q.where(EtlScript.script_name.ilike(kw))
    total = (await db.execute(count_q)).scalar_one()
    result = await db.execute(
        query.order_by(EtlScript.updated_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    return [_to_dict(s) for s in result.scalars().all()], total


async def get_script(db: AsyncSession, script_id: uuid.UUID) -> dict | None:
    result = await db.execute(select(EtlScript).where(EtlScript.id == script_id))
    s = result.scalar_one_or_none()
    return _to_dict(s) if s else None


async def create_script(
    db: AsyncSession, req: EtlScriptCreate, user_id: uuid.UUID,
) -> dict:
    script_code = req.script_code or f"etl_{req.language}_{uuid.uuid4().hex[:8]}"
    s = EtlScript(
        script_name=req.script_name,
        script_code=script_code,
        language=req.language,
        content=req.content,
        description=req.description,
        schedule_cron=req.schedule_cron,
        is_scheduled=bool(req.schedule_cron),
        created_by=user_id,
    )
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return _to_dict(s)


async def update_script(
    db: AsyncSession, script_id: uuid.UUID, req: EtlScriptUpdate,
) -> dict | None:
    result = await db.execute(select(EtlScript).where(EtlScript.id == script_id))
    s = result.scalar_one_or_none()
    if not s:
        return None
    if req.script_name is not None:
        s.script_name = req.script_name
    if req.language is not None:
        s.language = req.language
    if req.content is not None:
        s.content = req.content
    if req.description is not None:
        s.description = req.description
    if req.schedule_cron is not None:
        s.schedule_cron = req.schedule_cron
        s.is_scheduled = bool(req.schedule_cron)
    if req.is_scheduled is not None:
        s.is_scheduled = req.is_scheduled
    await db.commit()
    await db.refresh(s)
    return _to_dict(s)


async def delete_script(db: AsyncSession, script_id: uuid.UUID) -> bool:
    result = await db.execute(select(EtlScript).where(EtlScript.id == script_id))
    s = result.scalar_one_or_none()
    if not s:
        return False
    # Best-effort: remove deployed schedule DAG + uploaded script file from Airflow node
    try:
        from app.services.component_service import _load_config
        import paramiko

        config = await _load_config(db, "airflow")
        if config:
            ssh_host = config.get("ssh_host") or "192.168.1.4"
            ssh_port = int(config.get("ssh_port") or 22)
            ssh_user = config.get("ssh_user") or "root"
            ssh_password = config.get("ssh_password") or ""
            dags_path = config.get("dags_path") or "/home/airflow/dags"
            if ssh_password:
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                client.connect(
                    ssh_host, port=ssh_port, username=ssh_user,
                    password=ssh_password, timeout=15,
                )
                sftp = client.open_sftp()
                try:
                    ext = ".py" if s.language in ("pyspark", "python") else ".sql"
                    for remote in (
                        f"{dags_path.rstrip('/')}/etl_schedule_{s.script_code}.py",
                        f"{dags_path.rstrip('/')}/{s.script_code}_script.py",
                        f"/home/airflow/scripts/{s.script_code}{ext}",
                    ):
                        try:
                            sftp.remove(remote)
                        except FileNotFoundError:
                            pass
                finally:
                    sftp.close()
                    client.close()
    except Exception:
        # Remote cleanup failure should not block local delete
        pass
    await db.delete(s)
    await db.commit()
    return True


async def execute_script(
    db: AsyncSession,
    script_id: uuid.UUID,
    datasource_id: Optional[str],
    database: Optional[str],
    limit: int,
) -> dict:
    """Execute an ETL script:
    - sql       -> run against the chosen datasource
    - sparksql/pyspark/python -> upload to Airflow/Spark node and trigger spark_job DAG
    """
    result = await db.execute(select(EtlScript).where(EtlScript.id == script_id))
    s = result.scalar_one_or_none()
    if not s:
        raise ValueError("脚本不存在")

    if s.language == "sql":
        if not datasource_id:
            raise ValueError("SQL 执行需要选择数据源")
        from app.services.datasource_service import execute_query
        return await execute_query(
            db, uuid.UUID(datasource_id), s.content, limit,
            database=database,
        )

    # Spark / Python engines: upload script to the Airflow node and trigger spark_job
    import paramiko

    from app.services.component_service import _load_config

    config = await _load_config(db, "airflow")
    if not config:
        raise RuntimeError("Airflow component not configured")
    ssh_host = config.get("ssh_host") or "192.168.1.4"
    ssh_port = int(config.get("ssh_port") or 22)
    ssh_user = config.get("ssh_user") or "root"
    ssh_password = config.get("ssh_password") or ""
    if not ssh_password:
        raise ValueError("请先在 Airflow 组件配置中填写 SSH 密码")

    # Upload script file to the Airflow node (Spark runs on the same host)
    ext = ".sql" if s.language in ("sql", "sparksql") else ".py"
    remote_file = f"/home/airflow/scripts/{s.script_code}{ext}"

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(ssh_host, port=ssh_port, username=ssh_user, password=ssh_password, timeout=15)
    sftp = client.open_sftp()
    try:
        try:
            sftp.stat("/home/airflow/scripts")
        except FileNotFoundError:
            sftp.mkdir("/home/airflow/scripts")
        with sftp.open(remote_file, "w") as f:
            f.write(s.content.encode("utf-8"))
    finally:
        sftp.close()
        client.close()

    # Trigger spark_job DAG with the uploaded script
    from app.services.component_service import get_airflow_client
    from app.services.airflow_service import trigger_dag

    if s.language == "sparksql":
        spark_config = {"mode": "sql", "sql_file": remote_file, "target_table": ""}
    else:
        spark_config = {"mode": "pyspark", "script_file": remote_file, "script_args": {}}

    run = await trigger_dag(db, "spark_job", conf={
        "task_id": str(script_id),
        "script_code": s.script_code,
        "spark_config": spark_config,
    })
    return {"dag_id": "spark_job", "dag_run_id": run.get("dag_run_id", ""), "script_code": s.script_code}


async def deploy_schedule(db: AsyncSession, script_id: uuid.UUID) -> dict:
    """Deploy an ETL script as a scheduled Airflow DAG (cron-triggered)."""
    import paramiko

    from app.services.component_service import _load_config

    result = await db.execute(select(EtlScript).where(EtlScript.id == script_id))
    s = result.scalar_one_or_none()
    if not s:
        raise ValueError("脚本不存在")
    if not s.schedule_cron:
        raise ValueError("请先设置调度 Cron")
    if s.language == "sql":
        raise ValueError("SQL 脚本暂不支持调度，请使用 Spark SQL")

    config = await _load_config(db, "airflow")
    if not config:
        raise RuntimeError("Airflow component not configured")
    ssh_host = config.get("ssh_host") or "192.168.1.4"
    ssh_port = int(config.get("ssh_port") or 22)
    ssh_user = config.get("ssh_user") or "root"
    ssh_password = config.get("ssh_password") or ""
    dags_path = config.get("dags_path") or "/home/airflow/dags"
    if not ssh_password:
        raise ValueError("请先在 Airflow 组件配置中填写 SSH 密码")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(ssh_host, port=ssh_port, username=ssh_user, password=ssh_password, timeout=15)
    sftp = client.open_sftp()
    try:
        # 1. Upload script file
        try:
            sftp.stat("/home/airflow/scripts")
        except FileNotFoundError:
            sftp.mkdir("/home/airflow/scripts")
        ext = ".py" if s.language in ("pyspark", "python") else ".sql"
        remote_file = f"/home/airflow/scripts/{s.script_code}{ext}"
        with sftp.open(remote_file, "w") as f:
            f.write(s.content.encode("utf-8"))

        # 1.1 Mirror the script into the Airflow dags folder so it is visible
        # directly under /home/airflow/dags. Airflow is told to skip these
        # *_script.py mirrors via .airflowignore (gitignore-style patterns).
        exec_file = remote_file
        if s.language in ("pyspark", "python"):
            dags_root = dags_path.rstrip("/")
            dag_script = f"{dags_root}/{s.script_code}_script.py"
            with sftp.open(dag_script, "w") as f:
                f.write(s.content.encode("utf-8"))
            exec_file = dag_script

            # Ensure .airflowignore contains the mirror pattern
            ignore_path = f"{dags_root}/.airflowignore"
            ignore_pattern = "*_script.py"
            existing = ""
            try:
                with sftp.open(ignore_path, "r") as f:
                    existing = f.read().decode("utf-8", errors="replace")
            except FileNotFoundError:
                pass
            lines = [ln.strip() for ln in existing.splitlines() if ln.strip()]
            if ignore_pattern not in lines:
                new_content = (
                    existing.rstrip("\n") + "\n" + ignore_pattern + "\n"
                    if existing.strip()
                    else ignore_pattern + "\n"
                )
                with sftp.open(ignore_path, "w") as f:
                    f.write(new_content.encode("utf-8"))

        # 2. Generate scheduled DAG file
        dag_id = f"etl_schedule_{s.script_code}"
        if s.language == "sparksql":
            spark_config = {"mode": "sql", "sql_file": remote_file, "target_table": ""}
        else:
            spark_config = {"mode": "pyspark", "script_file": exec_file, "script_args": {}}

        content = (
            f'"""DataMind scheduled ETL script: {s.script_name}"""\n'
            "from airflow import DAG\n"
            "from airflow.operators.trigger_dagrun import TriggerDagRunOperator\n"
            "from airflow.utils.dates import days_ago\n"
            "\n"
            'default_args = {"owner": "datamind", "retries": 0}\n'
            "\n"
            "dag = DAG(\n"
            f'    dag_id="{dag_id}",\n'
            f'    description="{s.script_name}",\n'
            f'    schedule="{s.schedule_cron}",\n'
            "    start_date=days_ago(1),\n"
            "    catchup=False,\n"
            '    tags=["datamind", "schedule"],\n'
            "    default_args=default_args,\n"
            ")\n"
            "\n"
            "trigger_task = TriggerDagRunOperator(\n"
            '    task_id="run_script",\n'
            '    trigger_dag_id="spark_job",\n'
            f'    conf={{"task_id": "{str(script_id)}", "script_code": "{s.script_code}", "spark_config": {json.dumps(spark_config)}}},\n'
            "    dag=dag,\n"
            ")\n"
        )
        remote_dag = f"{dags_path.rstrip('/')}/{dag_id}.py"
        with sftp.open(remote_dag, "w") as f:
            f.write(content.encode("utf-8"))
    finally:
        sftp.close()
        client.close()

    # Mark as scheduled
    s.is_scheduled = True
    await db.commit()
    return {"dag_id": dag_id, "schedule": s.schedule_cron, "script_code": s.script_code}


def _to_dict(s: EtlScript) -> dict:
    return {
        "id": str(s.id),
        "script_name": s.script_name,
        "script_code": s.script_code,
        "language": s.language,
        "content": s.content,
        "description": s.description,
        "schedule_cron": s.schedule_cron,
        "is_scheduled": s.is_scheduled,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }
