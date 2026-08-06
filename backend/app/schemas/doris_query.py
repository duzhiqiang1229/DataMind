"""Doris 查询 Schema。"""
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """SQL 查询请求。"""
    sql: str = Field(..., description="SQL语句(仅支持SELECT)")
    database: Optional[str] = Field(None, description="指定数据库")
    limit: int = Field(10000, ge=1, le=100000, description="最大返回行数")


class QueryResultResponse(BaseModel):
    """查询结果。"""
    columns: list[str] = Field([], description="列名列表")
    rows: list[dict] = Field([], description="数据行(列名:值)")
    row_count: int
    truncated: bool = Field(False, description="是否被截断(超过limit)")
    elapsed_ms: int


class SavedQueryCreate(BaseModel):
    """保存查询。"""
    query_name: str = Field(..., max_length=200)
    description: Optional[str] = None
    sql_text: str = Field(...)
    database: Optional[str] = None
    tags: Optional[str] = Field(None, description="逗号分隔标签")


class SavedQueryResponse(BaseModel):
    """保存的查询响应。"""
    id: str
    query_name: str
    description: Optional[str] = None
    sql_text: str
    database: Optional[str] = None
    tags: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class QueryHistoryResponse(BaseModel):
    """查询历史。"""
    id: str
    sql_text: str
    database: Optional[str] = None
    row_count: Optional[int] = None
    truncated: bool = False
    elapsed_ms: Optional[int] = None
    status: str
    error_message: Optional[str] = None
    executed_by: Optional[str] = None
    executed_at: datetime

    class Config:
        from_attributes = True


class DatabaseInfo(BaseModel):
    """Doris 数据库信息。"""
    name: str


class TableInfo(BaseModel):
    """Doris 表信息。"""
    name: str
    engine: Optional[str] = None
    rows: Optional[int] = None
    data_size: Optional[int] = None


class ColumnInfo(BaseModel):
    """Doris 列信息。"""
    field: str
    type: str
    null: Optional[str] = None
    key: Optional[str] = None
    default: Optional[str] = None
    extra: Optional[str] = None
