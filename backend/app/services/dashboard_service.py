"""Dashboard service: stats + recent tasks + component status + task instances."""
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models import (
    DataSource, DataXTask, SparkTask, TaskInstance, QueryHistory,
    ComponentConfig, AirflowDagRun, MetricDefinition, DataServiceApi,
)
from app.services.airflow_service import list_dags as list_airflow_dags
from app.services.component_service import get_airflow_client, get_doris_client, get_cube_client, get_openmetadata_client


async def get_stats(db: AsyncSession) -> dict:
    """Platform overview statistics."""
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    # data sources
    ds_total = (await db.execute(select(func.count(DataSource.id)))).scalar_one()

    # datax + spark tasks (platform tasks)
    datax_total = (await db.execute(select(func.count(DataXTask.id)))).scalar_one()
    spark_total = (await db.execute(select(func.count(SparkTask.id)))).scalar_one()

    # 数据任务：调度任务中运行中的任务数 = Airflow 中未暂停的 DAG 数
    airflow_dags = await list_airflow_dags(db, limit=100, offset=0)
    running_tasks = sum(1 for d in airflow_dags if not d.get("is_paused"))
    schedule_task_count = len(airflow_dags)

    # 指标数：已发布指标
    published_metrics_count = (await db.execute(
        select(func.count(MetricDefinition.id))
        .where(MetricDefinition.status.in_(["published", "active"]))
    )).scalar_one()

    # 数据接口：启用的数据服务 API 数
    api_service_count = (await db.execute(
        select(func.count(DataServiceApi.id))
        .where(DataServiceApi.status == "active")
    )).scalar_one()

    # 今日执行：任务监控中今日（北京时间）运行的任务数
    beijing_tz = timezone(timedelta(hours=8))
    now_beijing = datetime.now(beijing_tz)
    today_start_beijing = now_beijing.replace(hour=0, minute=0, second=0, microsecond=0)
    today_start_utc = today_start_beijing.astimezone(timezone.utc)
    today_executions = (await db.execute(
        select(func.count(AirflowDagRun.id))
        .where(AirflowDagRun.start_date >= today_start_utc)
    )).scalar_one()

    # today's queries
    today_queries = (await db.execute(
        select(func.count(QueryHistory.id)).where(QueryHistory.executed_at >= today_start)
    )).scalar_one()

    # 7-day trend: 调度任务（Airflow DAG 运行）每日成功/失败，按北京时间归日
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    trend_result = await db.execute(
        select(
            func.date_trunc("day", func.timezone("Asia/Shanghai", AirflowDagRun.start_date)).label("day"),
            func.count(AirflowDagRun.id).label("count"),
            func.sum(case((AirflowDagRun.state == "success", 1), else_=0)).label("success"),
            func.sum(case((AirflowDagRun.state == "failed", 1), else_=0)).label("failed"),
        )
        .where(AirflowDagRun.start_date >= seven_days_ago)
        .group_by("day")
        .order_by("day")
    )
    rows = trend_result.all()
    trend = {
        "dates": [str(r.day)[:10] for r in rows],
        "success": [r.success or 0 for r in rows],
        "failed": [r.failed or 0 for r in rows],
    }

    return {
        "total_datasources": ds_total,
        "total_datax_tasks": datax_total + spark_total,
        "running_tasks": running_tasks,
        "schedule_task_count": schedule_task_count,
        "published_metrics_count": published_metrics_count,
        "api_service_count": api_service_count,
        "today_executions": today_executions,
        "today_queries": today_queries,
        "trend": trend,
    }


async def get_recent_tasks(db: AsyncSession, limit: int = 10) -> list[dict]:
    """Recent task executions (from Airflow DAG runs, same source as task monitor)."""
    result = await db.execute(
        select(AirflowDagRun)
        .order_by(AirflowDagRun.start_date.desc().nullslast())
        .limit(limit)
    )
    runs = result.scalars().all()
    return [
        {
            "dag_id": r.dag_id,
            "dag_run_id": r.dag_run_id,
            "run_type": r.run_type,
            "state": r.state,
            "start_date": r.start_date.isoformat() if r.start_date else None,
            "end_date": r.end_date.isoformat() if r.end_date else None,
            "duration_seconds": r.duration_seconds,
        }
        for r in runs
    ]


async def list_task_instances(
    db: AsyncSession, page: int, page_size: int,
    task_type: str | None = None, status: str | None = None,
) -> tuple[list[dict], int]:
    """Paginated task instances for task monitor page."""
    query = select(TaskInstance)
    count_q = select(func.count(TaskInstance.id))
    if task_type:
        query = query.where(TaskInstance.task_type == task_type)
        count_q = count_q.where(TaskInstance.task_type == task_type)
    if status:
        query = query.where(TaskInstance.status == status)
        count_q = count_q.where(TaskInstance.status == status)

    total = (await db.execute(count_q)).scalar_one()
    result = await db.execute(
        query.order_by(TaskInstance.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    instances = result.scalars().all()
    items = [
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
            "rows_read": t.rows_read,
            "rows_written": t.rows_written,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in instances
    ]
    return items, total


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
            "code": cfg.component_code,
            "name": cfg.component_name,
            "type": cfg.component_type,
            "base_url": cfg.base_url,
            "healthy": healthy,
            "last_check_at": cfg.last_check_at.isoformat() if cfg.last_check_at else None,
        })
    return status_list
