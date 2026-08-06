"""
Background task scheduler: polls Airflow DAG run status and updates local DB.
Uses APScheduler with AsyncIOScheduler.

Runs every N seconds (configurable via AIRFLOW_POLL_INTERVAL_SECONDS).
Only polls task instances that are in 'queued' or 'running' state.
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger

from app.core.config import settings

_scheduler: AsyncIOScheduler | None = None


async def poll_airflow_task_status():
    """
    Poll Airflow for task instances in 'queued' or 'running' state.
    Update their status in the local task_instances table.

    Flow:
    1. Query local DB for task_instances WHERE status IN ('queued', 'running')
    2. For each, call Airflow API get_dag_run_state(dag_id, run_id)
    3. If state changed, update local record
    4. If state is 'success' or 'failed', record end_time
    """
    from app.core.database import async_session
    from app.models.task_instance import TaskInstance
    from sqlalchemy import select, update
    from app.services.component_service import get_airflow_client

    try:
        async with async_session() as db:
            result = await db.execute(
                select(TaskInstance).where(
                    TaskInstance.status.in_(["queued", "running"])
                )
            )
            active_tasks = result.scalars().all()

            if not active_tasks:
                return

            airflow = await get_airflow_client(db)
            for task in active_tasks:
                try:
                    state = await airflow.get_dag_run_state(
                        task.dag_id, task.dag_run_id
                    )
                    if state != task.status:
                        from datetime import datetime, timezone
                        values = {"status": state}
                        if state in ("success", "failed"):
                            values["ended_at"] = datetime.now(timezone.utc)
                        await db.execute(
                            update(TaskInstance)
                            .where(TaskInstance.id == task.id)
                            .values(**values)
                        )
                        logger.info(f"Task {task.id} status updated: {task.status} -> {state}")
                except Exception as e:
                    logger.warning(f"Failed to poll task {task.id}: {e}")

            await db.commit()
    except Exception as e:
        logger.error(f"Airflow polling error: {e}")


def init_scheduler():
    """Start the background scheduler."""
    global _scheduler
    if _scheduler and _scheduler.running:
        return

    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(
        poll_airflow_task_status,
        "interval",
        seconds=settings.AIRFLOW_POLL_INTERVAL_SECONDS,
        id="airflow_poll",
        name="Poll Airflow task status",
        max_instances=1,
    )
    _scheduler.start()
    logger.info(
        f"Scheduler started, polling every {settings.AIRFLOW_POLL_INTERVAL_SECONDS}s"
    )


def shutdown_scheduler():
    """Stop the background scheduler."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
