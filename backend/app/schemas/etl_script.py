"""ETL script schemas."""
from typing import Optional
from pydantic import BaseModel, Field


class EtlScriptCreate(BaseModel):
    script_name: str = Field(..., max_length=100)
    script_code: Optional[str] = Field(None, max_length=100, description="脚本编码(留空自动生成)")
    language: str = Field("sql", pattern="^sql$")
    content: str
    description: Optional[str] = None


class EtlScriptUpdate(BaseModel):
    script_name: Optional[str] = None
    language: Optional[str] = Field(None, pattern="^sql$")
    content: Optional[str] = None
    description: Optional[str] = None


class EtlScriptExecute(BaseModel):
    """Execution params."""
    datasource_id: Optional[str] = None  # for SQL execution
    database: Optional[str] = None       # for SQL execution
    limit: int = Field(10000, ge=1, le=100000)
