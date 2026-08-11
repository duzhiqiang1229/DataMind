"""OpenMetadata 治理接口：资产目录、治理、质量与血缘。"""
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.common import ResponseOK
from app.services import openmetadata_service

router = APIRouter()


def unavailable(error: RuntimeError, data=None):
    return ResponseOK(code=503, message=str(error), data=data)


@router.get("/databases", response_model=ResponseOK[list], summary="数据库列表")
async def list_databases(
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        result = await openmetadata_service.list_databases(db, limit)
        return ResponseOK(data=result)
    except RuntimeError as e:
        return unavailable(e, [])


@router.get("/tables", response_model=ResponseOK[list], summary="表列表")
async def list_tables(
    database: str | None = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        result = await openmetadata_service.list_tables(db, database, limit)
        return ResponseOK(data=result)
    except RuntimeError as e:
        return unavailable(e, [])


@router.get("/tables/{table_fqn}", response_model=ResponseOK[dict], summary="表详情")
async def get_table(
    table_fqn: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        result = await openmetadata_service.get_table(db, table_fqn)
        return ResponseOK(data=result)
    except RuntimeError as e:
        return unavailable(e)


@router.get("/lineage", response_model=ResponseOK[dict], summary="血缘关系")
async def get_lineage(
    fqn: str,
    entity_type: str = "table",
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        result = await openmetadata_service.get_lineage(db, fqn, entity_type)
        return ResponseOK(data=result)
    except RuntimeError as e:
        return unavailable(e)


@router.get("/search", response_model=ResponseOK[list], summary="搜索资产")
async def search(
    q: str,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        result = await openmetadata_service.search(db, q, limit)
        return ResponseOK(data=result)
    except RuntimeError as e:
        return unavailable(e, [])


@router.get("/assets", response_model=ResponseOK[dict], summary="统一资产搜索")
async def assets(
    q: str = "*",
    entity_type: Literal["all", "table", "dashboard", "pipeline", "topic", "mlmodel", "container"] = "all",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        result = await openmetadata_service.search_assets(db, q, entity_type, page, page_size)
        return ResponseOK(data=result)
    except RuntimeError as e:
        return unavailable(e, {"items": [], "total": 0, "page": page, "page_size": page_size})


@router.get("/summary", response_model=ResponseOK[dict], summary="资产治理概览")
async def summary(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    try:
        return ResponseOK(data=await openmetadata_service.summary(db))
    except RuntimeError as e:
        return unavailable(e, {})


@router.get("/governance", response_model=ResponseOK[dict], summary="治理对象")
async def governance(
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        return ResponseOK(data=await openmetadata_service.governance(db, limit))
    except RuntimeError as e:
        return unavailable(e, {})


@router.get("/quality", response_model=ResponseOK[dict], summary="数据质量检查")
async def quality(
    table_fqn: str | None = None,
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        return ResponseOK(data=await openmetadata_service.quality(db, table_fqn, limit))
    except RuntimeError as e:
        return unavailable(e, {"items": [], "total": 0})


@router.get("/health", response_model=ResponseOK[dict], summary="健康检查")
async def health_check(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    healthy = await openmetadata_service.health_check(db)
    return ResponseOK(data={"healthy": healthy})
