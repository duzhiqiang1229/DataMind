"""Airflow DAG management service: list, trigger, pause/resume, logs, retry."""
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.services.component_service import get_airflow_client


async def list_dags(db: AsyncSession, limit: int = 100, offset: int = 0) -> list[dict]:
    """List all DAGs from Airflow.

    Args:
        db: Database session (used to load Airflow component config).
        limit: Maximum number of DAGs to return.
        offset: Pagination offset.

    Returns:
        List of DAG dictionaries. Returns an empty list if Airflow is not
        configured or the request fails.
    """
    try:
        client = await get_airflow_client(db)
        return await client.list_dags(limit=limit, offset=offset)
    except RuntimeError as e:
        logger.warning(f"[airflow] list_dags skipped: {e}")
        return []
    except Exception as e:
        logger.error(f"[airflow] list_dags failed: {e}")
        return []


async def get_dag(db: AsyncSession, dag_id: str) -> Optional[dict]:
    """Get details of a specific DAG.

    Args:
        db: Database session.
        dag_id: The DAG identifier.

    Returns:
        DAG detail dictionary, or None if Airflow is not configured / DAG not found.
    """
    try:
        client = await get_airflow_client(db)
        return await client.get_dag(dag_id)
    except RuntimeError as e:
        logger.warning(f"[airflow] get_dag skipped: {e}")
        return None
    except Exception as e:
        logger.error(f"[airflow] get_dag failed: {e}")
        return None


async def pause_dag(db: AsyncSession, dag_id: str) -> Optional[dict]:
    """Pause a DAG so it will no longer be scheduled.

    Args:
        db: Database session.
        dag_id: The DAG identifier.

    Returns:
        Updated DAG dictionary, or None on failure.
    """
    try:
        client = await get_airflow_client(db)
        return await client.patch_dag(dag_id, is_paused=True)
    except RuntimeError as e:
        logger.warning(f"[airflow] pause_dag skipped: {e}")
        return None
    except Exception as e:
        logger.error(f"[airflow] pause_dag failed: {e}")
        return None


async def resume_dag(db: AsyncSession, dag_id: str) -> Optional[dict]:
    """Resume (unpause) a DAG so the scheduler picks it up again.

    Args:
        db: Database session.
        dag_id: The DAG identifier.

    Returns:
        Updated DAG dictionary, or None on failure.
    """
    try:
        client = await get_airflow_client(db)
        return await client.patch_dag(dag_id, is_paused=False)
    except RuntimeError as e:
        logger.warning(f"[airflow] resume_dag skipped: {e}")
        return None
    except Exception as e:
        logger.error(f"[airflow] resume_dag failed: {e}")
        return None


async def trigger_dag(db: AsyncSession, dag_id: str, conf: Optional[dict] = None) -> Optional[dict]:
    """Trigger a new DAG run with optional configuration.

    Args:
        db: Database session.
        dag_id: The DAG identifier.
        conf: Optional configuration parameters passed to the DAG run.

    Returns:
        DAG run info dictionary (includes state, run_id, etc.), or None on failure.
    """
    try:
        client = await get_airflow_client(db)
        return await client.trigger_dag_run(dag_id, conf=conf)
    except RuntimeError as e:
        logger.warning(f"[airflow] trigger_dag skipped: {e}")
        return None
    except Exception as e:
        logger.error(f"[airflow] trigger_dag failed: {e}")
        return None


async def list_dag_runs(
    db: AsyncSession, dag_id: str, limit: int = 50, offset: int = 0
) -> list[dict]:
    """List recent DAG runs for a given DAG.

    Args:
        db: Database session.
        dag_id: The DAG identifier.
        limit: Maximum number of runs to return.
        offset: Pagination offset.

    Returns:
        List of DAG run dictionaries. Empty list on failure.
    """
    try:
        client = await get_airflow_client(db)
        return await client.list_dag_runs(dag_id, limit=limit, offset=offset)
    except RuntimeError as e:
        logger.warning(f"[airflow] list_dag_runs skipped: {e}")
        return []
    except Exception as e:
        logger.error(f"[airflow] list_dag_runs failed: {e}")
        return []


