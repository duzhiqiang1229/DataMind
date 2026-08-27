"""Authenticated OpenLineage HTTP transport endpoint."""
import secrets
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.services.openlineage_service import ingest_openlineage_event


router = APIRouter()


def verify_openlineage_token(
    authorization: str = Header(default=""),
    x_lineage_token: str = Header(default="", alias="X-Lineage-Token"),
) -> None:
    expected = settings.LINEAGE_EVENT_TOKEN or settings.EXECUTOR_TOKEN
    bearer = authorization[7:].strip() if authorization.lower().startswith("bearer ") else ""
    supplied = bearer or x_lineage_token
    if not expected or not supplied or not secrets.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Invalid OpenLineage event token")


@router.get("/health", summary="检查 OpenLineage 事件通道")
async def openlineage_health(_: None = Depends(verify_openlineage_token)):
    return {"status": "ok", "receiver": "datamind-openlineage"}


@router.post("/events", summary="接收 OpenLineage RunEvent")
async def receive_openlineage_event(
    body: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_openlineage_token),
):
    return await ingest_openlineage_event(db, body)
