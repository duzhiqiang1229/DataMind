"""Data model + fields + versions models."""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DataModel(Base):
    __tablename__ = "data_models"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    layer: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # ods/dwd/dws/ads
    database: Mapped[str] = mapped_column(String(50), nullable=False)
    table_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft", index=True)
    current_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # relationships
    fields: Mapped[list["DataModelField"]] = relationship(
        back_populates="model", cascade="all, delete-orphan", lazy="selectin",
        order_by="DataModelField.sort_order"
    )
    versions: Mapped[list["DataModelVersion"]] = relationship(
        back_populates="model", cascade="all, delete-orphan", lazy="selectin",
        order_by="DataModelVersion.version.desc()"
    )


class DataModelField(Base):
    __tablename__ = "data_model_fields"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("data_models.id", ondelete="CASCADE"), nullable=False, index=True)
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    field_type: Mapped[str] = mapped_column(String(50), nullable=False)
    field_comment: Mapped[str | None] = mapped_column(String(200))
    is_primary_key: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_partition: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    default_value: Mapped[str | None] = mapped_column(String(200))
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # relationships
    model: Mapped["DataModel"] = relationship(back_populates="fields")


class DataModelVersion(Base):
    __tablename__ = "data_model_versions"
    __table_args__ = (UniqueConstraint("model_id", "version"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("data_models.id", ondelete="CASCADE"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    table_ddl: Mapped[str | None] = mapped_column(Text)
    field_snapshot: Mapped[dict | None] = mapped_column(JSONB)
    change_log: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # relationships
    model: Mapped["DataModel"] = relationship(back_populates="versions")
