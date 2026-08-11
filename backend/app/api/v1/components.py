"""组件配置接口: CRUD + 健康检查。"""
from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role, PaginationParams
from app.schemas.component import (
    ComponentConfigCreate, ComponentConfigUpdate, ComponentConfigResponse,
    HealthCheckResponse,
)
from app.schemas.common import ResponseOK, PageResponse, PageResult
from app.services import component_service

router = APIRouter(dependencies=[Depends(require_role("admin"))])


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


@router.get("/by-code/{component_code}", response_model=ResponseOK[ComponentConfigResponse], summary="按组件标识查询配置")
async def get_component_by_code(component_code: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    cfg = await component_service.get_component_by_code(db, component_code)
    if not cfg:
        return ResponseOK(code=404, message="Component not configured")
    return ResponseOK(data=_to_response(cfg, include_credentials=True))


@router.put("/by-code/{component_code}", response_model=ResponseOK[ComponentConfigResponse], summary="按组件标识保存(upsert)配置")
async def upsert_component_by_code(
    component_code: str,
    req: ComponentConfigUpdate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    cfg = await component_service.upsert_component_by_code(db, component_code, req)
    return ResponseOK(data=_to_response(cfg))


@router.get("/all", response_model=ResponseOK[list[ComponentConfigResponse]], summary="全部组件列表(不分页)")
async def list_all_components(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """List all components without pagination - for the component grid page."""
    from sqlalchemy import select
    from app.models import ComponentConfig
    result = await db.execute(select(ComponentConfig).order_by(ComponentConfig.component_type))
    items = [_to_response(i) for i in result.scalars().all()]
    return ResponseOK(data=items)


@router.get("/{component_id}", response_model=ResponseOK[ComponentConfigResponse], summary="组件详情")
async def get_component(component_id: UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    cfg = await component_service.get_component(db, component_id)
    if not cfg:
        return ResponseOK(code=404, message="Component not found")
    return ResponseOK(data=_to_response(cfg, include_credentials=True))


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


def _to_response(cfg, include_credentials: bool = False) -> dict:
    credentials = {}
    if include_credentials and cfg.credentials_encrypted:
        try:
            import json
            from app.core.security import decrypt_value
            credentials = json.loads(decrypt_value(cfg.credentials_encrypted) or "{}")
        except Exception:
            credentials = {}
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
        "credentials": credentials,
        "created_at": cfg.created_at,
        "updated_at": cfg.updated_at,
    }
