"""DAG workflow definition models: a DAG arranges multiple tasks in a DAG."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DagDefinition(Base):
    """A scheduled workflow that runs multiple tasks in dependency order."""
    __tablename__ = "dag_definitions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dag_id: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    dag_name: Mapped[str] = mapped_column(String(100), nullable=False)
    schedule: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    nodes: Mapped[list["DagNode"]] = relationship(
        back_populates="dag", cascade="all, delete-orphan", lazy="selectin",
        order_by="DagNode.sort_order",
    )


class DagNode(Base):
    """A node inside a DAG: one DataX or Spark task, with upstream dependencies."""
    __tablename__ = "dag_nodes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dag_definitions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    node_name: Mapped[str] = mapped_column(String(100), nullable=False)
    task_type: Mapped[str] = mapped_column(String(20), nullable=False)  # datax / spark
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    depends_on: Mapped[list | None] = mapped_column(JSONB)  # list of upstream node_names
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    dag: Mapped["DagDefinition"] = relationship(back_populates="nodes")
