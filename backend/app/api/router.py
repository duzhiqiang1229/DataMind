"""API router aggregation."""
from fastapi import APIRouter

from app.api.v1 import (
    auth,
    users,
    roles,
    menus,
    components,
    datasources,
    datax_tasks,
    doris_query,
    dashboard,
    system,
)

api_router = APIRouter()

# Auth (no auth required)
api_router.include_router(auth.router, prefix="/auth", tags=["认证"])

# User & RBAC
api_router.include_router(users.router, prefix="/users", tags=["用户管理"])
api_router.include_router(roles.router, prefix="/roles", tags=["角色管理"])
api_router.include_router(menus.router, prefix="/menus", tags=["菜单管理"])

# Component & Data Source
api_router.include_router(components.router, prefix="/components", tags=["组件配置"])
api_router.include_router(datasources.router, prefix="/datasources", tags=["数据源管理"])

# Data Integration
api_router.include_router(datax_tasks.router, prefix="/datax-tasks", tags=["DataX同步"])
api_router.include_router(doris_query.router, prefix="/doris-query", tags=["数据查询"])

# Dashboard & System
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["首页驾驶舱"])
api_router.include_router(system.router, prefix="/system", tags=["系统管理"])
