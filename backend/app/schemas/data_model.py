"""Data model schemas."""
from typing import Optional
from pydantic import BaseModel, Field


class DataModelFieldItem(BaseModel):
    field_name: str
    field_type: str
    field_comment: Optional[str] = None
    is_primary_key: bool = False
    is_partition: bool = False
    default_value: Optional[str] = None
    sort_order: int = 0


class DataModelCreate(BaseModel):
    model_name: str = Field(..., max_length=100)
    model_code: Optional[str] = Field(None, max_length=100, description="模型编码(留空自动生成)")
    layer: str = Field(..., pattern="^(ods|dwd|dws|ads)$")
    database: str = Field(..., max_length=50)
    table_name: str = Field(..., max_length=100)
    description: Optional[str] = None
    etl_sql: Optional[str] = None
    business_domain: Optional[str] = Field(None, max_length=50)
    data_domain: Optional[str] = Field(None, max_length=50)
    fields: list[DataModelFieldItem] = Field(default_factory=list)


class DataModelUpdate(BaseModel):
    model_name: Optional[str] = None
    description: Optional[str] = None
    etl_sql: Optional[str] = None
    business_domain: Optional[str] = None
    data_domain: Optional[str] = None
    status: Optional[str] = None
    fields: Optional[list[DataModelFieldItem]] = None


class DataModelVersionCreate(BaseModel):
    change_log: Optional[str] = None
