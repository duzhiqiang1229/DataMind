"""Spark task model."""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SparkTask(Base):
    __tablename__ = "spark_tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_name: Mapped[str] = mapped_column(String(200), nullable=False)
    task_code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    # spark mode: sql or pyspark
    mode: Mapped[str] = mapped_column(String(20), nullable=False, default="sql")  # sql / pyspark

    # SQL mode: sql_file_path; PySpark mode: script_file_path
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    target_database: Mapped[str] = mapped_column(String(100), nullable=False)
    target_table: Mapped[str] = mapped_column(String(200), nullable=False)

    # Spark submission config (JSONB: master, deploy_mode, executor_memory, etc.)
    spark_config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # variables for SQL substitution or script args
    variables: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # scheduling
    schedule_cron: Mapped[str | None] = mapped_column(String(100))
    dag_id: Mapped[str | None] = mapped_column(String(100), index=True)
    is_paused: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft", index=True)
    description: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
