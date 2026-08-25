"""Self-hosted data catalog, lineage and quality APIs."""
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import PaginationParams, get_current_user, require_role
from app.models import QualityRule
from app.schemas.common import PageResponse, PageResult, ResponseOK
from app.services import data_asset_service


router = APIRouter()
engineer_only = [Depends(require_role("data_engineer"))]


class SyncRequest(BaseModel):
    datasource_id: uuid.UUID | None = None


class QualityRulePayload(BaseModel):
    asset_id: uuid.UUID
    rule_name: str = Field(min_length=1, max_length=200)
    rule_type: str = Field(pattern="^(not_null|unique|range|custom_sql)$")
    column_name: str | None = None
    config: dict = {}
    enabled: bool = True


@router.get("/overview", response_model=ResponseOK[dict], summary="资产概览")
async def overview(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    return ResponseOK(data=await data_asset_service.catalog_overview(db))


@router.post("/sync", response_model=ResponseOK[dict], summary="同步数据目录", dependencies=engineer_only)
async def sync_catalog(body: SyncRequest, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    try:
        return ResponseOK(data=await data_asset_service.sync_catalog(db, body.datasource_id))
    except ValueError as exc:
        return ResponseOK(code=400, message=str(exc))


@router.get("/catalog", response_model=PageResponse[dict], summary="数据目录")
async def catalog(
    pagination: PaginationParams = Depends(), keyword: str | None = None,
    datasource_id: uuid.UUID | None = None, status: str | None = "active",
    asset_type: str | None = None,
    db: AsyncSession = Depends(get_db), user=Depends(get_current_user),
):
    items, total = await data_asset_service.list_assets(
        db, pagination.page, pagination.page_size, keyword, datasource_id, status, asset_type
    )
    return PageResponse(data=PageResult.create(items, total, pagination.page, pagination.page_size))


@router.get("/catalog/{asset_id}", response_model=ResponseOK[dict], summary="资产详情")
async def asset_detail(asset_id: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    asset = await data_asset_service.get_asset(db, asset_id)
    if not asset:
        return ResponseOK(code=404, message="资产不存在")
    return ResponseOK(data=asset)


@router.get("/lineage", response_model=ResponseOK[dict], summary="血缘关系列表")
async def lineage(keyword: str | None = None, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    return ResponseOK(data=await data_asset_service.list_lineage(db, keyword))


@router.get("/quality/rules", response_model=ResponseOK[list[dict]], summary="质量规则列表")
async def quality_rules(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    return ResponseOK(data=await data_asset_service.list_quality_rules(db))


@router.post("/quality/rules", response_model=ResponseOK[dict], summary="新建质量规则", dependencies=engineer_only)
async def create_quality_rule(
    body: QualityRulePayload, db: AsyncSession = Depends(get_db), user=Depends(get_current_user),
):
    try:
        return ResponseOK(data=await data_asset_service.create_quality_rule(db, body.model_dump(), user.id))
    except ValueError as exc:
        return ResponseOK(code=400, message=str(exc))


@router.delete("/quality/rules/{rule_id}", response_model=ResponseOK, summary="删除质量规则", dependencies=engineer_only)
async def delete_quality_rule(rule_id: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    rule = (await db.execute(select(QualityRule).where(QualityRule.id == rule_id))).scalar_one_or_none()
    if not rule:
        return ResponseOK(code=404, message="质量规则不存在")
    await db.delete(rule)
    await db.commit()
    return ResponseOK()


@router.post("/quality/rules/{rule_id}/run", response_model=ResponseOK[dict], summary="执行质量规则", dependencies=engineer_only)
async def run_quality_rule(rule_id: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    try:
        return ResponseOK(data=await data_asset_service.run_quality_rule(db, rule_id))
    except ValueError as exc:
        return ResponseOK(code=400, message=str(exc))
