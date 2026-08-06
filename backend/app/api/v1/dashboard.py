"""首页驾驶舱接口: 统计卡片 + 运行状态。"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.common import ResponseOK
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


@router.get("/component-status", response_model=ResponseOK[list[dict]], summary="组件状态")
async def get_component_status(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    status = await dashboard_service.get_component_status(db)
    return ResponseOK(data=status)
