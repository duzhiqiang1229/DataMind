"""认证相关 Schema。"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """登录请求。"""
    username: str = Field(..., min_length=2, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=100, description="密码")


class TokenResponse(BaseModel):
    """登录成功返回的 Token。"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshTokenRequest(BaseModel):
    """刷新 Token 请求。"""
    refresh_token: str


class CurrentUserResponse(BaseModel):
    """当前登录用户信息 (含角色和权限)。"""
    id: str
    username: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    avatar: Optional[str] = None
    department: Optional[str] = None
    roles: list[str] = []           # ["admin", "data_engineer"]
    permissions: list[str] = []    # ["datax:task:create", "doris:query:execute"]
    menus: list[dict] = []          # 菜单树
