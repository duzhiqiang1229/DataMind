"""用户管理接口: CRUD + 重置密码 + 启用/禁用 + 分配角色。"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role, PaginationParams
from app.schemas.common import ResponseOK, PageResponse, PageResult
from app.services import user_service

router = APIRouter(dependencies=[Depends(require_role("admin"))])


class UserCreate(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)
    email: Optional[str] = None
    phone: Optional[str] = None
    full_name: Optional[str] = None
    department: Optional[str] = None
    role_ids: list[str] = []


class UserUpdate(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    full_name: Optional[str] = None
    department: Optional[str] = None
    avatar: Optional[str] = None
    status: Optional[str] = None


class ResetPassword(BaseModel):
    new_password: str = Field(..., min_length=6, max_length=100)


class AssignRoles(BaseModel):
    role_ids: list[str] = []


@router.get("", response_model=PageResponse[dict], summary="用户列表")
async def list_users(
    pagination: PaginationParams = Depends(),
    keyword: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    items, total = await user_service.list_users(
        db, pagination.page, pagination.page_size, keyword, status
    )
    return PageResponse(data=PageResult.create(items, total, pagination.page, pagination.page_size))


@router.post("", response_model=ResponseOK[dict], summary="新增用户")
async def create_user(
    req: UserCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    result = await user_service.create_user(
        db, req.username, req.password,
        req.email, req.phone, req.full_name, req.department, req.role_ids
    )
    return ResponseOK(data=result)


@router.get("/{user_id}", response_model=ResponseOK[dict], summary="用户详情")
async def get_user(user_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await user_service.get_user(db, uuid.UUID(user_id))
    if not result:
        return ResponseOK(code=404, message="User not found")
    return ResponseOK(data=result)


@router.put("/{user_id}", response_model=ResponseOK[dict], summary="更新用户")
async def update_user(
    user_id: str,
    req: UserUpdate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    result = await user_service.update_user(db, uuid.UUID(user_id), **req.model_dump())
    if not result:
        return ResponseOK(code=404, message="User not found")
    return ResponseOK(data=result)


@router.delete("/{user_id}", response_model=ResponseOK, summary="删除用户")
async def delete_user(user_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    ok = await user_service.delete_user(db, uuid.UUID(user_id))
    if not ok:
        return ResponseOK(code=404, message="User not found")
    return ResponseOK()


@router.post("/{user_id}/reset-password", response_model=ResponseOK, summary="重置密码")
async def reset_password(
    user_id: str,
    req: ResetPassword,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    await user_service.reset_password(db, uuid.UUID(user_id), req.new_password)
    return ResponseOK()


@router.post("/{user_id}/toggle-status", response_model=ResponseOK[dict], summary="启用/禁用")
async def toggle_user_status(user_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await user_service.toggle_status(db, uuid.UUID(user_id))
    if not result:
        return ResponseOK(code=404, message="User not found")
    return ResponseOK(data=result)


@router.put("/{user_id}/roles", response_model=ResponseOK[dict], summary="分配角色")
async def assign_roles(
    user_id: str,
    req: AssignRoles,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    result = await user_service.assign_roles(db, uuid.UUID(user_id), req.role_ids)
    if not result:
        return ResponseOK(code=404, message="User not found")
    return ResponseOK(data=result)
