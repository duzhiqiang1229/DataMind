"""Doris 查询接口: SQL执行 + 库表浏览 + 保存查询 + 历史。"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, PaginationParams
from app.schemas.doris_query import (
    QueryRequest, QueryResultResponse,
    SavedQueryCreate, SavedQueryResponse,
    QueryHistoryResponse,
    DatabaseInfo, TableInfo, ColumnInfo,
)
from app.schemas.common import ResponseOK, PageResponse, PageResult
from app.services import doris_query_service

router = APIRouter()


# ============================================================
# SQL 查询
# ============================================================

@router.post("/execute", response_model=ResponseOK[QueryResultResponse], summary="执行SQL查询")
async def execute_query(
    req: QueryRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        result = await doris_query_service.execute_query(
            db, req.sql, req.database, req.limit, user.id
        )
        return ResponseOK(data=result)
    except ValueError as e:
        return ResponseOK(code=400, message=str(e))
    except Exception as e:
        return ResponseOK(code=500, message=str(e))


# ============================================================
# 库表浏览
# ============================================================

@router.get("/databases", response_model=ResponseOK[list[DatabaseInfo]], summary="数据库列表")
async def list_databases(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await doris_query_service.list_databases(db)
    return ResponseOK(data=result)


@router.get("/databases/{database}/tables", response_model=ResponseOK[list[TableInfo]], summary="表列表")
async def list_tables(
    database: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    result = await doris_query_service.list_tables(db, database)
    return ResponseOK(data=result)


@router.get("/databases/{database}/tables/{table}/columns", response_model=ResponseOK[list[ColumnInfo]], summary="表结构")
async def get_table_schema(
    database: str,
    table: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    result = await doris_query_service.get_table_schema(db, database, table)
    return ResponseOK(data=result)


# ============================================================
# 保存的查询
# ============================================================

@router.get("/saved", response_model=PageResponse[SavedQueryResponse], summary="保存的查询列表")
async def list_saved_queries(
    pagination: PaginationParams = Depends(),
    tags: str | None = None,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    items, total = await doris_query_service.list_saved_queries(
        db, pagination.page, pagination.page_size, tags
    )
    return PageResponse(data=PageResult.create(items, total, pagination.page, pagination.page_size))


@router.post("/saved", response_model=ResponseOK[SavedQueryResponse], summary="保存查询")
async def save_query(
    req: SavedQueryCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    result = await doris_query_service.save_query(db, req, user.id)
    return ResponseOK(data=result)


@router.delete("/saved/{query_id}", response_model=ResponseOK, summary="删除保存的查询")
async def delete_saved_query(query_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    import uuid
    ok = await doris_query_service.delete_saved_query(db, uuid.UUID(query_id))
    if not ok:
        return ResponseOK(code=404, message="Query not found")
    return ResponseOK()


# ============================================================
# 查询历史
# ============================================================

@router.get("/history", response_model=PageResponse[QueryHistoryResponse], summary="查询历史")
async def list_query_history(
    pagination: PaginationParams = Depends(),
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    items, total = await doris_query_service.list_history(
        db, pagination.page, pagination.page_size, status
    )
    return PageResponse(data=PageResult.create(items, total, pagination.page, pagination.page_size))


@router.get("/history/{history_id}", response_model=ResponseOK[QueryHistoryResponse], summary="历史详情")
async def get_query_history(history_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    import uuid
    result = await doris_query_service.get_history(db, uuid.UUID(history_id))
    if not result:
        return ResponseOK(code=404, message="History not found")
    return ResponseOK(data=result)


# ============================================================
# 存储监控
# ============================================================

@router.get("/storage", response_model=ResponseOK[dict], summary="存储概览")
async def get_storage_overview(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """数据库级存储概览: 每库表数、总行数、总大小。"""
    try:
        result = await doris_query_service.get_storage_overview(db)
        return ResponseOK(data=result)
    except Exception as e:
        return ResponseOK(code=500, message=str(e))


@router.get("/databases/{database}/tables/{table}/stats", response_model=ResponseOK[dict], summary="表统计信息")
async def get_table_stats(
    database: str,
    table: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """单表详细统计: 引擎、行数、大小、列数、分区信息。"""
    try:
        result = await doris_query_service.get_table_stats(db, database, table)
        return ResponseOK(data=result)
    except Exception as e:
        return ResponseOK(code=500, message=str(e))


@router.get("/databases/{database}/tables/{table}/partitions", response_model=ResponseOK[list[dict]], summary="分区详情")
async def get_table_partitions(
    database: str,
    table: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """表分区详情: 分区名、行数、数据大小等。"""
    try:
        result = await doris_query_service.get_table_partitions(db, database, table)
        return ResponseOK(data=result)
    except Exception as e:
        return ResponseOK(code=500, message=str(e))
