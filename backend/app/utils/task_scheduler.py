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
                    TaskInstance.status.in_(["queued", "running"]),
                    TaskInstance.dag_id != "datax_direct",
                )
            )
            active_tasks = result.scalars().all()

            if not active_tasks:
                return

            airflow = await get_airflow_client(db)
            for task in active_tasks:
                try:
                    # Get full DAG run info so we can capture start/end times
                    info = await airflow.get_dag_run(task.dag_id, task.dag_run_id)
                    state = info.get("state", task.status)

                    def _parse_dt(iso):
                        if not iso:
                            return None
                        try:
                            s = str(iso)
                            if s.endswith("Z"):
                                s = s[:-1] + "+00:00"
                            dt = datetime.fromisoformat(s)
                            if dt.tzinfo is None:
                                dt = dt.replace(tzinfo=timezone.utc)
                            return dt
                        except Exception:
                            return None

                    from datetime import datetime, timezone
                    start_dt = _parse_dt(info.get("start_date"))
                    end_dt = _parse_dt(info.get("end_date"))

                    values = {"status": state}
                    if start_dt:
                        values["started_at"] = start_dt
                    if end_dt:
                        values["ended_at"] = end_dt
                    if start_dt and end_dt:
                        values["duration_seconds"] = max(
                            int((end_dt - start_dt).total_seconds()), 0
                        )

                    # For DataX tasks, read sync stats from XCom (rows read/written)
                    if task.task_type == "datax":
                        try:
                            xcom = await airflow.get_xcom(
                                task.dag_id,
                                task.dag_run_id,
                                "datax_sync_task",
                                "datax_stats",
                            )
                            if xcom:
                                import json
                                # Airflow may return XCom values as Python repr
                                # (e.g. "{'rows_read': 15}") — use literal_eval which
                                # handles both single/double quoted dicts.
                                import ast
                                stats = ast.literal_eval(xcom) if isinstance(xcom, str) else xcom
                                if isinstance(stats, dict):
                                    if stats.get("rows_read") is not None:
                                        values["rows_read"] = int(stats["rows_read"])
                                    if stats.get("rows_written") is not None:
                                        values["rows_written"] = int(stats["rows_written"])
                                    if stats.get("bytes_written") is not None:
                                        values["bytes_written"] = int(stats["bytes_written"])
                        except Exception as e:
                            logger.warning(f"Failed to read datax stats XCom for {task.id}: {e}")

                    if (
                        state != task.status
                        or "started_at" in values
                        or "duration_seconds" in values
                        or "rows_read" in values
                    ):
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
    _scheduler.add_job(
        sync_airflow_runs,
        "interval",
        seconds=60,
        id="airflow_runs_sync",
        name="Sync Airflow DAG runs",
        max_instances=1,
    )
    _scheduler.start()
    logger.info(
        f"Scheduler started, polling every {settings.AIRFLOW_POLL_INTERVAL_SECONDS}s"
    )


async def sync_airflow_runs():
    """Sync all Airflow DAG runs into the local table (every 60s)."""
    from app.core.database import async_session
    from app.services.airflow_service import sync_dag_runs

    try:
        async with async_session() as db:
            await sync_dag_runs(db)
    except Exception as e:
        logger.error(f"Airflow runs sync error: {e}")


def shutdown_scheduler():
    """Stop the background scheduler."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
