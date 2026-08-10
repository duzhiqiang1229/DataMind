"""Table owner schemas."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class TableOwnerCreate(BaseModel):
    """Create/upsert a table owner."""
    database_name: str = Field(..., max_length=100, description="数据库名")
    table_name: str = Field(..., max_length=200, description="表名")
    owner_name: str = Field(..., max_length=100, description="负责人姓名")
    owner_type: str = Field("person", max_length=20, description="负责人类型: person/team")
    contact: Optional[str] = Field(None, max_length=200, description="联系方式(邮箱或电话)")


class TableOwnerUpdate(BaseModel):
    """Update a table owner."""
    owner_name: Optional[str] = Field(None, max_length=100)
    owner_type: Optional[str] = Field(None, max_length=20)
    contact: Optional[str] = Field(None, max_length=200)


class TableOwnerResponse(BaseModel):
    """Table owner response."""
    id: str
    database_name: str
    table_name: str
    owner_name: str
    owner_type: str
    contact: Optional[str] = None
    updated_at: datetime

    class Config:
        from_attributes = True
