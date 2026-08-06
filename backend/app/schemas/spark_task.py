"""Spark task schemas."""
from typing import Optional
from pydantic import BaseModel, Field


class SparkTaskCreate(BaseModel):
    task_name: str = Field(..., max_length=200)
    task_code: str = Field(..., max_length=100)
    mode: str = Field("sql", pattern="^(sql|pyspark)$")
    file_path: str = Field(..., max_length=500)
    target_database: str = Field(..., max_length=100)
    target_table: str = Field(..., max_length=200)
    spark_config: dict = Field(default_factory=dict)
    variables: dict = Field(default_factory=dict)
    schedule_cron: Optional[str] = None
    description: Optional[str] = None


class SparkTaskUpdate(BaseModel):
    task_name: Optional[str] = None
    mode: Optional[str] = None
    file_path: Optional[str] = None
    target_database: Optional[str] = None
    target_table: Optional[str] = None
    spark_config: Optional[dict] = None
    variables: Optional[dict] = None
    schedule_cron: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None


class SparkTaskTrigger(BaseModel):
    run_immediately: bool = True
    conf: Optional[dict] = None
