"""数据服务 API Schema。"""
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ParameterItem(BaseModel):
    """API 参数定义 (用于校验)。"""
    name: str = Field(..., description="参数名")
    type: str = Field("string", description="参数类型: string/int/float/bool")
    required: bool = Field(False, description="是否必填")


class DataServiceCreate(BaseModel):
    """创建数据服务 API。"""
    api_name: str = Field(..., max_length=100, description="API名称")
    service_code: str = Field(..., min_length=2, max_length=100, pattern=r"^[a-z][a-z0-9_]*$")
    service_type: str = Field("custom_sql", description="服务类型: table/custom_sql/metric")
    api_path: Optional[str] = Field(None, max_length=200, description="API路径(自动生成)")
    method: str = Field("GET", description="HTTP方法: GET/POST")
    description: Optional[str] = Field(None, description="描述")
    sql_template: str = Field("", description="SQL模板, 使用 ${param} 占位符")
    parameters: list[dict] = Field(default=[], description="参数定义列表")
    datasource_id: Optional[str] = None
    database: str = Field("", description="目标数据库")
    table_name: Optional[str] = None
    selected_fields: list[str] = Field(default=[])
    filter_fields: list[dict] = Field(default=[])
    metric_ids: list[str] = Field(default=[])
    metric_dimensions: list[str] = Field(default=[])
    time_dimension: Optional[str] = None
    default_granularity: Optional[str] = "day"
    max_rows: int = Field(1000, ge=1, le=10000)
    cache_enabled: bool = False
    cache_ttl: int = Field(300, ge=0, le=86400)

    @field_validator("service_type")
    @classmethod
    def validate_service_type(cls, value: str) -> str:
        if value not in {"table", "custom_sql", "metric"}:
            raise ValueError("Unsupported service type")
        return value

    @model_validator(mode="after")
    def validate_source_config(self):
        if self.service_type in {"table", "custom_sql"} and not self.datasource_id:
            raise ValueError("请选择数据源")
        if self.service_type == "table" and (not self.table_name or not self.selected_fields):
            raise ValueError("物理表服务必须选择表和返回字段")
        if self.service_type == "custom_sql" and not self.sql_template.strip():
            raise ValueError("自定义 SQL 服务必须填写 SQL")
        if self.service_type == "metric" and not self.metric_ids:
            raise ValueError("指标服务必须至少选择一个指标")
        return self


class DataServiceUpdate(BaseModel):
    """更新数据服务 API (所有字段可选)。"""
    api_name: Optional[str] = Field(None, max_length=100)
    service_code: Optional[str] = Field(None, min_length=2, max_length=100, pattern=r"^[a-z][a-z0-9_]*$")
    service_type: Optional[str] = None
    api_path: Optional[str] = Field(None, max_length=200)
    method: Optional[str] = None
    description: Optional[str] = None
    sql_template: Optional[str] = None
    parameters: Optional[list[dict]] = None
    datasource_id: Optional[str] = None
    database: Optional[str] = None
    table_name: Optional[str] = None
    selected_fields: Optional[list[str]] = None
    filter_fields: Optional[list[dict]] = None
    metric_ids: Optional[list[str]] = None
    metric_dimensions: Optional[list[str]] = None
    time_dimension: Optional[str] = None
    default_granularity: Optional[str] = None
    max_rows: Optional[int] = Field(None, ge=1, le=10000)
    cache_enabled: Optional[bool] = None
    cache_ttl: Optional[int] = Field(None, ge=0)
    status: Optional[str] = None


class DataServiceResponse(BaseModel):
    """数据服务 API 响应。"""
    id: str
    api_name: str
    service_code: str
    service_type: str
    api_path: str
    method: str
    description: Optional[str] = None
    sql_template: str
    parameters: list[dict] = []
    datasource_id: Optional[str] = None
    datasource_name: Optional[str] = None
    database: str
    table_name: Optional[str] = None
    selected_fields: list[str] = []
    filter_fields: list[dict] = []
    metric_ids: list[str] = []
    metric_dimensions: list[str] = []
    time_dimension: Optional[str] = None
    default_granularity: Optional[str] = None
    max_rows: int = 1000
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
    cache_hit: bool = False


class AppKeyCreate(BaseModel):
    key_name: str = Field(..., min_length=2, max_length=100)
    expires_at: Optional[datetime] = None


class AppKeyCreatedResponse(BaseModel):
    id: str
    key_name: str
    app_key: str
    key_prefix: str
    expires_at: Optional[datetime] = None
