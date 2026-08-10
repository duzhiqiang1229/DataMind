"""Airflow DAG run snapshot model (synced from Airflow for unified monitoring)."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, UniqueConstraint, func
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
