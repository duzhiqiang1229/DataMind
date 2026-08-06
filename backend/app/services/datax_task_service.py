"""DataX task service: CRUD + config generation + trigger + pause/resume + instances."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from loguru import logger

from app.core.security import decrypt_value
from app.models import DataXTask, DataXFieldMapping, TaskInstance, DataSource
from app.integrations.datax_config_gen import datax_config_gen
from app.services.component_service import get_airflow_client
from app.schemas.datax_task import (
    DataXTaskCreate, DataXTaskUpdate, DataXTaskResponse,
    FieldMappingItem, TaskInstanceResponse,
)


async def list_tasks(
    db: AsyncSession, page: int, page_size: int, status: str | None = None
) -> tuple[list[dict], int]:
    query = select(DataXTask).options(selectinload(DataXTask.field_mappings))
    count_q = select(func.count(DataXTask.id))
    if status:
        query = query.where(DataXTask.status == status)
        count_q = count_q.where(DataXTask.status == status)

    total = (await db.execute(count_q)).scalar_one()
    result = await db.execute(
        query.order_by(DataXTask.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    tasks = result.scalars().all()
    return [_to_dict(t) for t in tasks], total


async def get_task(db: AsyncSession, task_id: uuid.UUID) -> dict | None:
    result = await db.execute(
        select(DataXTask)
        .options(selectinload(DataXTask.field_mappings))
        .where(DataXTask.id == task_id)
    )
    t = result.scalar_one_or_none()
    if not t:
        return None
    return _to_dict(t)


async def create_task(
    db: AsyncSession, req: DataXTaskCreate, user_id: uuid.UUID
) -> dict:
    """Create DataX task + field mappings + generate job JSON."""
    # load data source for config generation
    ds_result = await db.execute(
        select(DataSource).where(DataSource.id == uuid.UUID(req.source_datasource_id))
    )
    ds = ds_result.scalar_one_or_none()
    if not ds:
        raise ValueError(f"Data source {req.source_datasource_id} not found")

    # build source config for datax_config_gen
    source_config = {
        "type": ds.source_type,
        "host": ds.host,
        "port": ds.port,
        "username": ds.username,
        "password": decrypt_value(ds.password_encrypted),
        "database": ds.database_name or "",
        "table": req.source_table,
        "where": req.where_clause or "",
        "split_pk": req.split_pk or "",
    }

    # build target config (Doris) — load from component_configs
    from app.services.component_service import get_doris_client
    doris = await get_doris_client(db)
    target_config = {
        "type": "doris",
        "host": doris.mysql_host,
        "port": doris.mysql_port,
        "username": doris.username,
        "password": doris.password,
        "database": req.target_database,
        "table": req.target_table,
    }

    # column mapping
    column_mapping = [m.model_dump() for m in req.field_mappings]

    # options
    options = {
        "channel": req.channel,
        "error_limit_record": req.error_limit_record,
        "error_limit_percentage": req.error_limit_pct,
    }

    # generate DataX job JSON
    job_json = datax_config_gen.generate_job_json(source_config, target_config, column_mapping, options)

    # save task
    task = DataXTask(
        task_name=req.task_name,
        task_code=req.task_code,
        source_datasource_id=uuid.UUID(req.source_datasource_id),
        source_table=req.source_table,
        source_schema=req.source_schema,
        where_clause=req.where_clause,
        split_pk=req.split_pk,
        target_database=req.target_database,
        target_table=req.target_table,
        job_config=job_json,
        sync_mode=req.sync_mode,
        channel=req.channel,
        error_limit_record=req.error_limit_record,
        error_limit_pct=req.error_limit_pct,
        schedule_cron=req.schedule_cron,
        status="active" if req.schedule_cron else "draft",
        is_paused=bool(req.schedule_cron),
        created_by=user_id,
    )
    db.add(task)
    await db.flush()

    # save field mappings
    for m in req.field_mappings:
        db.add(DataXFieldMapping(
            task_id=task.id,
            source_column=m.source_column,
            target_column=m.target_column,
            source_type=m.source_type,
            target_type=m.target_type,
            is_primary_key=m.is_primary_key,
            sort_order=m.sort_order,
        ))

    await db.commit()
    await db.refresh(task)
    return _to_dict(task)


async def update_task(
    db: AsyncSession, task_id: uuid.UUID, req: DataXTaskUpdate
) -> dict | None:
    result = await db.execute(
        select(DataXTask).options(selectinload(DataXTask.field_mappings)).where(DataXTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        return None

    # update basic fields
    if req.task_name is not None:
        task.task_name = req.task_name
    if req.source_table is not None:
        task.source_table = req.source_table
    if req.where_clause is not None:
        task.where_clause = req.where_clause
    if req.split_pk is not None:
        task.split_pk = req.split_pk
    if req.target_database is not None:
        task.target_database = req.target_database
    if req.target_table is not None:
        task.target_table = req.target_table
    if req.sync_mode is not None:
        task.sync_mode = req.sync_mode
    if req.channel is not None:
        task.channel = req.channel
    if req.error_limit_record is not None:
        task.error_limit_record = req.error_limit_record
    if req.error_limit_pct is not None:
        task.error_limit_pct = req.error_limit_pct
    if req.schedule_cron is not None:
        task.schedule_cron = req.schedule_cron
    if req.status is not None:
        task.status = req.status

    # if field mappings changed, regenerate job JSON
    if req.field_mappings:
        # delete old mappings
        await db.execute(delete(DataXFieldMapping).where(DataXFieldMapping.task_id == task_id))
        for m in req.field_mappings:
            db.add(DataXFieldMapping(
                task_id=task_id,
                source_column=m.source_column,
                target_column=m.target_column,
                source_type=m.source_type,
                target_type=m.target_type,
                is_primary_key=m.is_primary_key,
                sort_order=m.sort_order,
            ))

        # regenerate job JSON
        ds_result = await db.execute(select(DataSource).where(DataSource.id == task.source_datasource_id))
        ds = ds_result.scalar_one()
        from app.services.component_service import get_doris_client
        doris = await get_doris_client(db)

        source_config = {
            "type": ds.source_type, "host": ds.host, "port": ds.port,
            "username": ds.username, "password": decrypt_value(ds.password_encrypted),
            "database": ds.database_name or "", "table": task.source_table,
            "where": task.where_clause or "", "split_pk": task.split_pk or "",
        }
        target_config = {
            "type": "doris", "host": doris.mysql_host, "port": doris.mysql_port,
            "username": doris.username, "password": doris.password,
            "database": task.target_database, "table": task.target_table,
        }
        column_mapping = [m.model_dump() for m in req.field_mappings]
        options = {"channel": task.channel, "error_limit_record": task.error_limit_record, "error_limit_percentage": float(task.error_limit_pct)}
        task.job_config = datax_config_gen.generate_job_json(source_config, target_config, column_mapping, options)

    await db.commit()
    await db.refresh(task)
    return _to_dict(task)


async def delete_task(db: AsyncSession, task_id: uuid.UUID) -> bool:
    result = await db.execute(select(DataXTask).where(DataXTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        return False
    await db.delete(task)
    await db.commit()
    return True


async def trigger_task(
    db: AsyncSession, task_id: uuid.UUID, user_id: uuid.UUID, conf: dict | None = None
) -> dict:
    """Trigger DataX task via Airflow."""
    task_result = await db.execute(
        select(DataXTask).where(DataXTask.id == task_id)
    )
    task = task_result.scalar_one_or_none()
    if not task:
        raise ValueError("Task not found")

    dag_id = "datax_sync"
    run_config = {
        "task_id": str(task.id),
        "task_code": task.task_code,
        "job_json": task.job_config,
        **(conf or {}),
    }

    # trigger via Airflow
    airflow = await get_airflow_client(db)
    run_result = await airflow.trigger_dag_run(dag_id, conf=run_config)
    dag_run_id = run_result.get("dag_run_id", "")

    # create task instance
    instance = TaskInstance(
        task_type="datax",
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


async def pause_task(db: AsyncSession, task_id: uuid.UUID) -> bool:
    """Pause scheduled task in Airflow."""
    task_result = await db.execute(select(DataXTask).where(DataXTask.id == task_id))
    task = task_result.scalar_one_or_none()
    if not task:
        return False
    if task.dag_id:
        airflow = await get_airflow_client(db)
        await airflow.patch_dag(task.dag_id, is_paused=True)
    task.is_paused = True
    await db.commit()
    return True


async def resume_task(db: AsyncSession, task_id: uuid.UUID) -> bool:
    """Resume scheduled task in Airflow."""
    task_result = await db.execute(select(DataXTask).where(DataXTask.id == task_id))
    task = task_result.scalar_one_or_none()
    if not task:
        return False
    if task.dag_id:
        airflow = await get_airflow_client(db)
        await airflow.patch_dag(task.dag_id, is_paused=False)
    task.is_paused = False
    await db.commit()
    return True


async def list_instances(
    db: AsyncSession, task_id: uuid.UUID, page: int, page_size: int
) -> tuple[list[dict], int]:
    count_q = select(func.count(TaskInstance.id)).where(TaskInstance.task_id == task_id)
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

    # optionally poll Airflow for latest status
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
    db: AsyncSession, instance_id: uuid.UUID, task_name: str = "datax_sync_task", try_number: int = 1
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


def _to_dict(t: DataXTask) -> dict:
    return {
        "id": str(t.id),
        "task_name": t.task_name,
        "task_code": t.task_code,
        "source_datasource_id": str(t.source_datasource_id),
        "source_table": t.source_table,
        "source_schema": t.source_schema,
        "where_clause": t.where_clause,
        "split_pk": t.split_pk,
        "target_database": t.target_database,
        "target_table": t.target_table,
        "sync_mode": t.sync_mode,
        "channel": t.channel,
        "error_limit_record": t.error_limit_record,
        "error_limit_pct": float(t.error_limit_pct),
        "schedule_cron": t.schedule_cron,
        "dag_id": t.dag_id,
        "is_paused": t.is_paused,
        "status": t.status,
        "job_config": t.job_config,
        "field_mappings": [
            {
                "source_column": m.source_column,
                "target_column": m.target_column,
                "source_type": m.source_type,
                "target_type": m.target_type,
                "is_primary_key": m.is_primary_key,
                "sort_order": m.sort_order,
            }
            for m in t.field_mappings
        ] if t.field_mappings else [],
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
        "rows_read": i.rows_read,
        "rows_written": i.rows_written,
        "triggered_by": str(i.triggered_by) if i.triggered_by else None,
        "created_at": i.created_at.isoformat() if i.created_at else None,
    }
