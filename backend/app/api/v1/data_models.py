"""数据模型管理接口: CRUD + 字段管理 + 版本管理 + DDL。"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, PaginationParams
from app.schemas.data_model import DataModelCreate, DataModelUpdate
from app.schemas.common import ResponseOK, PageResponse, PageResult
from app.services import data_model_service

router = APIRouter()


@router.get("", response_model=PageResponse[dict], summary="数据模型列表")
async def list_models(
    pagination: PaginationParams = Depends(),
    layer: str | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    items, total = await data_model_service.list_models(
        db, pagination.page, pagination.page_size, layer, status
    )
    return PageResponse(data=PageResult.create(items, total, pagination.page, pagination.page_size))


@router.post("", response_model=ResponseOK[dict], summary="创建数据模型")
async def create_model(
    req: DataModelCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        result = await data_model_service.create_model(db, req, user.id)
        return ResponseOK(data=result)
    except ValueError as e:
        return ResponseOK(code=400, message=str(e))


@router.get("/{model_id}", response_model=ResponseOK[dict], summary="模型详情")
async def get_model(model_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await data_model_service.get_model(db, uuid.UUID(model_id))
    if not result:
        return ResponseOK(code=404, message="Model not found")
    return ResponseOK(data=result)


@router.put("/{model_id}", response_model=ResponseOK[dict], summary="更新模型")
async def update_model(
    model_id: str,
    req: DataModelUpdate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    result = await data_model_service.update_model(db, uuid.UUID(model_id), req)
    if not result:
        return ResponseOK(code=404, message="Model not found")
    return ResponseOK(data=result)


@router.delete("/{model_id}", response_model=ResponseOK, summary="删除模型")
async def delete_model(model_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    ok = await data_model_service.delete_model(db, uuid.UUID(model_id))
    if not ok:
        return ResponseOK(code=404, message="Model not found")
    return ResponseOK()


@router.get("/{model_id}/versions", response_model=ResponseOK[list], summary="版本历史")
async def list_versions(model_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await data_model_service.list_versions(db, uuid.UUID(model_id))
    return ResponseOK(data=result)
