"""Authenticated callback endpoint for Airflow runtime lineage events."""
import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.schemas.common import ResponseOK
from app.services import runtime_lineage_service


router = APIRouter()


class RuntimeLineageEvent(BaseModel):
    dag_id: str = Field(min_length=1, max_length=200)
    dag_run_id: str = Field(min_length=1, max_length=250)
    task_id: str = Field(min_length=1, max_length=250)
    try_number: int = Field(default=1, ge=1)
    state: str = Field(pattern="^(running|success|failed)$")
    dag_state: str | None = None
    run_type: str | None = None
    operator_type: str | None = None
    sql: str | None = None
    datasource_name: str | None = None
    default_database: str | None = None
    input_tables: list[str] = Field(default_factory=list)
    output_tables: list[str] = Field(default_factory=list)
    input_datasets: list[dict] = Field(default_factory=list)
    output_datasets: list[dict] = Field(default_factory=list)
    affected_rows: int | None = None
    error_message: str | None = None
    execution_date: datetime | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None


def verify_lineage_token(x_lineage_token: str = Header(default="", alias="X-Lineage-Token")) -> None:
    expected = settings.LINEAGE_EVENT_TOKEN or settings.EXECUTOR_TOKEN
    if not expected or not secrets.compare_digest(x_lineage_token, expected):
        raise HTTPException(status_code=401, detail="Invalid lineage event token")


@router.post("/events", response_model=ResponseOK[dict], summary="接收 Airflow 运行血缘事件")
async def receive_event(
    body: RuntimeLineageEvent,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_lineage_token),
):
    try:
        result = await runtime_lineage_service.ingest_event(db, body.model_dump())
        return ResponseOK(data=result)
    except ValueError as exc:
        return ResponseOK(code=400, message=str(exc))
