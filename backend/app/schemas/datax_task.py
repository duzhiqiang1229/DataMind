"""DataX 同步任务 Schema。"""
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


# ============================================================
# 字段映射
# ============================================================
class FieldMappingItem(BaseModel):
    """单个字段映射。"""
    source_column: str = Field(..., description="源表字段名")
    target_column: str = Field(..., description="目标表字段名")
    source_type: Optional[str] = Field(None, description="源字段类型")
    target_type: Optional[str] = Field(None, description="目标字段类型")
    is_primary_key: bool = False
    sort_order: int = 0


# ============================================================
# DataX 任务
# ============================================================
class DataXTaskCreate(BaseModel):
    """创建 DataX 同步任务。"""
    task_name: str = Field(..., max_length=200, description="任务名称")
    task_code: Optional[str] = Field(None, max_length=100, description="任务编码(留空自动生成)")

    # 源端
    source_datasource_id: str = Field(..., description="源数据源ID")
    source_table: str = Field(..., description="源表名")
    source_schema: Optional[str] = None
    where_clause: Optional[str] = Field(None, description="增量同步条件")
    split_pk: Optional[str] = Field(None, description="分片字段")

    # 目标
    target_database: str = Field(..., description="目标Doris库")
    target_table: str = Field(..., description="目标Doris表")

    # 字段映射
    field_mappings: list[FieldMappingItem] = Field(..., min_length=1, description="字段映射列表")

    # 同步选项
    sync_mode: str = Field("full", description="同步模式: full/incremental")
    channel: int = Field(3, ge=1, le=10, description="并发通道数")
    error_limit_record: int = Field(0, description="错误记录限制")
    error_limit_pct: float = Field(0.02, description="错误百分比限制")

    # 调度
    schedule_cron: Optional[str] = Field(None, description="调度Cron表达式")


class DataXTaskUpdate(BaseModel):
    """更新 DataX 任务。"""
    task_name: Optional[str] = None
    source_table: Optional[str] = None
    where_clause: Optional[str] = None
    split_pk: Optional[str] = None
    target_database: Optional[str] = None
    target_table: Optional[str] = None
    field_mappings: Optional[list[FieldMappingItem]] = None
    sync_mode: Optional[str] = None
    channel: Optional[int] = None
    error_limit_record: Optional[int] = None
    error_limit_pct: Optional[float] = None
    schedule_cron: Optional[str] = None
    status: Optional[str] = None


class DataXTaskResponse(BaseModel):
    """DataX 任务详情。"""
    id: str
    task_name: str
    task_code: str
    source_datasource_id: str
    source_table: str
    source_schema: Optional[str] = None
    where_clause: Optional[str] = None
    split_pk: Optional[str] = None
    target_database: str
    target_table: str
    sync_mode: str
    channel: int
    error_limit_record: int
    error_limit_pct: float
    schedule_cron: Optional[str] = None
    dag_id: Optional[str] = None
    is_paused: bool
    status: str
    job_config: dict  # 生成的 DataX job JSON
    field_mappings: list[FieldMappingItem] = []
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DataXTaskTrigger(BaseModel):
    """触发 DataX 任务执行。"""
    run_immediately: bool = Field(True, description="是否立即执行")
    conf: Optional[dict] = Field(None, description="额外DAG参数")


# ============================================================
# 任务执行实例
# ============================================================
class TaskInstanceResponse(BaseModel):
    """任务执行实例。"""
    id: str
    task_type: str         # datax/spark
    task_id: str
    dag_id: str
    dag_run_id: str
    status: str            # queued/running/success/failed
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    rows_read: Optional[int] = None
    rows_written: Optional[int] = None
    triggered_by: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaskLogResponse(BaseModel):
    """任务执行日志。"""
    task_instance_id: str
    task_id: str          # Airflow task_id within DAG
    log_content: str
    try_number: int = 1
