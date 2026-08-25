"""Metric category model."""
import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class MetricCategory(Base):
    __tablename__ = "metric_categories"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_name: Mapped[str] = mapped_column(String(100), nullable=False)
    category_code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    sort_order: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

class MetricMapping(Base):
    """Maps Cube metric names to categories."""
    __tablename__ = "metric_mappings"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("metric_categories.id", ondelete="CASCADE"), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(200), nullable=False)  # Cube metric name like "Orders.count"
    metric_label: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class MetricDefinition(Base):
    """指标定义：登记/管理企业统一指标，关联 Cube 度量与维度。"""
    __tablename__ = "metric_definitions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    metric_code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_type: Mapped[str] = mapped_column(String(20), nullable=False, default="atomic", index=True)
    cube_name: Mapped[str | None] = mapped_column(String(100))
    cube_measure: Mapped[str | None] = mapped_column(String(200))
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("metric_categories.id", ondelete="SET NULL")
    )
    dimensions: Mapped[list | None] = mapped_column(JSONB)  # Cube dimension names
    default_time_dimension: Mapped[str | None] = mapped_column(String(200))
    calculation: Mapped[str | None] = mapped_column(Text)  # 计算模型/口径说明
    business_domain: Mapped[str | None] = mapped_column(String(50))
    unit: Mapped[str | None] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
