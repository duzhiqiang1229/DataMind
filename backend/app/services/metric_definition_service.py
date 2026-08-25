"""Metric definition service: CRUD."""
import uuid
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MetricDefinition
from app.schemas.metric_definition import MetricDefinitionCreate, MetricDefinitionUpdate


async def list_definitions(
    db: AsyncSession, page: int, page_size: int,
    keyword: Optional[str] = None, category_id: Optional[str] = None,
    metric_type: Optional[str] = None,
) -> tuple[list[dict], int]:
    query = select(MetricDefinition)
    count_q = select(func.count(MetricDefinition.id))
    if keyword:
        kw = f"%{keyword}%"
        query = query.where(
            MetricDefinition.metric_name.ilike(kw)
            | MetricDefinition.metric_code.ilike(kw)
        )
        count_q = count_q.where(
            MetricDefinition.metric_name.ilike(kw)
            | MetricDefinition.metric_code.ilike(kw)
        )
    if category_id:
        query = query.where(MetricDefinition.category_id == uuid.UUID(category_id))
        count_q = count_q.where(MetricDefinition.category_id == uuid.UUID(category_id))
    if metric_type:
        query = query.where(MetricDefinition.metric_type == metric_type)
        count_q = count_q.where(MetricDefinition.metric_type == metric_type)

    total = (await db.execute(count_q)).scalar_one()
    result = await db.execute(
        query.order_by(MetricDefinition.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    return [_to_dict(d) for d in result.scalars().all()], total


async def create_definition(
    db: AsyncSession, req: MetricDefinitionCreate
) -> dict:
    metric_code = req.metric_code
    if not metric_code:
        metric_code = f"M{uuid.uuid4().hex[:8].upper()}"
    d = MetricDefinition(
        metric_code=metric_code,
        metric_name=req.metric_name,
        metric_type=req.metric_type,
        cube_name=req.cube_name,
        cube_measure=req.cube_measure,
        category_id=uuid.UUID(req.category_id) if req.category_id else None,
        dimensions=req.dimensions or [],
        default_time_dimension=req.default_time_dimension,
        calculation=req.calculation,
        business_domain=req.business_domain,
        unit=req.unit,
        description=req.description,
        status=req.status or "draft",
    )
    db.add(d)
    await db.commit()
    await db.refresh(d)
    return _to_dict(d)


async def update_definition(
    db: AsyncSession, definition_id: uuid.UUID, req: MetricDefinitionUpdate
) -> dict | None:
    result = await db.execute(
        select(MetricDefinition).where(MetricDefinition.id == definition_id)
    )
    d = result.scalar_one_or_none()
    if not d:
        return None
    if req.metric_name is not None:
        d.metric_name = req.metric_name
    if req.metric_type is not None:
        d.metric_type = req.metric_type
    if req.cube_name is not None:
        d.cube_name = req.cube_name
    if req.cube_measure is not None:
        d.cube_measure = req.cube_measure
    if req.category_id is not None:
        d.category_id = uuid.UUID(req.category_id) if req.category_id else None
    if req.dimensions is not None:
        d.dimensions = req.dimensions
    if req.default_time_dimension is not None:
        d.default_time_dimension = req.default_time_dimension
    if req.calculation is not None:
        d.calculation = req.calculation
    if req.business_domain is not None:
        d.business_domain = req.business_domain
    if req.unit is not None:
        d.unit = req.unit
    if req.description is not None:
        d.description = req.description
    if req.status is not None:
        d.status = req.status
    await db.commit()
    await db.refresh(d)
    return _to_dict(d)


async def delete_definition(db: AsyncSession, definition_id: uuid.UUID) -> bool:
    result = await db.execute(
        select(MetricDefinition).where(MetricDefinition.id == definition_id)
    )
    d = result.scalar_one_or_none()
    if not d:
        return False
    await db.delete(d)
    await db.commit()
    return True


def _to_dict(d: MetricDefinition) -> dict:
    return {
        "id": str(d.id),
        "metric_code": d.metric_code,
        "metric_name": d.metric_name,
        "metric_type": d.metric_type,
        "cube_name": d.cube_name,
        "cube_measure": d.cube_measure,
        "category_id": str(d.category_id) if d.category_id else None,
        "dimensions": d.dimensions or [],
        "default_time_dimension": d.default_time_dimension,
        "calculation": d.calculation,
        "business_domain": d.business_domain,
        "unit": d.unit,
        "description": d.description,
        "status": d.status,
        "created_at": d.created_at.isoformat() if d.created_at else None,
        "updated_at": d.updated_at.isoformat() if d.updated_at else None,
    }
