"""DAG workflow API: CRUD + deploy."""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, PaginationParams
from app.schemas.common import ResponseOK, PageResponse, PageResult
from app.schemas.dag import DagDefinitionCreate, DagDefinitionUpdate
from app.services import dag_service

router = APIRouter()


@router.get("", response_model=PageResponse[dict], summary="DAG 工作流列表")
async def list_dags(
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    items, total = await dag_service.list_dags(db, pagination.page, pagination.page_size)
    return PageResponse(data=PageResult.create(items, total, pagination.page, pagination.page_size))


@router.post("", response_model=ResponseOK[dict], summary="创建 DAG 工作流")
async def create_dag(
    req: DagDefinitionCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    result = await dag_service.create_dag(db, req)
    return ResponseOK(data=result)


@router.get("/{dag_id}", response_model=ResponseOK[dict], summary="DAG 工作流详情")
async def get_dag(
    dag_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    result = await dag_service.get_dag(db, uuid.UUID(dag_id))
    if not result:
        return ResponseOK(code=404, message="DAG not found")
    return ResponseOK(data=result)


@router.put("/{dag_id}", response_model=ResponseOK[dict], summary="更新 DAG 工作流")
async def update_dag(
    dag_id: str,
    req: DagDefinitionUpdate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        result = await dag_service.update_dag(db, uuid.UUID(dag_id), req)
    except ValueError as e:
        return ResponseOK(code=400, message=str(e))
    if not result:
        return ResponseOK(code=404, message="DAG not found")
    return ResponseOK(data=result)


@router.delete("/{dag_id}", response_model=ResponseOK, summary="删除 DAG 工作流")
async def delete_dag(
    dag_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    ok = await dag_service.delete_dag(db, uuid.UUID(dag_id))
    if not ok:
        return ResponseOK(code=404, message="DAG not found")
    return ResponseOK()


@router.post("/{dag_id}/deploy", response_model=ResponseOK[dict], summary="部署 DAG 到 Airflow")
async def deploy_dag(
    dag_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        result = await dag_service.deploy_dag(db, uuid.UUID(dag_id))
    except ValueError as e:
        return ResponseOK(code=400, message=str(e))
    return ResponseOK(data=result)
