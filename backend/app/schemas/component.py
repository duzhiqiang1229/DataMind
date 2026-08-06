"""组件配置 Schema。"""
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class ComponentConfigBase(BaseModel):
    """组件配置基础字段。"""
    component_code: str = Field(..., description="组件标识: airflow/doris/cube/openmetadata")
    component_name: str = Field(..., description="组件名称")
    component_type: str = Field(..., description="组件类型: scheduler/olap/semantic/governance")
    base_url: str = Field(..., description="API基础地址")
    config_json: dict = Field(default={}, description="非敏感配置JSON")
    auth_type: str = Field("none", description="认证类型: none/token/basic")
    credentials: Optional[dict] = Field(None, description="敏感凭据(密码/token, 仅写入, 不返回)")


class ComponentConfigCreate(ComponentConfigBase):
    """创建组件配置。"""
    pass


class ComponentConfigUpdate(BaseModel):
    """更新组件配置 (所有字段可选)。"""
    component_name: Optional[str] = None
    base_url: Optional[str] = None
    config_json: Optional[dict] = None
    auth_type: Optional[str] = None
    credentials: Optional[dict] = Field(None, description="更新凭据时传入")
    status: Optional[str] = None


class ComponentConfigResponse(BaseModel):
    """组件配置响应 (不含敏感凭据)。"""
    id: str
    component_code: str
    component_name: str
    component_type: str
    base_url: str
    config_json: dict
    auth_type: str
    status: str
    last_check_at: Optional[datetime] = None
    last_check_ok: Optional[bool] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class HealthCheckResponse(BaseModel):
    """组件健康检查响应。"""
    component_code: str
    component_name: str
    healthy: bool
    message: str = ""
    checked_at: datetime