async def get_dag_run_detail(db: AsyncSession, dag_id: str, run_id: str) -> Optional[dict]:
    """Get DAG run detail including its task instances.

    Combines the DAG run info and the task instances list into a single
    response payload for convenience.

    Args:
        db: Database session.
        dag_id: The DAG identifier.
        run_id: The DAG run identifier.

    Returns:
        Dictionary with ``run`` (DAG run info) and ``task_instances`` keys,
        or None on failure.
    """
    try:
        client = await get_airflow_client(db)
        run = await client.get_dag_run(dag_id, run_id)
        task_instances = await client.get_task_instances(dag_id, run_id)
        return {
            "run": run,
            "task_instances": task_instances,
        }
    except RuntimeError as e:
        logger.warning(f"[airflow] get_dag_run_detail skipped: {e}")
        return None
    except Exception as e:
        logger.error(f"[airflow] get_dag_run_detail failed: {e}")
        return None


async def get_dag_run_log(
    db: AsyncSession, dag_id: str, run_id: str, task_id: str, try_number: int = 1
) -> str:
    """Fetch execution log text for a specific task instance.

    Args:
        db: Database session.
        dag_id: The DAG identifier.
        run_id: The DAG run identifier.
        task_id: The task instance identifier.
        try_number: The attempt number (1-based). Defaults to 1.

    Returns:
        Log text. Empty string on failure.
    """
    try:
        client = await get_airflow_client(db)
        return await client.get_task_log(
            dag_id, run_id, task_id, try_number=try_number
        )
    except RuntimeError as e:
        logger.warning(f"[airflow] get_dag_run_log skipped: {e}")
        return ""
    except Exception as e:
        logger.error(f"[airflow] get_dag_run_log failed: {e}")
        return ""


async def retry_dag_run(
    db: AsyncSession, dag_id: str, run_id: str, task_id: str
) -> dict:
    """Retry a failed task instance within a DAG run.

    Airflow does not expose a dedicated retry endpoint. The approach is to
    clear the task instance state by sending ``PATCH`` with
    ``{"state": "none"}``. Once cleared, the Airflow scheduler picks the
    task up and re-executes it.

    Args:
        db: Database session.
        dag_id: The DAG identifier.
        run_id: The DAG run identifier.
        task_id: The task instance to retry.

    Returns:
        Dictionary describing the retry outcome::

            {"success": bool, "dag_id": str, "run_id": str,
             "task_id": str, "message": str, "detail": dict | None}
    """
    result: dict[str, Any] = {
        "success": False,
        "dag_id": dag_id,
        "run_id": run_id,
        "task_id": task_id,
        "message": "",
        "detail": None,
    }

    try:
        client = await get_airflow_client(db)
        # Clear the task instance state so the scheduler re-runs it.
        resp = await client._request(
            "PATCH",
            f"/api/v1/dags/{dag_id}/dagRuns/{run_id}/taskInstances/{task_id}",
            json={"state": "none"},
        )
        detail = resp.json() if resp.content else {}
        result["success"] = True
        result["detail"] = detail
        result["message"] = (
            f"Task instance '{task_id}' in run '{run_id}' cleared for retry. "
            "The Airflow scheduler will pick it up shortly."
        )
        logger.info(
            f"[airflow] retry_dag_run: cleared task {task_id} "
            f"in dag={dag_id} run={run_id}"
        )
    except RuntimeError as e:
        result["message"] = f"Airflow not configured: {e}"
        logger.warning(f"[airflow] retry_dag_run skipped: {e}")
    except Exception as e:
        result["message"] = f"Failed to retry task instance: {e}"
        logger.error(f"[airflow] retry_dag_run failed: {e}")

    return result
