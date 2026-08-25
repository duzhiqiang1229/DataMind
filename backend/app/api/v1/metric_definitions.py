"""指标定义接口."""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, PaginationParams
from app.schemas.common import ResponseOK, PageResponse, PageResult
from app.schemas.metric_definition import (
    MetricDefinitionCreate, MetricDefinitionUpdate,
)
from app.services import metric_definition_service

router = APIRouter()


@router.get("", response_model=PageResponse[dict], summary="指标定义列表")
async def list_definitions(
    pagination: PaginationParams = Depends(),
    keyword: str | None = None,
    category_id: str | None = None,
    metric_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    items, total = await metric_definition_service.list_definitions(
        db, pagination.page, pagination.page_size, keyword, category_id, metric_type
    )
    return PageResponse(data=PageResult.create(items, total, pagination.page, pagination.page_size))


@router.post("", response_model=ResponseOK[dict], summary="新建指标定义")
async def create_definition(
    req: MetricDefinitionCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    result = await metric_definition_service.create_definition(db, req)
    return ResponseOK(data=result)


@router.put("/{definition_id}", response_model=ResponseOK[dict], summary="更新指标定义")
async def update_definition(
    definition_id: str,
    req: MetricDefinitionUpdate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    result = await metric_definition_service.update_definition(
        db, uuid.UUID(definition_id), req
    )
    if not result:
        return ResponseOK(code=404, message="Metric definition not found")
    return ResponseOK(data=result)


@router.delete("/{definition_id}", response_model=ResponseOK, summary="删除指标定义")
async def delete_definition(
    definition_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    ok = await metric_definition_service.delete_definition(db, uuid.UUID(definition_id))
    if not ok:
        return ResponseOK(code=404, message="Metric definition not found")
    return ResponseOK()
