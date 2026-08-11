"""数据源接口: CRUD + 连接测试 + 表/字段查询。"""
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission, PaginationParams
from app.schemas.datasource import (
    DataSourceCreate, DataSourceUpdate, DataSourceResponse,
    ConnectionTestResponse,
)
from app.schemas.common import ResponseOK, PageResponse, PageResult
from app.services import datasource_service

router = APIRouter()


class DatasourceQueryRequest(BaseModel):
    """Read-only query against a configured data source."""
    sql: str = Field(..., description="SQL语句(仅支持SELECT/SHOW/DESC/WITH)")
    limit: int = Field(10000, ge=1, le=100000, description="最大返回行数")


@router.get("", response_model=PageResponse[DataSourceResponse], summary="数据源列表")
async def list_datasources(
    pagination: PaginationParams = Depends(),
    source_type: str | None = None,
    status: str | None = None,
    keyword: str | None = None,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    items, total = await datasource_service.list_datasources(
        db, pagination.page, pagination.page_size, source_type, status, keyword
    )
    return PageResponse(data=PageResult.create(items, total, pagination.page, pagination.page_size))


@router.post(
    "", response_model=ResponseOK[DataSourceResponse], summary="新增数据源",
    dependencies=[Depends(require_permission("datasource:create"))],
)
async def create_datasource(
    req: DataSourceCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    result = await datasource_service.create_datasource(db, req, user.id)
    return ResponseOK(data=result)


@router.get("/{datasource_id}", response_model=ResponseOK[DataSourceResponse], summary="数据源详情")
async def get_datasource(datasource_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await datasource_service.get_datasource(db, __import__("uuid").UUID(datasource_id))
    if not result:
        return ResponseOK(code=404, message="Data source not found")
    return ResponseOK(data=result)


@router.put(
    "/{datasource_id}", response_model=ResponseOK[DataSourceResponse], summary="更新数据源",
    dependencies=[Depends(require_permission("datasource:update"))],
)
async def update_datasource(
    datasource_id: str,
    req: DataSourceUpdate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    result = await datasource_service.update_datasource(
        db, __import__("uuid").UUID(datasource_id), req
    )
    if not result:
        return ResponseOK(code=404, message="Data source not found")
    return ResponseOK(data=result)


@router.delete(
    "/{datasource_id}", response_model=ResponseOK, summary="删除数据源",
    dependencies=[Depends(require_permission("datasource:delete"))],
)
async def delete_datasource(datasource_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    ok = await datasource_service.delete_datasource(db, __import__("uuid").UUID(datasource_id))
    if not ok:
        return ResponseOK(code=404, message="Data source not found")
    return ResponseOK()


@router.post(
    "/{datasource_id}/test", response_model=ResponseOK[ConnectionTestResponse], summary="连接测试",
    dependencies=[Depends(require_permission("datasource:update"))],
)
async def test_connection(datasource_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await datasource_service.test_connection(db, __import__("uuid").UUID(datasource_id))
    return ResponseOK(data=result)


@router.post(
    "/{datasource_id}/query", response_model=ResponseOK[dict], summary="执行数据源查询",
    dependencies=[Depends(require_permission("doris:query:execute"))],
)
async def query_datasource(
    datasource_id: str,
    req: DatasourceQueryRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    result = await datasource_service.execute_query(
        db, uuid.UUID(datasource_id), req.sql, req.limit
    )
    return ResponseOK(data=result)


@router.get("/{datasource_id}/tables", response_model=ResponseOK[list[dict]], summary="获取表列表")
async def list_tables(
    datasource_id: str,
    schema: str | None = None,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    result = await datasource_service.list_tables(db, __import__("uuid").UUID(datasource_id), schema)
    return ResponseOK(data=result)


@router.get("/{datasource_id}/databases", response_model=ResponseOK[list[str]], summary="列出服务器上所有数据库")
async def list_databases(
    datasource_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    result = await datasource_service.list_databases(db, __import__("uuid").UUID(datasource_id))
    return ResponseOK(data=result)


@router.get("/{datasource_id}/tables/{table_name}/columns", response_model=ResponseOK[list[dict]], summary="获取表字段")
async def get_table_columns(
    datasource_id: str,
    table_name: str,
    schema: str | None = None,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    result = await datasource_service.get_table_columns(
        db, __import__("uuid").UUID(datasource_id), table_name, schema
    )
    return ResponseOK(data=result)
