"""数据源 Schema。"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator
import re


class DataSourceBase(BaseModel):
    """数据源基础字段。"""
    source_name: str = Field(..., max_length=100, description="数据源名称")
    source_type: str = Field(..., description="类型: mysql/oracle/postgresql/sqlserver")
    host: str = Field(..., description="主机地址")
    port: int = Field(..., ge=1, le=65535, description="端口")
    database_name: Optional[str] = Field(None, description="数据库名")
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码(仅写入,不返回)")
    default_schema: Optional[str] = Field(None, description="默认Schema")
    description: Optional[str] = Field(None, max_length=500)

    @field_validator("source_type")
    @classmethod
    def validate_source_type(cls, v):
        allowed = {"mysql", "oracle", "postgresql", "sqlserver"}
        if v not in allowed:
            raise ValueError(f"source_type must be one of {allowed}")
        return v


class DataSourceCreate(DataSourceBase):
    pass


class DataSourceUpdate(BaseModel):
    source_name: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    database_name: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    default_schema: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class DataSourceResponse(BaseModel):
    """数据源响应 (不含密码)。"""
    id: str
    source_name: str
    source_type: str
    host: str
    port: int
    database_name: Optional[str] = None
    username: str
    default_schema: Optional[str] = None
    description: Optional[str] = None
    status: str
    last_connection_test: Optional[datetime] = None
    last_connection_ok: Optional[bool] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConnectionTestResponse(BaseModel):
    """连接测试结果。"""
    success: bool
    message: str
    version: Optional[str] = None  # 数据库版本信息
    tested_at: datetime
