"""DataX 同步任务接口: CRUD + 生成配置 + 触发 + 执行历史 + 日志。"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, PaginationParams
from app.schemas.datax_task import (
    DataXTaskCreate, DataXTaskUpdate, DataXTaskResponse,
    DataXTaskTrigger, TaskInstanceResponse, TaskLogResponse,
)
from app.schemas.common import ResponseOK, PageResponse, PageResult
from app.services import datax_task_service

router = APIRouter()


@router.get("", response_model=PageResponse[dict], summary="DataX任务列表")
async def list_datax_tasks(
    pagination: PaginationParams = Depends(),
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    items, total = await datax_task_service.list_tasks(db, pagination.page, pagination.page_size, status)
    return PageResponse(data=PageResult.create(items, total, pagination.page, pagination.page_size))


@router.post("", response_model=ResponseOK[dict], summary="创建DataX任务")
async def create_datax_task(
    req: DataXTaskCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        result = await datax_task_service.create_task(db, req, user.id)
        return ResponseOK(data=result)
    except ValueError as e:
        return ResponseOK(code=400, message=str(e))


@router.get("/{task_id}", response_model=ResponseOK[dict], summary="任务详情")
async def get_datax_task(task_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    import uuid
    result = await datax_task_service.get_task(db, uuid.UUID(task_id))
    if not result:
        return ResponseOK(code=404, message="Task not found")
    return ResponseOK(data=result)


@router.put("/{task_id}", response_model=ResponseOK[dict], summary="更新任务")
async def update_datax_task(
    task_id: str,
    req: DataXTaskUpdate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    import uuid
    result = await datax_task_service.update_task(db, uuid.UUID(task_id), req)
    if not result:
        return ResponseOK(code=404, message="Task not found")
    return ResponseOK(data=result)


@router.delete("/{task_id}", response_model=ResponseOK, summary="删除任务")
async def delete_datax_task(task_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    import uuid
    ok = await datax_task_service.delete_task(db, uuid.UUID(task_id))
    if not ok:
        return ResponseOK(code=404, message="Task not found")
    return ResponseOK()


@router.post("/{task_id}/trigger", response_model=ResponseOK[dict], summary="触发任务执行")
async def trigger_datax_task(
    task_id: str,
    req: DataXTaskTrigger = DataXTaskTrigger(),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    import uuid
    try:
        result = await datax_task_service.trigger_task(db, uuid.UUID(task_id), user.id, req.conf)
        return ResponseOK(data=result)
    except ValueError as e:
        return ResponseOK(code=404, message=str(e))


@router.post("/{task_id}/pause", response_model=ResponseOK, summary="暂停定时调度")
async def pause_datax_task(task_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    import uuid
    ok = await datax_task_service.pause_task(db, uuid.UUID(task_id))
    if not ok:
        return ResponseOK(code=404, message="Task not found")
    return ResponseOK()


@router.post("/{task_id}/resume", response_model=ResponseOK, summary="恢复定时调度")
async def resume_datax_task(task_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    import uuid
    ok = await datax_task_service.resume_task(db, uuid.UUID(task_id))
    if not ok:
        return ResponseOK(code=404, message="Task not found")
    return ResponseOK()


@router.get("/{task_id}/instances", response_model=PageResponse[dict], summary="执行历史")
async def list_task_instances(
    task_id: str,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    import uuid
    items, total = await datax_task_service.list_instances(
        db, uuid.UUID(task_id), pagination.page, pagination.page_size
    )
    return PageResponse(data=PageResult.create(items, total, pagination.page, pagination.page_size))


@router.get("/instances/{instance_id}/status", response_model=ResponseOK[dict], summary="执行状态")
async def get_task_instance_status(
    instance_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    import uuid
    result = await datax_task_service.get_instance_status(db, uuid.UUID(instance_id))
    if not result:
        return ResponseOK(code=404, message="Instance not found")
    return ResponseOK(data=result)


@router.get("/instances/{instance_id}/log", response_model=ResponseOK[dict], summary="执行日志")
async def get_task_log(
    instance_id: str,
    task_name: str = "datax_sync_task",
    try_number: int = 1,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    import uuid
    result = await datax_task_service.get_instance_log(
        db, uuid.UUID(instance_id), task_name, try_number
    )
    if not result:
        return ResponseOK(code=404, message="Instance not found")
    return ResponseOK(data=result)
