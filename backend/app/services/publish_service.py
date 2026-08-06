"""Publish service: create publish tasks + execute + records."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from loguru import logger

from app.models import PublishTask, PublishRecord, DataModel, SparkTask, DataXTask
from app.schemas.publish import PublishTaskCreate


async def list_tasks(
    db: AsyncSession, page: int, page_size: int,
    publish_type: Optional[str] = None, status: Optional[str] = None,
) -> tuple[list[dict], int]:
    query = select(PublishTask).options(selectinload(PublishTask.records))
    count_q = select(func.count(PublishTask.id))
    if publish_type:
        query = query.where(PublishTask.publish_type == publish_type)
        count_q = count_q.where(PublishTask.publish_type == publish_type)
    if status:
        query = query.where(PublishTask.status == status)
        count_q = count_q.where(PublishTask.status == status)

    total = (await db.execute(count_q)).scalar_one()
    result = await db.execute(
        query.order_by(PublishTask.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    tasks = result.scalars().all()
    return [_to_dict(t) for t in tasks], total


async def get_task(db: AsyncSession, task_id: uuid.UUID) -> dict | None:
    result = await db.execute(
        select(PublishTask)
        .options(selectinload(PublishTask.records))
        .where(PublishTask.id == task_id)
    )
    t = result.scalar_one_or_none()
    if not t:
        return None
    return _to_dict(t)


async def create_task(
    db: AsyncSession, req: PublishTaskCreate, user_id: uuid.UUID
) -> dict:
    task = PublishTask(
        publish_name=req.publish_name,
        publish_type=req.publish_type,
        source_ids=[uuid.UUID(sid) for sid in req.source_ids],
        target_environment=req.target_environment,
        description=req.description,
        status="pending",
        created_by=user_id,
    )
    db.add(task)
    await db.flush()

    # Create publish records for each source
    for sid in req.source_ids:
        source_uuid = uuid.UUID(sid)
        source_name = await _get_source_name(db, req.publish_type, source_uuid)
        db.add(PublishRecord(
            publish_task_id=task.id,
            source_id=source_uuid,
            source_type=req.publish_type,
            source_name=source_name,
            result="pending",
        ))

    await db.commit()
    await db.refresh(task)
    return _to_dict(task)


async def execute_task(db: AsyncSession, task_id: uuid.UUID) -> dict | None:
    """Execute a publish task: for models, execute DDL in Doris; for tasks, set status to production."""
    result = await db.execute(
        select(PublishTask).options(selectinload(PublishTask.records))
        .where(PublishTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        return None

    task.status = "running"
    task.executed_at = datetime.now(timezone.utc)
    await db.commit()

    # Process each record
    for record in task.records:
        if record.result != "pending":
            continue
        try:
            if task.publish_type == "model":
                await _publish_model(db, record)
            elif task.publish_type == "spark_task":
                await _publish_spark_task(db, record)
            elif task.publish_type == "datax_task":
                await _publish_datax_task(db, record)
            record.result = "success"
        except Exception as e:
            record.result = "failed"
            record.error_message = str(e)
            logger.error(f"Publish record {record.id} failed: {e}")

    # Update task status
    all_success = all(r.result == "success" for r in task.records)
    task.status = "success" if all_success else "failed"
    await db.commit()
    await db.refresh(task)
    return _to_dict(task)


async def _get_source_name(db: AsyncSession, source_type: str, source_id: uuid.UUID) -> str:
    if source_type == "model":
        result = await db.execute(select(DataModel).where(DataModel.id == source_id))
        m = result.scalar_one_or_none()
        return m.model_name if m else str(source_id)
    elif source_type == "spark_task":
        result = await db.execute(select(SparkTask).where(SparkTask.id == source_id))
        t = result.scalar_one_or_none()
        return t.task_name if t else str(source_id)
    elif source_type == "datax_task":
        result = await db.execute(select(DataXTask).where(DataXTask.id == source_id))
        t = result.scalar_one_or_none()
        return t.task_name if t else str(source_id)
    return str(source_id)


async def _publish_model(db: AsyncSession, record: PublishRecord):
    """Publish a data model: execute its DDL in Doris."""
    result = await db.execute(select(DataModel).where(DataModel.id == record.source_id))
    model = result.scalar_one_or_none()
    if not model:
        raise ValueError(f"Model {record.source_id} not found")

    from app.services.component_service import get_doris_client
    doris = await get_doris_client(db)
    # Get the latest version DDL
    from app.models import DataModelVersion
    version_result = await db.execute(
        select(DataModelVersion)
        .where(DataModelVersion.model_id == model.id)
        .order_by(DataModelVersion.version.desc())
        .limit(1)
    )
    version = version_result.scalar_one_or_none()
    if version and version.table_ddl:
        doris.execute_query(version.table_ddl)
        record.source_name = model.model_name


async def _publish_spark_task(db: AsyncSession, record: PublishRecord):
    """Publish a Spark task: set status to active."""
    result = await db.execute(select(SparkTask).where(SparkTask.id == record.source_id))
    task = result.scalar_one_or_none()
    if not task:
        raise ValueError(f"Spark task {record.source_id} not found")
    task.status = "active"
    record.source_name = task.task_name


async def _publish_datax_task(db: AsyncSession, record: PublishRecord):
    """Publish a DataX task: set status to active."""
    result = await db.execute(select(DataXTask).where(DataXTask.id == record.source_id))
    task = result.scalar_one_or_none()
    if not task:
        raise ValueError(f"DataX task {record.source_id} not found")
    task.status = "active"
    record.source_name = task.task_name


async def delete_task(db: AsyncSession, task_id: uuid.UUID) -> bool:
    result = await db.execute(select(PublishTask).where(PublishTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        return False
    await db.delete(task)
    await db.commit()
    return True


def _to_dict(t: PublishTask) -> dict:
    return {
        "id": str(t.id),
        "publish_name": t.publish_name,
        "publish_type": t.publish_type,
        "source_ids": [str(sid) for sid in t.source_ids],
        "target_environment": t.target_environment,
        "description": t.description,
        "status": t.status,
        "records": [
            {
                "id": str(r.id),
                "source_id": str(r.source_id),
                "source_type": r.source_type,
                "source_name": r.source_name,
                "result": r.result,
                "error_message": r.error_message,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in (t.records or [])
        ],
        "created_by": str(t.created_by) if t.created_by else None,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "executed_at": t.executed_at.isoformat() if t.executed_at else None,
    }
