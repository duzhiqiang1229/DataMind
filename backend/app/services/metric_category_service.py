"""Metric category service: category CRUD + metric mapping."""
import uuid
from typing import Optional

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.metric_category import MetricCategory, MetricMapping
from app.schemas.metric_category import (
    MetricCategoryCreate, MetricCategoryUpdate,
    MetricMappingCreate,
)


async def list_categories(db: AsyncSession) -> list[dict]:
    """List all metric categories ordered by sort_order."""
    result = await db.execute(
        select(MetricCategory).order_by(MetricCategory.sort_order.asc(), MetricCategory.created_at.asc())
    )
    categories = result.scalars().all()
    return [_category_to_dict(c) for c in categories]


async def create_category(db: AsyncSession, req: MetricCategoryCreate) -> dict:
    """Create a new metric category."""
    category = MetricCategory(
        category_name=req.category_name,
        category_code=req.category_code,
        description=req.description,
        sort_order=req.sort_order,
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return _category_to_dict(category)


async def update_category(
    db: AsyncSession, category_id: uuid.UUID, req: MetricCategoryUpdate
) -> dict | None:
    """Update a metric category. Returns None if not found."""
    result = await db.execute(
        select(MetricCategory).where(MetricCategory.id == category_id)
    )
    category = result.scalar_one_or_none()
    if not category:
        return None

    if req.category_name is not None:
        category.category_name = req.category_name
    if req.category_code is not None:
        category.category_code = req.category_code
    if req.description is not None:
        category.description = req.description
    if req.sort_order is not None:
        category.sort_order = req.sort_order

    await db.commit()
    await db.refresh(category)
    return _category_to_dict(category)


async def delete_category(db: AsyncSession, category_id: uuid.UUID) -> bool:
    """Delete a metric category and its mappings. Returns False if not found."""
    result = await db.execute(
        select(MetricCategory).where(MetricCategory.id == category_id)
    )
    category = result.scalar_one_or_none()
    if not category:
        return False

    # Cascade delete mappings first (in case FK cascade hasn't applied)
    await db.execute(
        delete(MetricMapping).where(MetricMapping.category_id == category_id)
    )
    await db.delete(category)
    await db.commit()
    return True


async def assign_metric(
    db: AsyncSession, category_id: uuid.UUID,
    metric_name: str, metric_label: Optional[str] = None,
) -> dict:
    """Assign a Cube metric to a category. Upsert: if metric_name already mapped to this category, update label."""
    existing = await db.execute(
        select(MetricMapping).where(
            MetricMapping.category_id == category_id,
            MetricMapping.metric_name == metric_name,
        )
    )
    mapping = existing.scalar_one_or_none()
    if mapping:
        mapping.metric_label = metric_label
    else:
        mapping = MetricMapping(
            category_id=category_id,
            metric_name=metric_name,
            metric_label=metric_label,
        )
        db.add(mapping)

    await db.commit()
    await db.refresh(mapping)
    return _mapping_to_dict(mapping)


async def list_metrics_by_category(
    db: AsyncSession, category_id: uuid.UUID
) -> list[dict]:
    """List all metrics mapped to a category."""
    result = await db.execute(
        select(MetricMapping)
        .where(MetricMapping.category_id == category_id)
        .order_by(MetricMapping.created_at.asc())
    )
    mappings = result.scalars().all()
    return [_mapping_to_dict(m) for m in mappings]


async def list_unmapped_metrics(db: AsyncSession) -> list[dict]:
    """List Cube metrics that have not been mapped to any category.

    Calls Cube meta API to get all metrics, then filters out mapped ones.
    """
    from app.services.cube_service import get_meta
    from app.services.component_service import get_cube_client

    # Get all mapped metric names
    mapped_result = await db.execute(select(MetricMapping.metric_name))
    mapped_names = {row[0] for row in mapped_result.all()}

    # Get all Cube metrics from meta
    try:
        cube = await get_cube_client(db)
        meta = await cube.get_meta()
    except RuntimeError as e:
        logger.warning(f"Cube not configured, returning empty unmapped list: {e}")
        return []

    # Cube meta format: { "cubes": [ { "name": "Orders", "measures": [ {"name": "Orders.count", "title": "Count"}, ... ] } ] }
    unmapped = []
    cubes = meta.get("cubes", [])
    for cube_obj in cubes:
        cube_name = cube_obj.get("name", "")
        measures = cube_obj.get("measures", [])
        for measure in measures:
            metric_name = measure.get("name", "")
            if metric_name and metric_name not in mapped_names:
                unmapped.append({
                    "metric_name": metric_name,
                    "metric_label": measure.get("title"),
                    "cube_name": cube_name,
                })

    return unmapped


def _category_to_dict(c: MetricCategory) -> dict:
    return {
        "id": str(c.id),
        "category_name": c.category_name,
        "category_code": c.category_code,
        "description": c.description,
        "sort_order": c.sort_order,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


def _mapping_to_dict(m: MetricMapping) -> dict:
    return {
        "id": str(m.id),
        "category_id": str(m.category_id),
        "metric_name": m.metric_name,
        "metric_label": m.metric_label,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }
