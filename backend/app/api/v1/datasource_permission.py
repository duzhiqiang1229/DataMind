"""数据源权限管理接口."""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.common import ResponseOK
from app.schemas.datasource_permission import DatasourcePermissionCreate
from app.services import datasource_permission_service

router = APIRouter()


@router.get("/{datasource_id}", response_model=ResponseOK[list[dict]], summary="数据源权限列表")
async def list_permissions(
    datasource_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    result = await datasource_permission_service.list_permissions(
        db, uuid.UUID(datasource_id)
    )
    return ResponseOK(data=result)


@router.post("", response_model=ResponseOK[dict], summary="分配/更新数据源权限")
async def assign_permission(
    req: DatasourcePermissionCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    result = await datasource_permission_service.assign_permission(db, req)
    return ResponseOK(data=result)


@router.delete("/{datasource_id}/{role_id}", response_model=ResponseOK, summary="撤销数据源权限")
async def revoke_permission(
    datasource_id: str,
    role_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    ok = await datasource_permission_service.revoke_permission(
        db, uuid.UUID(datasource_id), uuid.UUID(role_id)
    )
    if not ok:
        return ResponseOK(code=404, message="Permission not found")
    return ResponseOK()
