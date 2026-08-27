"""API router aggregation."""
from fastapi import APIRouter

from app.api.v1 import (
    auth,
    users,
    roles,
    menus,
    components,
    datasources,
    doris_query,
    data_models,
    publish,
    dashboard,
    system,
    cube,
    airflow,
    data_service,
    metric_category,
    table_owner,
    datasource_permission,
    metric_definitions,
    etl_scripts,
    cube_model,
    data_assets,
    runtime_lineage,
    openlineage,
    mcp_management,
)

api_router = APIRouter()

# Auth (no auth required)
api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(runtime_lineage.router, prefix="/internal/lineage", tags=["运行血缘回调"])
api_router.include_router(openlineage.router, prefix="/internal/openlineage", tags=["OpenLineage事件"])

# User & RBAC
api_router.include_router(users.router, prefix="/users", tags=["用户管理"])
api_router.include_router(roles.router, prefix="/roles", tags=["角色管理"])
api_router.include_router(menus.router, prefix="/menus", tags=["菜单管理"])

# Component & Data Source
api_router.include_router(components.router, prefix="/components", tags=["组件配置"])
api_router.include_router(datasources.router, prefix="/datasources", tags=["数据源管理"])

api_router.include_router(doris_query.router, prefix="/doris-query", tags=["数据查询"])

# Data Development
api_router.include_router(data_models.router, prefix="/data-models", tags=["数据模型"])
api_router.include_router(publish.router, prefix="/publish", tags=["发布管理"])

# Dashboard & System
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["首页驾驶舱"])
api_router.include_router(system.router, prefix="/system", tags=["系统管理"])

# Metrics & Governance
api_router.include_router(cube.router, prefix="/cube", tags=["指标中心"])
api_router.include_router(airflow.router, prefix="/airflow", tags=["Airflow调度"])

# Data Service Center
api_router.include_router(data_service.router, prefix="/data-services", tags=["数据服务"])
api_router.include_router(data_service.public_router, prefix="/open-api/v1", tags=["数据服务调用"])

# Metric Categories & Table Owners & Datasource Permissions
api_router.include_router(metric_category.router, prefix="/metric-categories", tags=["指标分类"])
api_router.include_router(table_owner.router, prefix="/table-owners", tags=["表负责人"])
api_router.include_router(datasource_permission.router, prefix="/datasource-permissions", tags=["数据源权限"])
api_router.include_router(metric_definitions.router, prefix="/metric-definitions", tags=["指标定义"])
api_router.include_router(etl_scripts.router, prefix="/etl-scripts", tags=["ETL 脚本"])
api_router.include_router(cube_model.router, prefix="/cube-model", tags=["Cube 建模"])
api_router.include_router(data_assets.router, prefix="/assets", tags=["数据资产"])
api_router.include_router(mcp_management.router, prefix="/mcp-management", tags=["MCP管理"])
