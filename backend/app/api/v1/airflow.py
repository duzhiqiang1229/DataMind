"""Airflow DAG management API: list, trigger, pause/resume, runs, logs, retry."""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.common import ResponseOK
from app.services import airflow_service

router = APIRouter()


# --- Request body schemas ---


class TriggerDagBody(BaseModel):
    """Request body for triggering a DAG run."""
    conf: dict = {}


class RetryDagRunBody(BaseModel):
    """Request body for retrying a failed task instance."""
    task_id: str


# --- Endpoints ---


@router.get("", response_model=ResponseOK[list], summary="DAG列表")
async def list_dags(
    limit: int = Query(100, ge=1, description="返回数量上限"),
    offset: int = Query(0, ge=0, description="分页偏移量"),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """List all DAGs registered in Airflow."""
    result = await airflow_service.list_dags(db, limit=limit, offset=offset)
    return ResponseOK(data=result)


@router.get("/{dag_id}", response_model=ResponseOK[dict], summary="DAG详情")
async def get_dag(
    dag_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get detail of a specific DAG."""
    result = await airflow_service.get_dag(db, dag_id)
    if result is None:
        return ResponseOK(code=404, message="DAG not found or Airflow not configured")
    return ResponseOK(data=result)


@router.post("/{dag_id}/pause", response_model=ResponseOK[dict], summary="暂停DAG")
async def pause_dag(
    dag_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Pause a DAG so it stops being scheduled."""
    result = await airflow_service.pause_dag(db, dag_id)
    if result is None:
        return ResponseOK(code=500, message="Failed to pause DAG or Airflow not configured")
    return ResponseOK(data=result)


@router.post("/{dag_id}/resume", response_model=ResponseOK[dict], summary="恢复DAG")
async def resume_dag(
    dag_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Resume (unpause) a DAG."""
    result = await airflow_service.resume_dag(db, dag_id)
    if result is None:
        return ResponseOK(code=500, message="Failed to resume DAG or Airflow not configured")
    return ResponseOK(data=result)


@router.post("/{dag_id}/trigger", response_model=ResponseOK[dict], summary="触发DAG运行")
async def trigger_dag(
    dag_id: str,
    body: TriggerDagBody,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Trigger a new DAG run with the provided configuration."""
    result = await airflow_service.trigger_dag(db, dag_id, conf=body.conf)
    if result is None:
        return ResponseOK(code=500, message="Failed to trigger DAG or Airflow not configured")
    return ResponseOK(data=result)


@router.get("/{dag_id}/runs", response_model=ResponseOK[list], summary="DAG运行列表")
async def list_dag_runs(
    dag_id: str,
    limit: int = Query(50, ge=1, description="返回数量上限"),
    offset: int = Query(0, ge=0, description="分页偏移量"),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """List recent DAG runs for a given DAG."""
    result = await airflow_service.list_dag_runs(
        db, dag_id, limit=limit, offset=offset
    )
    return ResponseOK(data=result)


@router.get(
    "/{dag_id}/runs/{run_id}", response_model=ResponseOK[dict], summary="DAG运行详情"
)
async def get_dag_run_detail(
    dag_id: str,
    run_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get DAG run detail including task instances."""
    result = await airflow_service.get_dag_run_detail(db, dag_id, run_id)
    if result is None:
        return ResponseOK(code=404, message="DAG run not found or Airflow not configured")
    return ResponseOK(data=result)


@router.get(
    "/{dag_id}/runs/{run_id}/log",
    response_model=ResponseOK[str],
    summary="任务日志",
)
async def get_dag_run_log(
    dag_id: str,
    run_id: str,
    task_id: str = Query(..., description="任务实例ID"),
    try_number: int = Query(1, ge=1, description="尝试次数"),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Fetch execution log for a specific task instance."""
    result = await airflow_service.get_dag_run_log(
        db, dag_id, run_id, task_id, try_number=try_number
    )
    return ResponseOK(data=result)


@router.post(
    "/{dag_id}/runs/{run_id}/retry",
    response_model=ResponseOK[dict],
    summary="重试失败任务",
)
async def retry_dag_run(
    dag_id: str,
    run_id: str,
    body: RetryDagRunBody,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Retry a failed task instance by clearing its state.

    The Airflow scheduler will pick up the cleared task and re-run it.
    """
    result = await airflow_service.retry_dag_run(db, dag_id, run_id, body.task_id)
    code = 200 if result.get("success") else 500
    return ResponseOK(code=code, message=result.get("message", ""), data=result)
