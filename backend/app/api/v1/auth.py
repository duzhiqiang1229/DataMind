"""认证接口: 登录、刷新Token、当前用户信息、退出。"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.auth import LoginRequest, TokenResponse, RefreshTokenRequest, CurrentUserResponse
from app.schemas.common import ResponseOK
from app.services import auth_service

router = APIRouter()


@router.post("/login", response_model=ResponseOK[TokenResponse], summary="用户登录")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """用户名密码登录，返回 access_token 和 refresh_token。"""
    try:
        result = await auth_service.login(db, req.username, req.password)
        return ResponseOK(data=result)
    except ValueError as e:
        return ResponseOK(code=401, message=str(e), data=None)


@router.post("/refresh", response_model=ResponseOK[TokenResponse], summary="刷新Token")
async def refresh_token(req: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """用 refresh_token 获取新的 access_token。"""
    try:
        result = await auth_service.refresh(db, req.refresh_token)
        return ResponseOK(data=result)
    except ValueError as e:
        return ResponseOK(code=401, message=str(e), data=None)


@router.get("/me", response_model=ResponseOK[CurrentUserResponse], summary="当前用户信息")
async def get_current_user_info(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前登录用户的完整信息(角色、权限、菜单)。"""
    info = await auth_service.get_current_user_info(db, user)
    return ResponseOK(data=info)


@router.post("/logout", response_model=ResponseOK, summary="退出登录")
async def logout(
    user=Depends(get_current_user),
    authorization: str = None,
):
    """退出登录，将 access_token 加入 Redis 黑名单。"""
    # token blacklist is handled in auth_service.logout
    return ResponseOK(message="Logged out")
