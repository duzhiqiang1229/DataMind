"""组件配置接口: CRUD + 健康检查。"""
from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, PaginationParams
from app.schemas.component import (
    ComponentConfigCreate, ComponentConfigUpdate, ComponentConfigResponse,
    HealthCheckResponse,
)
from app.schemas.common import ResponseOK, PageResponse, PageResult
from app.services import component_service

router = APIRouter()


@router.get("", response_model=PageResponse[ComponentConfigResponse], summary="组件列表")
async def list_components(
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    items, total = await component_service.list_components(db, pagination.page, pagination.page_size)
    items = [_to_response(i) for i in items]
    return PageResponse(data=PageResult.create(items, total, pagination.page, pagination.page_size))


@router.post("", response_model=ResponseOK[ComponentConfigResponse], summary="新增组件配置")
async def create_component(
    req: ComponentConfigCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    cfg = await component_service.create_component(db, req)
    return ResponseOK(data=_to_response(cfg))


@router.get("/{component_id}", response_model=ResponseOK[ComponentConfigResponse], summary="组件详情")
async def get_component(component_id: UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    cfg = await component_service.get_component(db, component_id)
    if not cfg:
        return ResponseOK(code=404, message="Component not found")
    return ResponseOK(data=_to_response(cfg))


@router.put("/{component_id}", response_model=ResponseOK[ComponentConfigResponse], summary="更新组件配置")
async def update_component(
    component_id: UUID,
    req: ComponentConfigUpdate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    cfg = await component_service.update_component(db, component_id, req)
    if not cfg:
        return ResponseOK(code=404, message="Component not found")
    return ResponseOK(data=_to_response(cfg))


@router.delete("/{component_id}", response_model=ResponseOK, summary="删除组件配置")
async def delete_component(component_id: UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    ok = await component_service.delete_component(db, component_id)
    if not ok:
        return ResponseOK(code=404, message="Component not found")
    return ResponseOK()


@router.post("/{component_code}/health-check", response_model=ResponseOK[HealthCheckResponse], summary="健康检查")
async def health_check(component_code: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await component_service.health_check(db, component_code)
    return ResponseOK(data=result)


def _to_response(cfg) -> dict:
    return {
        "id": str(cfg.id),
        "component_code": cfg.component_code,
        "component_name": cfg.component_name,
        "component_type": cfg.component_type,
        "base_url": cfg.base_url,
        "config_json": cfg.config_json,
        "auth_type": cfg.auth_type,
        "status": cfg.status,
        "last_check_at": cfg.last_check_at,
        "last_check_ok": cfg.last_check_ok,
        "created_at": cfg.created_at,
        "updated_at": cfg.updated_at,
    }
