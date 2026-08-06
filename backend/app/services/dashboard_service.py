"""Dashboard service: stats + recent tasks + component status."""
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models import DataSource, DataXTask, TaskInstance, QueryHistory, ComponentConfig
from app.services.component_service import get_airflow_client, get_doris_client, get_cube_client, get_openmetadata_client


async def get_stats(db: AsyncSession) -> dict:
    """Platform overview statistics."""
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    # data sources
    ds_total = (await db.execute(select(func.count(DataSource.id)))).scalar_one()
    ds_active = (await db.execute(select(func.count(DataSource.id)).where(DataSource.status == "active"))).scalar_one()

    # datax tasks
    task_total = (await db.execute(select(func.count(DataXTask.id)))).scalar_one()
    task_active = (await db.execute(select(func.count(DataXTask.id)).where(DataXTask.status == "active"))).scalar_one()

    # today's executions
    today_executions = (await db.execute(
        select(func.count(TaskInstance.id)).where(TaskInstance.created_at >= today_start)
    )).scalar_one()

    # today's queries
    today_queries = (await db.execute(
        select(func.count(QueryHistory.id)).where(QueryHistory.executed_at >= today_start)
    )).scalar_one()

    # 7-day sync trend
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    trend_result = await db.execute(
        select(
            func.date_trunc("day", TaskInstance.created_at).label("day"),
            func.count(TaskInstance.id).label("count"),
            func.sum(func.case((TaskInstance.status == "success", 1), else_=0)).label("success"),
            func.sum(func.case((TaskInstance.status == "failed", 1), else_=0)).label("failed"),
        )
        .where(TaskInstance.created_at >= seven_days_ago)
        .group_by("day")
        .order_by("day")
    )
    trend = [
        {"date": str(row.day)[:10], "total": row.count, "success": row.success or 0, "failed": row.failed or 0}
        for row in trend_result
    ]

    return {
        "data_sources": {"total": ds_total, "active": ds_active},
        "datax_tasks": {"total": task_total, "active": task_active},
        "today_executions": today_executions,
        "today_queries": today_queries,
        "sync_trend": trend,
    }


async def get_recent_tasks(db: AsyncSession, limit: int = 10) -> list[dict]:
    """Recent task executions."""
    result = await db.execute(
        select(TaskInstance)
        .order_by(TaskInstance.created_at.desc())
        .limit(limit)
    )
    tasks = result.scalars().all()
    return [
        {
            "id": str(t.id),
            "task_type": t.task_type,
            "task_id": str(t.task_id),
            "dag_id": t.dag_id,
            "dag_run_id": t.dag_run_id,
            "status": t.status,
            "started_at": t.started_at.isoformat() if t.started_at else None,
            "ended_at": t.ended_at.isoformat() if t.ended_at else None,
            "duration_seconds": t.duration_seconds,
            "rows_written": t.rows_written,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in tasks
    ]


async def get_component_status(db: AsyncSession) -> list[dict]:
    """Check health of all configured components."""
    result = await db.execute(
        select(ComponentConfig).where(ComponentConfig.status == "active")
        .order_by(ComponentConfig.component_type)
    )
    components = result.scalars().all()

    status_list = []
    for cfg in components:
        healthy = cfg.last_check_ok
        status_list.append({
            "component_code": cfg.component_code,
            "component_name": cfg.component_name,
            "component_type": cfg.component_type,
            "base_url": cfg.base_url,
            "healthy": healthy,
            "last_check_at": cfg.last_check_at.isoformat() if cfg.last_check_at else None,
        })
    return status_list
