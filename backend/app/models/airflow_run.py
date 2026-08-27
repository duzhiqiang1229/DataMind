"""Airflow DAG run snapshot model (synced from Airflow for unified monitoring)."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AirflowDagRun(Base):
    """Snapshot of an Airflow DAG run, synced periodically."""
    __tablename__ = "airflow_dag_runs"
    __table_args__ = (UniqueConstraint("dag_id", "dag_run_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dag_id: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    dag_run_id: Mapped[str] = mapped_column(String(250), nullable=False)
    run_type: Mapped[str | None] = mapped_column(String(20))
    state: Mapped[str | None] = mapped_column(String(20), index=True)
    execution_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    task_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success_task_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_task_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    input_asset_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_asset_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lineage_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    lineage_collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class AirflowTaskRun(Base):
    """Task-level execution record received from a DataMind lineage callback."""
    __tablename__ = "airflow_task_runs"
    __table_args__ = (UniqueConstraint("dag_id", "dag_run_id", "task_id", "try_number"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dag_run_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("airflow_dag_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    dag_id: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    dag_run_id: Mapped[str] = mapped_column(String(250), nullable=False, index=True)
    task_id: Mapped[str] = mapped_column(String(250), nullable=False)
    try_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    operator_type: Mapped[str | None] = mapped_column(String(100))
    state: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    executed_sql: Mapped[str | None] = mapped_column(Text)
    sql_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    affected_rows: Mapped[int | None] = mapped_column(Integer)
    input_tables: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    output_tables: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    openlineage_inputs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    openlineage_outputs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    openlineage_run_id: Mapped[str | None] = mapped_column(String(100), index=True)
    openlineage_job_namespace: Mapped[str | None] = mapped_column(String(500))
    openlineage_job_name: Mapped[str | None] = mapped_column(String(500))
    error_message: Mapped[str | None] = mapped_column(Text)
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
