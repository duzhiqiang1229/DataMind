"""数据服务接口: CRUD + 执行 + 调用日志 + 权限控制。"""
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, Header, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_optional_current_user, PaginationParams
from app.schemas.data_service import (
    DataServiceCreate, DataServiceUpdate, DataServiceResponse,
    ExecuteRequest, ExecuteResultResponse, AppKeyCreate, AppKeyCreatedResponse,
)
from app.schemas.data_service_log import (
    CallLogListResponse, CallStatsResponse, DataServicePermissionCreate,
)
from app.schemas.common import ResponseOK, PageResponse, PageResult
from app.services import data_service

router = APIRouter()
public_router = APIRouter()


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


@router.get("/call-logs", response_model=PageResponse[CallLogListResponse], summary="全部调用日志")
async def list_all_call_logs(
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """分页查询全部数据服务的调用日志。"""
    items, total = await data_service.list_call_logs(
        db, pagination.page, pagination.page_size
    )
    return PageResponse(data=PageResult.create(items, total, pagination.page, pagination.page_size))


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
            allow_draft=True,
        )
        return ResponseOK(data=result)
    except PermissionError as e:
        return ResponseOK(code=403, message=str(e))
    except ValueError as e:
        return ResponseOK(code=400, message=str(e))
    except httpx.HTTPStatusError as e:
        detail = ""
        try:
            body = e.response.json()
            detail = str(body.get("error") or body.get("message") or "")
        except (TypeError, ValueError):
            detail = ""
        message = f"Cube 查询失败：{detail}" if detail else "Cube 查询失败，请检查指标和维度配置"
        return ResponseOK(code=400, message=message)
    except Exception as e:
        return ResponseOK(code=500, message=str(e))


@router.post("/{api_id}/publish", response_model=ResponseOK[DataServiceResponse], summary="发布数据服务")
async def publish_api(
    api_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    result = await data_service.set_status(db, api_id, "published")
    if not result:
        return ResponseOK(code=404, message="API not found")
    return ResponseOK(data=result)


@router.post("/{api_id}/offline", response_model=ResponseOK[DataServiceResponse], summary="停用数据服务")
async def offline_api(
    api_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    result = await data_service.set_status(db, api_id, "offline")
    if not result:
        return ResponseOK(code=404, message="API not found")
    return ResponseOK(data=result)


@router.get("/{api_id}/app-keys", response_model=ResponseOK[list[dict]], summary="AppKey 列表")
async def list_app_keys(
    api_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    return ResponseOK(data=await data_service.list_app_keys(db, api_id))


@router.post("/{api_id}/app-keys", response_model=ResponseOK[AppKeyCreatedResponse], summary="创建 AppKey")
async def create_app_key(
    api_id: UUID,
    req: AppKeyCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        result = await data_service.create_app_key(db, api_id, req.key_name, user.id, req.expires_at)
        return ResponseOK(data=result)
    except ValueError as e:
        return ResponseOK(code=400, message=str(e))


@router.delete("/{api_id}/app-keys/{key_id}", response_model=ResponseOK, summary="撤销 AppKey")
async def revoke_app_key(
    api_id: UUID,
    key_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    if not await data_service.revoke_app_key(db, api_id, key_id):
        return ResponseOK(code=404, message="AppKey not found")
    return ResponseOK()


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


async def _invoke_service(
    service_code: str,
    params: dict,
    request: Request,
    db: AsyncSession,
    user,
    app_key: str | None,
):
    try:
        if app_key:
            if not await data_service.validate_app_key(db, service_code, app_key):
                return ResponseOK(code=401, message="AppKey 无效、已撤销或已过期")
        elif user is None:
            return ResponseOK(code=401, message="请提供 Bearer Token 或 X-API-Key")
        return ResponseOK(data=await data_service.execute_by_code(
            db,
            service_code,
            params,
            user_id=user.id if user else None,
            username=user.username if user else "AppKey",
            ip=request.client.host if request.client else None,
        ))
    except PermissionError as e:
        return ResponseOK(code=403, message=str(e))
    except ValueError as e:
        return ResponseOK(code=400, message=str(e))
    except Exception as e:
        return ResponseOK(code=500, message=str(e))


@public_router.get("/{service_code}", response_model=ResponseOK[ExecuteResultResponse], summary="调用已发布数据服务")
async def invoke_get(
    service_code: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_optional_current_user),
    x_api_key: str | None = Header(None, alias="X-API-Key"),
):
    return await _invoke_service(service_code, dict(request.query_params), request, db, user, x_api_key)


@public_router.post("/{service_code}", response_model=ResponseOK[ExecuteResultResponse], summary="调用已发布数据服务")
async def invoke_post(
    service_code: str,
    req: ExecuteRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_optional_current_user),
    x_api_key: str | None = Header(None, alias="X-API-Key"),
):
    return await _invoke_service(service_code, req.params, request, db, user, x_api_key)
