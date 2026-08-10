"""指标分类管理接口."""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.common import ResponseOK
from app.schemas.metric_category import (
    MetricCategoryCreate, MetricCategoryUpdate,
    MetricMappingCreate,
)
from app.services import metric_category_service

router = APIRouter()


@router.get("", response_model=ResponseOK[list[dict]], summary="指标分类列表")
async def list_categories(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    result = await metric_category_service.list_categories(db)
    return ResponseOK(data=result)


@router.post("", response_model=ResponseOK[dict], summary="新建指标分类")
async def create_category(
    req: MetricCategoryCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    result = await metric_category_service.create_category(db, req)
    return ResponseOK(data=result)


@router.put("/{category_id}", response_model=ResponseOK[dict], summary="更新指标分类")
async def update_category(
    category_id: str,
    req: MetricCategoryUpdate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    result = await metric_category_service.update_category(
        db, uuid.UUID(category_id), req
    )
    if not result:
        return ResponseOK(code=404, message="Category not found")
    return ResponseOK(data=result)


@router.delete("/{category_id}", response_model=ResponseOK, summary="删除指标分类")
async def delete_category(
    category_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    ok = await metric_category_service.delete_category(db, uuid.UUID(category_id))
    if not ok:
        return ResponseOK(code=404, message="Category not found")
    return ResponseOK()


@router.post("/{category_id}/metrics", response_model=ResponseOK[dict], summary="分配指标到分类")
async def assign_metric(
    category_id: str,
    req: MetricMappingCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    result = await metric_category_service.assign_metric(
        db, uuid.UUID(category_id), req.metric_name, req.metric_label
    )
    return ResponseOK(data=result)


@router.get("/{category_id}/metrics", response_model=ResponseOK[list[dict]], summary="分类下指标列表")
async def list_metrics_by_category(
    category_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    result = await metric_category_service.list_metrics_by_category(
        db, uuid.UUID(category_id)
    )
    return ResponseOK(data=result)


@router.get("/unmapped", response_model=ResponseOK[list[dict]], summary="未分类指标列表")
async def list_unmapped_metrics(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    result = await metric_category_service.list_unmapped_metrics(db)
    return ResponseOK(data=result)
