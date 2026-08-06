"""User service: CRUD + reset password + toggle status + assign roles."""
import uuid
from typing import Optional

from sqlalchemy import select, update, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import hash_password
from app.models import User, UserRole


async def list_users(
    db: AsyncSession, page: int, page_size: int,
    keyword: Optional[str] = None, status: Optional[str] = None,
) -> tuple[list, int]:
    """Paginated user list with optional filters."""
    query = select(User).options(selectinload(User.roles))
    count_q = select(func.count(User.id))

    if keyword:
        kw = f"%{keyword}%"
        query = query.where(User.username.ilike(kw) | User.full_name.ilike(kw))
        count_q = count_q.where(User.username.ilike(kw) | User.full_name.ilike(kw))
    if status:
        query = query.where(User.status == status)
        count_q = count_q.where(User.status == status)

    total = (await db.execute(count_q)).scalar_one()
    result = await db.execute(
        query.order_by(User.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    users = result.scalars().all()

    items = []
    for u in users:
        items.append({
            "id": str(u.id),
            "username": u.username,
            "email": u.email,
            "phone": u.phone,
            "full_name": u.full_name,
            "avatar": u.avatar,
            "department": u.department,
            "status": u.status,
            "roles": [{"id": str(r.id), "code": r.role_code, "name": r.role_name} for r in u.roles],
            "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        })
    return items, total


async def get_user(db: AsyncSession, user_id: uuid.UUID) -> dict | None:
    result = await db.execute(
        select(User).options(selectinload(User.roles)).where(User.id == user_id)
    )
    u = result.scalar_one_or_none()
    if not u:
        return None
    return {
        "id": str(u.id),
        "username": u.username,
        "email": u.email,
        "phone": u.phone,
        "full_name": u.full_name,
        "avatar": u.avatar,
        "department": u.department,
        "status": u.status,
        "roles": [{"id": str(r.id), "code": r.role_code, "name": r.role_name} for r in u.roles],
        "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }


async def create_user(
    db: AsyncSession, username: str, password: str,
    email: Optional[str] = None, phone: Optional[str] = None,
    full_name: Optional[str] = None, department: Optional[str] = None,
    role_ids: Optional[list[str]] = None,
) -> dict:
    user = User(
        username=username,
        hashed_password=hash_password(password),
        email=email,
        phone=phone,
        full_name=full_name,
        department=department,
    )
    db.add(user)
    await db.flush()

    if role_ids:
        for rid in role_ids:
            db.add(UserRole(user_id=user.id, role_id=uuid.UUID(rid)))

    await db.commit()
    await db.refresh(user)
    return await get_user(db, user.id)


async def update_user(
    db: AsyncSession, user_id: uuid.UUID, **kwargs
) -> dict | None:
    allowed = {"email", "phone", "full_name", "department", "avatar", "status"}
    updates = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
    if updates:
        await db.execute(update(User).where(User.id == user_id).values(**updates))
        await db.commit()
    return await get_user(db, user_id)


async def delete_user(db: AsyncSession, user_id: uuid.UUID) -> bool:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return False
    await db.delete(user)
    await db.commit()
    return True


async def reset_password(db: AsyncSession, user_id: uuid.UUID, new_password: str) -> bool:
    await db.execute(
        update(User).where(User.id == user_id).values(hashed_password=hash_password(new_password))
    )
    await db.commit()
    return True


async def toggle_status(db: AsyncSession, user_id: uuid.UUID) -> dict | None:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return None
    user.status = "disabled" if user.status == "active" else "active"
    await db.commit()
    await db.refresh(user)
    return {"id": str(user.id), "status": user.status}


async def assign_roles(db: AsyncSession, user_id: uuid.UUID, role_ids: list[str]) -> dict | None:
    # delete existing
    await db.execute(delete(UserRole).where(UserRole.user_id == user_id))
    # insert new
    for rid in role_ids:
        db.add(UserRole(user_id=user_id, role_id=uuid.UUID(rid)))
    await db.commit()
    return await get_user(db, user_id)
