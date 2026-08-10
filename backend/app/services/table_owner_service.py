"""Table owner service: list, get, upsert, delete."""
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.table_owner import TableOwner
from app.schemas.table_owner import TableOwnerCreate


async def list_owners(
    db: AsyncSession, page: int, page_size: int,
    database_name: Optional[str] = None,
) -> tuple[list[dict], int]:
    """List table owners with pagination, optionally filtered by database."""
    query = select(TableOwner)
    count_q = select(func.count(TableOwner.id))

    if database_name:
        query = query.where(TableOwner.database_name == database_name)
        count_q = count_q.where(TableOwner.database_name == database_name)

    total = (await db.execute(count_q)).scalar_one()
    result = await db.execute(
        query.order_by(TableOwner.updated_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    owners = result.scalars().all()
    return [_to_dict(o) for o in owners], total


async def get_owner(
    db: AsyncSession, database_name: str, table_name: str
) -> dict | None:
    """Get owner for a specific table. Returns None if not found."""
    result = await db.execute(
        select(TableOwner).where(
            TableOwner.database_name == database_name,
            TableOwner.table_name == table_name,
        )
    )
    owner = result.scalar_one_or_none()
    if not owner:
        return None
    return _to_dict(owner)


async def set_owner(db: AsyncSession, req: TableOwnerCreate) -> dict:
    """Upsert: if owner for (database, table) exists, update; else create."""
    result = await db.execute(
        select(TableOwner).where(
            TableOwner.database_name == req.database_name,
            TableOwner.table_name == req.table_name,
        )
    )
    owner = result.scalar_one_or_none()
    if owner:
        owner.owner_name = req.owner_name
        owner.owner_type = req.owner_type
        owner.contact = req.contact
    else:
        owner = TableOwner(
            database_name=req.database_name,
            table_name=req.table_name,
            owner_name=req.owner_name,
            owner_type=req.owner_type,
            contact=req.contact,
        )
        db.add(owner)

    await db.commit()
    await db.refresh(owner)
    return _to_dict(owner)


async def delete_owner(
    db: AsyncSession, database_name: str, table_name: str
) -> bool:
    """Delete owner for a specific table. Returns False if not found."""
    result = await db.execute(
        select(TableOwner).where(
            TableOwner.database_name == database_name,
            TableOwner.table_name == table_name,
        )
    )
    owner = result.scalar_one_or_none()
    if not owner:
        return False
    await db.delete(owner)
    await db.commit()
    return True


def _to_dict(o: TableOwner) -> dict:
    return {
        "id": str(o.id),
        "database_name": o.database_name,
        "table_name": o.table_name,
        "owner_name": o.owner_name,
        "owner_type": o.owner_type,
        "contact": o.contact,
        "updated_at": o.updated_at.isoformat() if o.updated_at else None,
    }
