"""Role service: CRUD + permission assignment + menu assignment."""
import uuid
from typing import Optional

from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Role, Permission, RolePermission, RoleMenu


async def list_roles(db: AsyncSession) -> list[dict]:
    result = await db.execute(select(Role).order_by(Role.created_at))
    roles = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "role_code": r.role_code,
            "role_name": r.role_name,
            "description": r.description,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in roles
    ]


async def create_role(
    db: AsyncSession, role_code: str, role_name: str,
    description: Optional[str] = None,
) -> dict:
    role = Role(role_code=role_code, role_name=role_name, description=description)
    db.add(role)
    await db.commit()
    await db.refresh(role)
    return {"id": str(role.id), "role_code": role.role_code, "role_name": role.role_name}


async def update_role(db: AsyncSession, role_id: uuid.UUID, **kwargs) -> dict | None:
    allowed = {"role_name", "description", "status"}
    updates = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
    if updates:
        from sqlalchemy import update
        await db.execute(update(Role).where(Role.id == role_id).values(**updates))
        await db.commit()
    result = await db.execute(select(Role).where(Role.id == role_id))
    r = result.scalar_one_or_none()
    if not r:
        return None
    return {"id": str(r.id), "role_code": r.role_code, "role_name": r.role_name, "status": r.status}


async def delete_role(db: AsyncSession, role_id: uuid.UUID) -> bool:
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    if not role:
        return False
    await db.delete(role)
    await db.commit()
    return True


async def assign_permissions(db: AsyncSession, role_id: uuid.UUID, permission_ids: list[str]) -> bool:
    await db.execute(delete(RolePermission).where(RolePermission.role_id == role_id))
    for pid in permission_ids:
        db.add(RolePermission(role_id=role_id, permission_id=uuid.UUID(pid)))
    await db.commit()
    return True


async def assign_menus(db: AsyncSession, role_id: uuid.UUID, menu_ids: list[str]) -> bool:
    await db.execute(delete(RoleMenu).where(RoleMenu.role_id == role_id))
    for mid in menu_ids:
        db.add(RoleMenu(role_id=role_id, menu_id=uuid.UUID(mid)))
    await db.commit()
    return True


async def list_permissions(db: AsyncSession) -> list[dict]:
    result = await db.execute(select(Permission).order_by(Permission.resource, Permission.action))
    perms = result.scalars().all()
    return [
        {
            "id": str(p.id),
            "permission_code": p.permission_code,
            "permission_name": p.permission_name,
            "resource": p.resource,
            "action": p.action,
            "description": p.description,
        }
        for p in perms
    ]
