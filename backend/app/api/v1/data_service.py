"""数据服务接口: CRUD + 执行 + 调用日志 + 权限控制。"""
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, PaginationParams
from app.schemas.data_service import (
    DataServiceCreate, DataServiceUpdate, DataServiceResponse,
    ExecuteRequest, ExecuteResultResponse,
)
from app.schemas.data_service_log import (
    CallLogListResponse, CallStatsResponse, DataServicePermissionCreate,
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


@router.get("/call-stats", response_model=ResponseOK[CallStatsResponse], summary="调用统计")
async def call_stats(
    days: int = Query(7, ge=1, le=90, description="统计天数"),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """返回最近 N 天的数据服务调用统计 (总量/成功/失败/平均耗时 + 每日趋势)。"""
    stats = await data_service.get_call_stats(db, days)
    return ResponseOK(data=stats)


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
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    client_ip = request.client.host if request.client else None
    try:
        result = await data_service.execute_api(
            db,
            api_id,
            req.params,
            user_id=user.id,
            username=user.username,
            ip=client_ip,
        )
        return ResponseOK(data=result)
    except PermissionError as e:
        return ResponseOK(code=403, message=str(e))
    except ValueError as e:
        return ResponseOK(code=400, message=str(e))
    except Exception as e:
        return ResponseOK(code=500, message=str(e))


@router.get("/{api_id}/logs", response_model=PageResponse[CallLogListResponse], summary="调用日志")
async def list_call_logs(
    api_id: UUID,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """分页查询指定数据服务的调用日志。"""
    items, total = await data_service.list_call_logs(
        db, pagination.page, pagination.page_size, api_id
    )
    return PageResponse(data=PageResult.create(items, total, pagination.page, pagination.page_size))


@router.get("/{api_id}/permissions", response_model=ResponseOK, summary="权限列表")
async def list_permissions(
    api_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """查询指定数据服务已授权的角色列表。"""
    perms = await data_service.list_permissions(db, api_id)
    return ResponseOK(data=perms)


@router.post("/{api_id}/permissions", response_model=ResponseOK, summary="分配权限")
async def assign_permission(
    api_id: UUID,
    req: DataServicePermissionCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """为角色分配数据服务调用/管理权限 (upsert)。"""
    # Ensure the path api_id matches the body-less api_id
    req.api_id = api_id
    try:
        result = await data_service.assign_permission(db, req)
        return ResponseOK(data=result)
    except Exception as e:
        return ResponseOK(code=500, message=str(e))


@router.delete("/{api_id}/permissions/{role_id}", response_model=ResponseOK, summary="撤销权限")
async def revoke_permission(
    api_id: UUID,
    role_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """撤销角色对指定数据服务的访问权限。"""
    ok = await data_service.revoke_permission(db, api_id, role_id)
    if not ok:
        return ResponseOK(code=404, message="Permission not found")
    return ResponseOK()
