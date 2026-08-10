"""Data source permission schemas."""
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class DatasourcePermissionCreate(BaseModel):
    """Assign a permission to a role for a datasource."""
    datasource_id: uuid.UUID = Field(..., description="数据源ID")
    role_id: uuid.UUID = Field(..., description="角色ID")
    permission: str = Field("read", max_length=20, description="权限: read/write/admin")


class DatasourcePermissionUpdate(BaseModel):
    """Update a permission level."""
    permission: str = Field(..., max_length=20, description="权限: read/write/admin")


class DatasourcePermissionResponse(BaseModel):
    """Data source permission response."""
    id: str
    datasource_id: str
    role_id: str
    permission: str
    created_at: datetime

    class Config:
        from_attributes = True
