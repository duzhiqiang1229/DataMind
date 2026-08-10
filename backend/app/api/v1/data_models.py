"""数据模型管理接口: CRUD + 字段管理 + 版本管理 + DDL。"""
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, PaginationParams
from app.schemas.data_model import DataModelCreate, DataModelUpdate
from app.schemas.common import ResponseOK, PageResponse, PageResult
from app.services import data_model_service

router = APIRouter()


class DomainPayload(BaseModel):
    domain_name: str
    domain_code: str = ""
    data_domain: str | None = None
    description: str | None = None
    sort_order: int = 0


def _domain_dict(d) -> dict:
    return {
        "id": str(d.id),
        "domain_name": d.domain_name,
        "domain_code": d.domain_code,
        "data_domain": getattr(d, "data_domain", None),
        "description": d.description,
        "sort_order": d.sort_order,
    }


@router.get("/business-domains", response_model=ResponseOK[list[dict]], summary="业务域列表")
async def list_business_domains(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    from app.models import BusinessDomain
    result = await db.execute(
        select(BusinessDomain).order_by(BusinessDomain.sort_order, BusinessDomain.domain_name)
    )
    return ResponseOK(data=[_domain_dict(d) for d in result.scalars().all()])


@router.post("/business-domains", response_model=ResponseOK[dict], summary="新增业务过程")
async def create_business_domain(
    body: DomainPayload,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    from app.models import BusinessDomain
    d = BusinessDomain(
        domain_name=body.domain_name,
        domain_code=body.domain_code or body.domain_name,
        data_domain=body.data_domain,
        description=body.description,
        sort_order=body.sort_order,
    )
    db.add(d)
    await db.commit()
    await db.refresh(d)
    return ResponseOK(data=_domain_dict(d))


@router.put("/business-domains/{domain_id}", response_model=ResponseOK[dict], summary="更新业务过程")
async def update_business_domain(
    domain_id: str,
    body: DomainPayload,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    from app.models import BusinessDomain
    d = (await db.execute(select(BusinessDomain).where(BusinessDomain.id == uuid.UUID(domain_id)))).scalar_one_or_none()
    if not d:
        return ResponseOK(code=404, message="业务过程不存在")
    d.domain_name = body.domain_name
    d.domain_code = body.domain_code or body.domain_name
    d.data_domain = body.data_domain
    d.description = body.description
    d.sort_order = body.sort_order
    await db.commit()
    await db.refresh(d)
    return ResponseOK(data=_domain_dict(d))


@router.delete("/business-domains/{domain_id}", response_model=ResponseOK, summary="删除业务过程")
async def delete_business_domain(
    domain_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    from app.models import BusinessDomain
    d = (await db.execute(select(BusinessDomain).where(BusinessDomain.id == uuid.UUID(domain_id)))).scalar_one_or_none()
    if not d:
        return ResponseOK(code=404, message="业务过程不存在")
    await db.delete(d)
    await db.commit()
    return ResponseOK()


@router.get("/data-domains", response_model=ResponseOK[list[dict]], summary="数据域列表")
async def list_data_domains(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    from app.models import DataDomain
    result = await db.execute(
        select(DataDomain).order_by(DataDomain.sort_order, DataDomain.domain_name)
    )
    return ResponseOK(data=[_domain_dict(d) for d in result.scalars().all()])


@router.post("/data-domains", response_model=ResponseOK[dict], summary="新增数据域")
async def create_data_domain(
    body: DomainPayload,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    from app.models import DataDomain
    d = DataDomain(
        domain_name=body.domain_name,
        domain_code=body.domain_code or body.domain_name,
        description=body.description,
        sort_order=body.sort_order,
    )
    db.add(d)
    await db.commit()
    await db.refresh(d)
    return ResponseOK(data=_domain_dict(d))


@router.put("/data-domains/{domain_id}", response_model=ResponseOK[dict], summary="更新数据域")
async def update_data_domain(
    domain_id: str,
    body: DomainPayload,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    from app.models import DataDomain
    d = (await db.execute(select(DataDomain).where(DataDomain.id == uuid.UUID(domain_id)))).scalar_one_or_none()
    if not d:
        return ResponseOK(code=404, message="数据域不存在")
    d.domain_name = body.domain_name
    d.domain_code = body.domain_code or body.domain_name
    d.description = body.description
    d.sort_order = body.sort_order
    await db.commit()
    await db.refresh(d)
    return ResponseOK(data=_domain_dict(d))


@router.delete("/data-domains/{domain_id}", response_model=ResponseOK, summary="删除数据域")
async def delete_data_domain(
    domain_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    from app.models import DataDomain
    d = (await db.execute(select(DataDomain).where(DataDomain.id == uuid.UUID(domain_id)))).scalar_one_or_none()
    if not d:
        return ResponseOK(code=404, message="数据域不存在")
    await db.delete(d)
    await db.commit()
    return ResponseOK()


@router.get("", response_model=PageResponse[dict], summary="数据模型列表")
async def list_models(
    pagination: PaginationParams = Depends(),
    layer: str | None = None,
    status: str | None = None,
    business_domain: str | None = None,
    data_domain: str | None = None,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    items, total = await data_model_service.list_models(
        db, pagination.page, pagination.page_size,
        layer, status, business_domain, data_domain,
    )
    return PageResponse(data=PageResult.create(items, total, pagination.page, pagination.page_size))


@router.post("", response_model=ResponseOK[dict], summary="创建数据模型")
async def create_model(
    req: DataModelCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        result = await data_model_service.create_model(db, req, user.id)
        return ResponseOK(data=result)
    except ValueError as e:
        return ResponseOK(code=400, message=str(e))


@router.post("/{model_id}/publish", response_model=ResponseOK[dict], summary="发布模型(一键建表)")
async def publish_model(
    model_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        result = await data_model_service.publish_model(db, uuid.UUID(model_id))
    except ValueError as e:
        return ResponseOK(code=400, message=str(e))
    if not result:
        return ResponseOK(code=404, message="Model not found")
    return ResponseOK(data=result)


@router.get("/{model_id}", response_model=ResponseOK[dict], summary="模型详情")
async def get_model(model_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await data_model_service.get_model(db, uuid.UUID(model_id))
    if not result:
        return ResponseOK(code=404, message="Model not found")
    return ResponseOK(data=result)


@router.put("/{model_id}", response_model=ResponseOK[dict], summary="更新模型")
async def update_model(
    model_id: str,
    req: DataModelUpdate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    result = await data_model_service.update_model(db, uuid.UUID(model_id), req)
    if not result:
        return ResponseOK(code=404, message="Model not found")
    return ResponseOK(data=result)


@router.delete("/{model_id}", response_model=ResponseOK, summary="删除模型")
async def delete_model(model_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    ok = await data_model_service.delete_model(db, uuid.UUID(model_id))
    if not ok:
        return ResponseOK(code=404, message="Model not found")
    return ResponseOK()


@router.get("/{model_id}/versions", response_model=ResponseOK[list], summary="版本历史")
async def list_versions(model_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await data_model_service.list_versions(db, uuid.UUID(model_id))
    return ResponseOK(data=result)
