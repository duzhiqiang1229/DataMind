"""表负责人管理接口."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, PaginationParams
from app.schemas.common import ResponseOK, PageResponse, PageResult
from app.schemas.table_owner import TableOwnerCreate, TableOwnerResponse
from app.services import table_owner_service

router = APIRouter()


@router.get("", response_model=PageResponse[TableOwnerResponse], summary="表负责人列表")
async def list_owners(
    pagination: PaginationParams = Depends(),
    database_name: str | None = None,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    items, total = await table_owner_service.list_owners(
        db, pagination.page, pagination.page_size, database_name
    )
    return PageResponse(data=PageResult.create(items, total, pagination.page, pagination.page_size))


@router.post("", response_model=ResponseOK[TableOwnerResponse], summary="设置/更新表负责人")
async def set_owner(
    req: TableOwnerCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    result = await table_owner_service.set_owner(db, req)
    return ResponseOK(data=result)


@router.get("/{database}/{table}", response_model=ResponseOK[TableOwnerResponse], summary="查询表负责人")
async def get_owner(
    database: str,
    table: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    result = await table_owner_service.get_owner(db, database, table)
    if not result:
        return ResponseOK(code=404, message="Owner not found")
    return ResponseOK(data=result)


@router.delete("/{database}/{table}", response_model=ResponseOK, summary="删除表负责人")
async def delete_owner(
    database: str,
    table: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    ok = await table_owner_service.delete_owner(db, database, table)
    if not ok:
        return ResponseOK(code=404, message="Owner not found")
    return ResponseOK()
