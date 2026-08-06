"""OpenMetadata 治理接口: 数据目录 + 血缘 + 搜索。"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.common import ResponseOK
from app.services import openmetadata_service

router = APIRouter()


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
        return ResponseOK(code=503, message=str(e), data=[])


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
        return ResponseOK(code=503, message=str(e), data=[])


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
        return ResponseOK(code=503, message=str(e))


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
        return ResponseOK(code=503, message=str(e))


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
        return ResponseOK(code=503, message=str(e), data=[])


@router.get("/health", response_model=ResponseOK[dict], summary="健康检查")
async def health_check(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    healthy = await openmetadata_service.health_check(db)
    return ResponseOK(data={"healthy": healthy})
