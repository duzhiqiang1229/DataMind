"""数据服务接口: CRUD + 执行。"""
from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, PaginationParams
from app.schemas.data_service import (
    DataServiceCreate, DataServiceUpdate, DataServiceResponse,
    ExecuteRequest, ExecuteResultResponse,
)
from app.schemas.common import ResponseOK, PageResponse, PageResult
from app.services import data_service

router = APIRouter()


@router.get("", response_model=PageResponse[DataServiceResponse], summary="数据服务列表")
async def list_apis(
    pagination: PaginationParams = Depends(),
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    items, total = await data_service.list_apis(db, pagination.page, pagination.page_size, status)
    return PageResponse(data=PageResult.create(items, total, pagination.page, pagination.page_size))


@router.post("", response_model=ResponseOK[DataServiceResponse], summary="新增数据服务")
async def create_api(
    req: DataServiceCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    result = await data_service.create_api(db, req, user.id)
    return ResponseOK(data=result)


@router.get("/{api_id}", response_model=ResponseOK[DataServiceResponse], summary="数据服务详情")
async def get_api(api_id: UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await data_service.get_api(db, api_id)
    if not result:
        return ResponseOK(code=404, message="API not found")
    return ResponseOK(data=result)


@router.put("/{api_id}", response_model=ResponseOK[DataServiceResponse], summary="更新数据服务")
async def update_api(
    api_id: UUID,
    req: DataServiceUpdate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    result = await data_service.update_api(db, api_id, req)
    if not result:
        return ResponseOK(code=404, message="API not found")
    return ResponseOK(data=result)


@router.delete("/{api_id}", response_model=ResponseOK, summary="删除数据服务")
async def delete_api(api_id: UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    ok = await data_service.delete_api(db, api_id)
    if not ok:
        return ResponseOK(code=404, message="API not found")
    return ResponseOK()


@router.post("/{api_id}/execute", response_model=ResponseOK[ExecuteResultResponse], summary="执行数据服务")
async def execute_api(
    api_id: UUID,
    req: ExecuteRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        result = await data_service.execute_api(db, api_id, req.params)
        return ResponseOK(data=result)
    except ValueError as e:
        return ResponseOK(code=400, message=str(e))
    except Exception as e:
        return ResponseOK(code=500, message=str(e))
