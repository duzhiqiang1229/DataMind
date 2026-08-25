"""ETL script API."""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role, PaginationParams
from app.schemas.common import ResponseOK, PageResponse, PageResult
from app.schemas.etl_script import EtlScriptCreate, EtlScriptUpdate, EtlScriptExecute
from app.services import etl_script_service

router = APIRouter()
engineer_only = [Depends(require_role("data_engineer"))]


@router.get("", response_model=PageResponse[dict], summary="ETL 脚本列表")
async def list_scripts(
    pagination: PaginationParams = Depends(),
    language: str | None = None,
    keyword: str | None = None,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    items, total = await etl_script_service.list_scripts(
        db, pagination.page, pagination.page_size, language, keyword
    )
    return PageResponse(data=PageResult.create(items, total, pagination.page, pagination.page_size))


@router.post("", response_model=ResponseOK[dict], summary="创建 ETL 脚本", dependencies=engineer_only)
async def create_script(
    req: EtlScriptCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    result = await etl_script_service.create_script(db, req, user.id)
    return ResponseOK(data=result)

@router.get("/{script_id}", response_model=ResponseOK[dict], summary="ETL 脚本详情")
async def get_script(
    script_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    result = await etl_script_service.get_script(db, uuid.UUID(script_id))
    if not result:
        return ResponseOK(code=404, message="Script not found")
    return ResponseOK(data=result)


@router.put("/{script_id}", response_model=ResponseOK[dict], summary="更新 ETL 脚本", dependencies=engineer_only)
async def update_script(
    script_id: str,
    req: EtlScriptUpdate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    result = await etl_script_service.update_script(db, uuid.UUID(script_id), req)
    if not result:
        return ResponseOK(code=404, message="Script not found")
    return ResponseOK(data=result)


@router.delete("/{script_id}", response_model=ResponseOK, summary="删除 ETL 脚本", dependencies=engineer_only)
async def delete_script(
    script_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    ok = await etl_script_service.delete_script(db, uuid.UUID(script_id))
    if not ok:
        return ResponseOK(code=404, message="Script not found")
    return ResponseOK()


@router.post("/{script_id}/execute", response_model=ResponseOK[dict], summary="执行 ETL 脚本", dependencies=engineer_only)
async def execute_script(
    script_id: str,
    req: EtlScriptExecute,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        result = await etl_script_service.execute_script(
            db, uuid.UUID(script_id), req.datasource_id, req.database, req.limit
        )
    except ValueError as e:
        return ResponseOK(code=400, message=str(e))
    return ResponseOK(data=result)
