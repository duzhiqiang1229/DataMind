"""Airflow DAG management API: list, trigger, pause/resume, runs, logs, retry."""
from typing import Optional
import uuid

from fastapi import APIRouter, Body, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role, PaginationParams
from app.schemas.common import ResponseOK, PageResponse, PageResult
from app.services import airflow_service

router = APIRouter()
engineer_only = [Depends(require_role("data_engineer"))]


# --- Request body schemas ---


class TriggerDagBody(BaseModel):
    """Request body for triggering a DAG run."""
    conf: dict = {}


class RetryDagRunBody(BaseModel):
    """Request body for retrying a failed task instance."""
    task_id: str


class CreateDagFileBody(BaseModel):
    """Request body for creating a scheduling script (.py DAG file)."""
    script_name: str
    content: str


class UpdateDagFileBody(BaseModel):
    """Request body for saving a DAG file's content."""
    content: str


@router.get("/dag-runs", response_model=PageResponse[dict], summary="DAG 运行记录(同步)")
async def dag_runs(
    pagination: PaginationParams = Depends(),
    dag_id: str | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    items, total = await airflow_service.list_dag_runs_page(
        db, pagination.page, pagination.page_size, dag_id, status
    )
    return PageResponse(data=PageResult.create(items, total, pagination.page, pagination.page_size))


@router.post("/sync-runs", response_model=ResponseOK[dict], summary="手动同步 DAG 运行记录", dependencies=engineer_only)
async def sync_runs(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    result = await airflow_service.sync_dag_runs(db)
    return ResponseOK(data=result)


@router.get("/dag-runs/{record_id}/tasks", response_model=ResponseOK[list], summary="运行记录任务明细")
async def dag_run_tasks(
    record_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    return ResponseOK(data=await airflow_service.list_recorded_task_runs(db, record_id))


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


@router.post("/{dag_id}/pause", response_model=ResponseOK[dict], summary="暂停DAG", dependencies=engineer_only)
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


@router.post("/{dag_id}/resume", response_model=ResponseOK[dict], summary="恢复DAG", dependencies=engineer_only)
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


@router.post("/{dag_id}/trigger", response_model=ResponseOK[dict], summary="触发DAG运行", dependencies=engineer_only)
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
    dependencies=engineer_only,
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


@router.put("/{dag_id}/schedule", response_model=ResponseOK[dict], summary="更新调度配置", dependencies=engineer_only)
async def update_schedule(
    dag_id: str,
    schedule: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    result = await airflow_service.update_dag_schedule(db, dag_id, schedule.get("schedule_interval", ""))
    if not result:
        return ResponseOK(code=503, message="Airflow not configured or update failed")
    return ResponseOK(data=result)


@router.post("/dag-files", response_model=ResponseOK[dict], summary="新增调度脚本(.py DAG文件)", dependencies=engineer_only)
async def create_dag_file(
    body: CreateDagFileBody,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Write a new scheduling script (.py) into the Airflow dags folder.

    The script is a self-contained Airflow DAG file; the scheduler parses it
    automatically, so DAG name / schedule / status come from the script.
    """
    try:
        result = await airflow_service.create_dag_file(db, body.script_name, body.content)
    except ValueError as e:
        return ResponseOK(code=400, message=str(e))
    except RuntimeError as e:
        return ResponseOK(code=503, message=str(e))
    return ResponseOK(data=result)


@router.get("/{dag_id}/file", response_model=ResponseOK[dict], summary="读取DAG文件内容")
async def get_dag_file(
    dag_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    result = await airflow_service.get_dag_file(db, dag_id)
    if result is None:
        return ResponseOK(code=404, message="DAG 文件不存在或无法读取")
    return ResponseOK(data=result)


@router.put("/{dag_id}/file", response_model=ResponseOK[dict], summary="保存DAG文件内容", dependencies=engineer_only)
async def update_dag_file(
    dag_id: str,
    body: UpdateDagFileBody,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        result = await airflow_service.update_dag_file(db, dag_id, body.content)
    except ValueError as e:
        return ResponseOK(code=400, message=str(e))
    if result is None:
        return ResponseOK(code=404, message="DAG 文件不存在或无法写入")
    return ResponseOK(data=result)
