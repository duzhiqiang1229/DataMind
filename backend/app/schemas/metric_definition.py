"""Metric definition schemas."""
from typing import Literal, Optional
from pydantic import BaseModel, Field


class MetricDefinitionCreate(BaseModel):
    metric_code: Optional[str] = Field(None, max_length=100, description="指标编码(留空系统自动生成)")
    metric_name: str = Field(..., max_length=100)
    metric_type: Literal["atomic", "derived", "composite"] = Field("atomic", description="指标类型")
    cube_name: Optional[str] = Field(None, max_length=100)
    cube_measure: Optional[str] = Field(None, max_length=200)
    category_id: Optional[str] = None
    dimensions: list[str] = Field(default_factory=list)
    default_time_dimension: Optional[str] = Field(None, max_length=200, description="默认时间维度")
    calculation: Optional[str] = None
    business_domain: Optional[str] = Field(None, max_length=50)
    unit: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=500)
    status: Optional[str] = Field("draft", description="状态: draft/published")


class MetricDefinitionUpdate(BaseModel):
    metric_name: Optional[str] = None
    metric_type: Optional[Literal["atomic", "derived", "composite"]] = None
    cube_name: Optional[str] = None
    cube_measure: Optional[str] = None
    category_id: Optional[str] = None
    dimensions: Optional[list[str]] = None
    default_time_dimension: Optional[str] = None
    calculation: Optional[str] = None
    business_domain: Optional[str] = None
    unit: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
