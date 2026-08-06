"""首页驾驶舱接口: 统计卡片 + 运行状态 + 任务实例。"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, PaginationParams
from app.schemas.common import ResponseOK, PageResponse, PageResult
from app.services import dashboard_service

router = APIRouter()


@router.get("/stats", response_model=ResponseOK[dict], summary="平台统计")
async def get_dashboard_stats(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    stats = await dashboard_service.get_stats(db)
    return ResponseOK(data=stats)


@router.get("/recent-tasks", response_model=ResponseOK[list[dict]], summary="最近任务执行")
async def get_recent_tasks(limit: int = 10, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    tasks = await dashboard_service.get_recent_tasks(db, limit)
    return ResponseOK(data=tasks)


@router.get("/task-instances", response_model=PageResponse[dict], summary="任务实例列表")
async def list_task_instances(
    pagination: PaginationParams = Depends(),
    task_type: str | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    items, total = await dashboard_service.list_task_instances(
        db, pagination.page, pagination.page_size, task_type, status
    )
    return PageResponse(data=PageResult.create(items, total, pagination.page, pagination.page_size))


@router.get("/component-status", response_model=ResponseOK[list[dict]], summary="组件状态")
async def get_component_status(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    status = await dashboard_service.get_component_status(db)
    return ResponseOK(data=status)
