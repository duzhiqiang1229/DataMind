"""Publish schemas."""
from typing import Optional
from pydantic import BaseModel, Field


class PublishTaskCreate(BaseModel):
    publish_name: str = Field(..., max_length=100)
    publish_type: str = Field("model", pattern="^model$")
    source_ids: list[str] = Field(default_factory=list)
    target_environment: str = Field("production", max_length=20)
    description: Optional[str] = None
