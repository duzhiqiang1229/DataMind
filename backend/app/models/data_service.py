"""Data service model."""
import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class DataServiceApi(Base):
    __tablename__ = "data_service_apis"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    api_name: Mapped[str] = mapped_column(String(100), nullable=False)
    api_path: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False, default="GET")
    description: Mapped[str | None] = mapped_column(Text)
    sql_template: Mapped[str] = mapped_column(Text, nullable=False)
    parameters: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # parameters format: [{"name": "start_date", "type": "string", "required": true}, ...]

    database: Mapped[str] = mapped_column(String(100), nullable=False, default="default")
    cache_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    cache_ttl: Mapped[int] = mapped_column(Integer, default=300)  # seconds

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", index=True)
    call_count: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
