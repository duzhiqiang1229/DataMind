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
    spark_tasks,
    doris_query,
    data_models,
    publish,
    dashboard,
    system,
    cube,
    openmetadata,
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
api_router.include_router(spark_tasks.router, prefix="/spark-tasks", tags=["Spark任务"])
api_router.include_router(doris_query.router, prefix="/doris-query", tags=["数据查询"])

# Data Development
api_router.include_router(data_models.router, prefix="/data-models", tags=["数据模型"])
api_router.include_router(publish.router, prefix="/publish", tags=["发布管理"])

# Dashboard & System
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["首页驾驶舱"])
api_router.include_router(system.router, prefix="/system", tags=["系统管理"])

# Metrics & Governance
api_router.include_router(cube.router, prefix="/cube", tags=["指标中心"])
api_router.include_router(openmetadata.router, prefix="/openmetadata", tags=["数据治理"])
