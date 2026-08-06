"""DataX task + field mapping models."""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DataXTask(Base):
    __tablename__ = "datax_tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_name: Mapped[str] = mapped_column(String(200), nullable=False)
    task_code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    # source config
    source_datasource_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("data_sources.id"), nullable=False, index=True)
    source_table: Mapped[str] = mapped_column(String(200), nullable=False)
    source_schema: Mapped[str | None] = mapped_column(String(100))
    where_clause: Mapped[str | None] = mapped_column(Text)
    split_pk: Mapped[str | None] = mapped_column(String(100))

    # target config (Doris)
    target_database: Mapped[str] = mapped_column(String(100), nullable=False)
    target_table: Mapped[str] = mapped_column(String(200), nullable=False)
    target_type: Mapped[str] = mapped_column(String(20), nullable=False, default="doris")

    # DataX job JSON
    job_config: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # sync options
    sync_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="full")
    channel: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    error_limit_record: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_limit_pct: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False, default=0.02)

    # scheduling
    schedule_cron: Mapped[str | None] = mapped_column(String(100))
    dag_id: Mapped[str | None] = mapped_column(String(100), index=True)
    is_paused: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft", index=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # relationships
    field_mappings: Mapped[list["DataXFieldMapping"]] = relationship(
        back_populates="task", cascade="all, delete-orphan", lazy="selectin"
    )


class DataXFieldMapping(Base):
    __tablename__ = "datax_field_mappings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("datax_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    source_column: Mapped[str] = mapped_column(String(200), nullable=False)
    target_column: Mapped[str] = mapped_column(String(200), nullable=False)
    source_type: Mapped[str | None] = mapped_column(String(100))
    target_type: Mapped[str | None] = mapped_column(String(100))
    is_primary_key: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # relationships
    task: Mapped["DataXTask"] = relationship(back_populates="field_mappings")
