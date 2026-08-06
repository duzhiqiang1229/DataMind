"""Spark task service: CRUD + config generation + trigger + instances."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models import SparkTask, TaskInstance
from app.integrations.spark_config_gen import spark_config_gen
from app.services.component_service import get_airflow_client
from app.schemas.spark_task import SparkTaskCreate, SparkTaskUpdate


async def list_tasks(
    db: AsyncSession, page: int, page_size: int, status: str | None = None
) -> tuple[list[dict], int]:
    query = select(SparkTask)
    count_q = select(func.count(SparkTask.id))
    if status:
        query = query.where(SparkTask.status == status)
        count_q = count_q.where(SparkTask.status == status)

    total = (await db.execute(count_q)).scalar_one()
    result = await db.execute(
        query.order_by(SparkTask.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    tasks = result.scalars().all()
    return [_to_dict(t) for t in tasks], total


async def get_task(db: AsyncSession, task_id: uuid.UUID) -> dict | None:
    result = await db.execute(select(SparkTask).where(SparkTask.id == task_id))
    t = result.scalar_one_or_none()
    if not t:
        return None
    return _to_dict(t)


async def create_task(
    db: AsyncSession, req: SparkTaskCreate, user_id: uuid.UUID
) -> dict:
    """Create Spark task and generate submission config."""
    # generate spark config using the config generator
    if req.mode == "sql":
        spark_config = spark_config_gen.generate_sql_config(
            sql_file_path=req.file_path,
            target_table=f"{req.target_database}.{req.target_table}",
            spark_options=req.spark_config,
            variables=req.variables,
        )
    else:
        spark_config = spark_config_gen.generate_pyspark_config(
            script_file_path=req.file_path,
            spark_options=req.spark_config,
            script_args=req.variables,
        )

    task = SparkTask(
        task_name=req.task_name,
        task_code=req.task_code,
        mode=req.mode,
        file_path=req.file_path,
        target_database=req.target_database,
        target_table=req.target_table,
        spark_config=spark_config,
        variables=req.variables,
        schedule_cron=req.schedule_cron,
        status="active" if req.schedule_cron else "draft",
        is_paused=bool(req.schedule_cron),
        description=req.description,
        created_by=user_id,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return _to_dict(task)


async def update_task(
    db: AsyncSession, task_id: uuid.UUID, req: SparkTaskUpdate
) -> dict | None:
    result = await db.execute(select(SparkTask).where(SparkTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        return None

    if req.task_name is not None:
        task.task_name = req.task_name
    if req.mode is not None:
        task.mode = req.mode
    if req.file_path is not None:
        task.file_path = req.file_path
    if req.target_database is not None:
        task.target_database = req.target_database
    if req.target_table is not None:
        task.target_table = req.target_table
    if req.spark_config is not None:
        # regenerate config
        if task.mode == "sql":
            task.spark_config = spark_config_gen.generate_sql_config(
                sql_file_path=task.file_path,
                target_table=f"{task.target_database}.{task.target_table}",
                spark_options=req.spark_config,
                variables=task.variables,
            )
        else:
            task.spark_config = spark_config_gen.generate_pyspark_config(
                script_file_path=task.file_path,
                spark_options=req.spark_config,
                script_args=task.variables,
            )
    if req.variables is not None:
        task.variables = req.variables
    if req.schedule_cron is not None:
        task.schedule_cron = req.schedule_cron
    if req.status is not None:
        task.status = req.status
    if req.description is not None:
        task.description = req.description

    await db.commit()
    await db.refresh(task)
    return _to_dict(task)


async def delete_task(db: AsyncSession, task_id: uuid.UUID) -> bool:
    result = await db.execute(select(SparkTask).where(SparkTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        return False
    await db.delete(task)
    await db.commit()
    return True


async def trigger_task(
    db: AsyncSession, task_id: uuid.UUID, user_id: uuid.UUID, conf: dict | None = None
) -> dict:
    """Trigger Spark task via Airflow."""
    task_result = await db.execute(select(SparkTask).where(SparkTask.id == task_id))
    task = task_result.scalar_one_or_none()
    if not task:
        raise ValueError("Task not found")

    dag_id = "spark_job"
    run_config = {
        "task_id": str(task.id),
        "task_code": task.task_code,
        "spark_config": task.spark_config,
        **(conf or {}),
    }

    airflow = await get_airflow_client(db)
    run_result = await airflow.trigger_dag_run(dag_id, conf=run_config)
    dag_run_id = run_result.get("dag_run_id", "")

    instance = TaskInstance(
        task_type="spark",
        task_id=task.id,
        dag_id=dag_id,
        dag_run_id=dag_run_id,
        run_config=run_config,
        status="queued",
        triggered_by=user_id,
    )
    db.add(instance)
    await db.commit()
    await db.refresh(instance)
    return _instance_to_dict(instance)


async def list_instances(
    db: AsyncSession, task_id: uuid.UUID, page: int, page_size: int
) -> tuple[list[dict], int]:
    count_q = select(func.count(TaskInstance.id)).where(
        TaskInstance.task_id == task_id and TaskInstance.task_type == "spark"
    )
    total = (await db.execute(count_q)).scalar_one()
    result = await db.execute(
        select(TaskInstance)
        .where(TaskInstance.task_id == task_id)
        .order_by(TaskInstance.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    instances = result.scalars().all()
    return [_instance_to_dict(i) for i in instances], total


async def get_instance_status(db: AsyncSession, instance_id: uuid.UUID) -> dict | None:
    result = await db.execute(select(TaskInstance).where(TaskInstance.id == instance_id))
    inst = result.scalar_one_or_none()
    if not inst:
        return None

    try:
        airflow = await get_airflow_client(db)
        state = await airflow.get_dag_run_state(inst.dag_id, inst.dag_run_id)
        if state != inst.status:
            await db.execute(
                update(TaskInstance).where(TaskInstance.id == inst.id)
                .values(status=state, ended_at=datetime.now(timezone.utc) if state in ("success", "failed") else None)
            )
            await db.commit()
            await db.refresh(inst)
    except Exception as e:
        logger.warning(f"Failed to poll instance {instance_id}: {e}")

    return _instance_to_dict(inst)


async def get_instance_log(
    db: AsyncSession, instance_id: uuid.UUID, task_name: str = "spark_job_task", try_number: int = 1
) -> dict | None:
    result = await db.execute(select(TaskInstance).where(TaskInstance.id == instance_id))
    inst = result.scalar_one_or_none()
    if not inst:
        return None

    airflow = await get_airflow_client(db)
    log_content = await airflow.get_task_log(inst.dag_id, inst.dag_run_id, task_name, try_number)

    return {
        "task_instance_id": str(inst.id),
        "task_id": task_name,
        "log_content": log_content,
        "try_number": try_number,
    }


def _to_dict(t: SparkTask) -> dict:
    return {
        "id": str(t.id),
        "task_name": t.task_name,
        "task_code": t.task_code,
        "mode": t.mode,
        "file_path": t.file_path,
        "target_database": t.target_database,
        "target_table": t.target_table,
        "spark_config": t.spark_config,
        "variables": t.variables,
        "schedule_cron": t.schedule_cron,
        "dag_id": t.dag_id,
        "is_paused": t.is_paused,
        "status": t.status,
        "description": t.description,
        "created_by": str(t.created_by) if t.created_by else None,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
    }


def _instance_to_dict(i: TaskInstance) -> dict:
    return {
        "id": str(i.id),
        "task_type": i.task_type,
        "task_id": str(i.task_id),
        "dag_id": i.dag_id,
        "dag_run_id": i.dag_run_id,
        "status": i.status,
        "error_message": i.error_message,
        "started_at": i.started_at.isoformat() if i.started_at else None,
        "ended_at": i.ended_at.isoformat() if i.ended_at else None,
        "duration_seconds": i.duration_seconds,
        "triggered_by": str(i.triggered_by) if i.triggered_by else None,
        "created_at": i.created_at.isoformat() if i.created_at else None,
    }
