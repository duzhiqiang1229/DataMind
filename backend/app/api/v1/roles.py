"""角色管理接口: CRUD + 权限分配 + 菜单分配。"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.schemas.common import ResponseOK
from app.services import role_service

router = APIRouter(dependencies=[Depends(require_role("admin"))])


class RoleCreate(BaseModel):
    role_code: str = Field(..., max_length=50)
    role_name: str = Field(..., max_length=50)
    description: Optional[str] = None


class RoleUpdate(BaseModel):
    role_name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class AssignPermissions(BaseModel):
    permission_ids: list[str] = []


class AssignMenus(BaseModel):
    menu_ids: list[str] = []


@router.get("", response_model=ResponseOK[list[dict]], summary="角色列表")
async def list_roles(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await role_service.list_roles(db)
    return ResponseOK(data=result)


@router.post("", response_model=ResponseOK[dict], summary="新增角色")
async def create_role(req: RoleCreate, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await role_service.create_role(db, req.role_code, req.role_name, req.description)
    return ResponseOK(data=result)


@router.put("/{role_id}", response_model=ResponseOK[dict], summary="更新角色")
async def update_role(role_id: str, req: RoleUpdate, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await role_service.update_role(db, uuid.UUID(role_id), **req.model_dump())
    if not result:
        return ResponseOK(code=404, message="Role not found")
    return ResponseOK(data=result)


@router.delete("/{role_id}", response_model=ResponseOK, summary="删除角色")
async def delete_role(role_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    ok = await role_service.delete_role(db, uuid.UUID(role_id))
    if not ok:
        return ResponseOK(code=404, message="Role not found")
    return ResponseOK()


@router.put("/{role_id}/permissions", response_model=ResponseOK, summary="分配权限")
async def assign_permissions(role_id: str, req: AssignPermissions, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    await role_service.assign_permissions(db, uuid.UUID(role_id), req.permission_ids)
    return ResponseOK()


@router.put("/{role_id}/menus", response_model=ResponseOK, summary="分配菜单")
async def assign_menus(role_id: str, req: AssignMenus, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    await role_service.assign_menus(db, uuid.UUID(role_id), req.menu_ids)
    return ResponseOK()


@router.get("/permissions", response_model=ResponseOK[list[dict]], summary="权限列表(全量)")
async def list_permissions(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await role_service.list_permissions(db)
    return ResponseOK(data=result)
