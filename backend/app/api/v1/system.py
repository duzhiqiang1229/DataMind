"""系统管理接口: 配置 + 日志。"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role, PaginationParams
from app.schemas.common import ResponseOK, PageResponse, PageResult
from app.services import system_service

router = APIRouter(dependencies=[Depends(require_role("admin"))])


class ConfigUpdate(BaseModel):
    config_value: str


# 系统配置
@router.get("/configs", response_model=ResponseOK[list[dict]], summary="系统配置列表")
async def list_configs(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await system_service.list_configs(db)
    return ResponseOK(data=result)


@router.put("/configs/{config_key}", response_model=ResponseOK[dict], summary="更新配置")
async def update_config(
    config_key: str,
    req: ConfigUpdate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        result = await system_service.update_config(db, config_key, req.config_value, user.id)
        if not result:
            return ResponseOK(code=404, message="Config not found")
        return ResponseOK(data=result)
    except ValueError as e:
        return ResponseOK(code=400, message=str(e))


# 操作日志
@router.get("/logs", response_model=PageResponse[dict], summary="操作日志")
async def list_logs(
    pagination: PaginationParams = Depends(),
    module: str | None = None,
    user_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    items, total = await system_service.list_logs(
        db, pagination.page, pagination.page_size, module, user_id
    )
    return PageResponse(data=PageResult.create(items, total, pagination.page, pagination.page_size))
