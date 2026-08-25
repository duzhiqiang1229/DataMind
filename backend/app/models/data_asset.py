"""Self-hosted data catalog, lineage and quality models."""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AssetObject(Base):
    __tablename__ = "asset_objects"
    __table_args__ = (UniqueConstraint("fqn", name="uq_asset_objects_fqn"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    datasource_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    asset_type: Mapped[str] = mapped_column(String(30), nullable=False, default="table", index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    fqn: Mapped[str] = mapped_column(String(600), nullable=False, unique=True, index=True)
    database_name: Mapped[str | None] = mapped_column(String(150), index=True)
    schema_name: Mapped[str | None] = mapped_column(String(150), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", index=True)
    properties: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    last_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    columns: Mapped[list["AssetColumn"]] = relationship(
        back_populates="asset", cascade="all, delete-orphan", lazy="selectin", order_by="AssetColumn.ordinal_position"
    )


class AssetColumn(Base):
    __tablename__ = "asset_columns"
    __table_args__ = (UniqueConstraint("asset_id", "name", name="uq_asset_columns_asset_name"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("asset_objects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    data_type: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    nullable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    primary_key: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    default_value: Mapped[str | None] = mapped_column(Text)
    ordinal_position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    asset: Mapped["AssetObject"] = relationship(back_populates="columns")


class AssetLineageEdge(Base):
    __tablename__ = "asset_lineage_edges"
    __table_args__ = (
        UniqueConstraint("source_asset_id", "target_asset_id", "source_type", name="uq_asset_lineage_edge"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("asset_objects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("asset_objects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    lineage_type: Mapped[str] = mapped_column(String(20), nullable=False, default="table")
    source_type: Mapped[str] = mapped_column(String(30), nullable=False, default="model")
    expression: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    success_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_dag_run_id: Mapped[str | None] = mapped_column(String(250))
    last_task_id: Mapped[str | None] = mapped_column(String(250))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class LineageRunEvent(Base):
    """One successful runtime observation of an upstream/downstream pair."""
    __tablename__ = "lineage_run_events"
    __table_args__ = (
        UniqueConstraint("task_run_id", "source_asset_id", "target_asset_id", name="uq_lineage_run_event_pair"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("airflow_task_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("asset_objects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("asset_objects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    dag_id: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    dag_run_id: Mapped[str] = mapped_column(String(250), nullable=False, index=True)
    task_id: Mapped[str] = mapped_column(String(250), nullable=False)
    sql_hash: Mapped[str | None] = mapped_column(String(64))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class QualityRule(Base):
    __tablename__ = "quality_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("asset_objects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rule_name: Mapped[str] = mapped_column(String(200), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    column_name: Mapped[str | None] = mapped_column(String(200))
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class QualityRuleRun(Base):
    __tablename__ = "quality_rule_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quality_rules.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    total_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pass_rate: Mapped[float] = mapped_column(Numeric(7, 4), nullable=False, default=0)
    message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
