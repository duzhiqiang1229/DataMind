"""DAG workflow schemas."""
from typing import Optional
from pydantic import BaseModel, Field


class DagNodeItem(BaseModel):
    node_name: str = Field(..., max_length=100)
    task_type: str = Field(..., pattern="^(datax|spark)$")
    task_id: str
    depends_on: list[str] = Field(default_factory=list)


class DagDefinitionCreate(BaseModel):
    dag_name: str = Field(..., max_length=100)
    schedule: str = Field(..., max_length=100)
    description: Optional[str] = None
    nodes: list[DagNodeItem] = Field(default_factory=list)


class DagDefinitionUpdate(BaseModel):
    dag_name: Optional[str] = None
    schedule: Optional[str] = None
    description: Optional[str] = None
    nodes: Optional[list[DagNodeItem]] = None
    status: Optional[str] = None
