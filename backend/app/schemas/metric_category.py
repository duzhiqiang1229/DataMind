"""Metric category schemas."""
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class MetricCategoryCreate(BaseModel):
    """Create a metric category."""
    category_name: str = Field(..., max_length=100, description="分类名称")
    category_code: str = Field(..., max_length=100, description="分类编码")
    description: Optional[str] = Field(None, max_length=500, description="描述")
    sort_order: int = Field(default=0, description="排序值，越小越靠前")


class MetricCategoryUpdate(BaseModel):
    """Update a metric category."""
    category_name: Optional[str] = Field(None, max_length=100)
    category_code: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    sort_order: Optional[int] = None


class MetricCategoryResponse(BaseModel):
    """Metric category response."""
    id: str
    category_name: str
    category_code: str
    description: Optional[str] = None
    sort_order: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MetricMappingCreate(BaseModel):
    """Assign a Cube metric to a category."""
    category_id: uuid.UUID = Field(..., description="分类ID")
    metric_name: str = Field(..., max_length=200, description="Cube指标名, 如 Orders.count")
    metric_label: Optional[str] = Field(None, max_length=200, description="指标显示名")


class MetricMappingResponse(BaseModel):
    """Metric mapping response."""
    id: str
    category_id: str
    metric_name: str
    metric_label: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
