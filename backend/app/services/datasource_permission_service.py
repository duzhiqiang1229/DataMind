"""Data source permission service: list, assign (upsert), revoke, check."""
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.datasource_permission import DatasourcePermission
from app.schemas.datasource_permission import DatasourcePermissionCreate


async def list_permissions(
    db: AsyncSession, datasource_id: uuid.UUID
) -> list[dict]:
    """List all role permissions for a datasource."""
    result = await db.execute(
        select(DatasourcePermission)
        .where(DatasourcePermission.datasource_id == datasource_id)
        .order_by(DatasourcePermission.created_at.asc())
    )
    perms = result.scalars().all()
    return [_to_dict(p) for p in perms]


async def assign_permission(
    db: AsyncSession, req: DatasourcePermissionCreate
) -> dict:
    """Upsert: if (datasource, role) permission exists, update; else create."""
    result = await db.execute(
        select(DatasourcePermission).where(
            DatasourcePermission.datasource_id == req.datasource_id,
            DatasourcePermission.role_id == req.role_id,
        )
    )
    perm = result.scalar_one_or_none()
    if perm:
        perm.permission = req.permission
    else:
        perm = DatasourcePermission(
            datasource_id=req.datasource_id,
            role_id=req.role_id,
            permission=req.permission,
        )
        db.add(perm)

    await db.commit()
    await db.refresh(perm)
    return _to_dict(perm)


async def revoke_permission(
    db: AsyncSession, datasource_id: uuid.UUID, role_id: uuid.UUID
) -> bool:
    """Revoke a role's permission on a datasource. Returns False if not found."""
    result = await db.execute(
        select(DatasourcePermission).where(
            DatasourcePermission.datasource_id == datasource_id,
            DatasourcePermission.role_id == role_id,
        )
    )
    perm = result.scalar_one_or_none()
    if not perm:
        return False
    await db.delete(perm)
    await db.commit()
    return True


async def check_permission(
    db: AsyncSession, datasource_id: uuid.UUID, role_id: uuid.UUID
) -> bool:
    """Check if a role has any permission on a datasource. Returns True if permission exists."""
    result = await db.execute(
        select(DatasourcePermission).where(
            DatasourcePermission.datasource_id == datasource_id,
            DatasourcePermission.role_id == role_id,
        )
    )
    perm = result.scalar_one_or_none()
    return perm is not None


def _to_dict(p: DatasourcePermission) -> dict:
    return {
        "id": str(p.id),
        "datasource_id": str(p.datasource_id),
        "role_id": str(p.role_id),
        "permission": p.permission,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }
