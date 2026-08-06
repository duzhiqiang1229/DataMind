"""发布管理接口: 创建发布任务 + 执行 + 查看记录。"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, PaginationParams
from app.schemas.publish import PublishTaskCreate
from app.schemas.common import ResponseOK, PageResponse, PageResult
from app.services import publish_service

router = APIRouter()


@router.get("", response_model=PageResponse[dict], summary="发布任务列表")
async def list_publish_tasks(
    pagination: PaginationParams = Depends(),
    publish_type: str | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    items, total = await publish_service.list_tasks(
        db, pagination.page, pagination.page_size, publish_type, status
    )
    return PageResponse(data=PageResult.create(items, total, pagination.page, pagination.page_size))


@router.post("", response_model=ResponseOK[dict], summary="创建发布任务")
async def create_publish_task(
    req: PublishTaskCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        result = await publish_service.create_task(db, req, user.id)
        return ResponseOK(data=result)
    except ValueError as e:
        return ResponseOK(code=400, message=str(e))


@router.get("/{task_id}", response_model=ResponseOK[dict], summary="发布任务详情")
async def get_publish_task(task_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await publish_service.get_task(db, uuid.UUID(task_id))
    if not result:
        return ResponseOK(code=404, message="Publish task not found")
    return ResponseOK(data=result)


@router.post("/{task_id}/execute", response_model=ResponseOK[dict], summary="执行发布任务")
async def execute_publish_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        result = await publish_service.execute_task(db, uuid.UUID(task_id))
        if not result:
            return ResponseOK(code=404, message="Publish task not found")
        return ResponseOK(data=result)
    except Exception as e:
        return ResponseOK(code=500, message=str(e))


@router.delete("/{task_id}", response_model=ResponseOK, summary="删除发布任务")
async def delete_publish_task(task_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    ok = await publish_service.delete_task(db, uuid.UUID(task_id))
    if not ok:
        return ResponseOK(code=404, message="Publish task not found")
    return ResponseOK()
