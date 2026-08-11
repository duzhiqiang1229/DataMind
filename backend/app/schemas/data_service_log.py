"""Data service call log & permission schemas."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CallLogResponse(BaseModel):
    """单个调用日志记录响应。"""

    id: str
    api_id: str
    api_path: str
    caller_user_id: Optional[str] = None
    caller_username: Optional[str] = None
    request_params: Optional[str] = None
    status: str
    row_count: Optional[int] = None
    elapsed_ms: Optional[int] = None
    error_message: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CallLogListResponse(BaseModel):
    """调用日志列表项 (兼容分页)。"""

    id: str
    api_id: str
    api_path: str
    caller_username: Optional[str] = None
    status: str
    row_count: Optional[int] = None
    elapsed_ms: Optional[int] = None
    error_message: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CallStatsResponse(BaseModel):
    """调用统计响应。"""

    total_calls: int = 0
    success_count: int = 0
    failed_count: int = 0
    avg_elapsed_ms: float = 0
    daily_trend: list[dict] = Field(default=[], description="每日趋势: [{date, count, success, failed}]")


class DataServicePermissionCreate(BaseModel):
    """分配数据服务权限请求体。

    api_id 通常由 URL 路径提供，body 中可不传。
    """

    api_id: Optional[UUID] = Field(None, description="API ID (由路径提供时可省略)")
    role_id: UUID = Field(..., description="角色ID")
    permission: str = Field("call", description="权限: call / admin")
