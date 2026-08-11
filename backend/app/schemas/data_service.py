"""数据服务 API Schema。"""
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class ParameterItem(BaseModel):
    """API 参数定义 (用于校验)。"""
    name: str = Field(..., description="参数名")
    type: str = Field("string", description="参数类型: string/int/float/bool")
    required: bool = Field(False, description="是否必填")


class DataServiceCreate(BaseModel):
    """创建数据服务 API。"""
    api_name: str = Field(..., max_length=100, description="API名称")
    api_path: str = Field(..., max_length=200, description="API路径(唯一)")
    method: str = Field("GET", description="HTTP方法: GET/POST")
    description: Optional[str] = Field(None, description="描述")
    sql_template: str = Field(..., description="SQL模板, 使用 ${param} 占位符")
    parameters: list[dict] = Field(default=[], description="参数定义列表")
    database: str = Field("default", description="目标数据库")


class DataServiceUpdate(BaseModel):
    """更新数据服务 API (所有字段可选)。"""
    api_name: Optional[str] = Field(None, max_length=100)
    api_path: Optional[str] = Field(None, max_length=200)
    method: Optional[str] = None
    description: Optional[str] = None
    sql_template: Optional[str] = None
    parameters: Optional[list[dict]] = None
    database: Optional[str] = None
    cache_enabled: Optional[bool] = None
    cache_ttl: Optional[int] = Field(None, ge=0)
    status: Optional[str] = None


class DataServiceResponse(BaseModel):
    """数据服务 API 响应。"""
    id: str
    api_name: str
    api_path: str
    method: str
    description: Optional[str] = None
    sql_template: str
    parameters: list[dict] = []
    database: str
    cache_enabled: bool = False
    cache_ttl: int = 300
    status: str
    call_count: int = 0
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExecuteRequest(BaseModel):
    """执行 API 请求体。"""
    params: dict = Field(default={}, description="参数键值对")


class ExecuteResultResponse(BaseModel):
    """执行结果响应。"""
    api_id: str
    api_path: str
    columns: list[str] = []
    rows: list[dict] = []
    row_count: int
    truncated: bool = False
    elapsed_ms: int
