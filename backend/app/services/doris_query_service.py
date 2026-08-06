"""Doris query service: SQL execution + DB/table browsing + saved queries + history."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models import SavedQuery, QueryHistory
from app.services.component_service import get_doris_client


async def execute_query(
    db: AsyncSession, sql: str, database: Optional[str], limit: int, user_id: uuid.UUID
) -> dict:
    """Execute a SELECT query on Doris and record history."""
    sql_stripped = sql.strip()
    if not sql_stripped.upper().startswith("SELECT") and not sql_stripped.upper().startswith("SHOW") and not sql_stripped.upper().startswith("DESC"):
        raise ValueError("Only SELECT/SHOW/DESC queries are allowed")

    doris = await get_doris_client(db)
    try:
        result = await doris.execute_query(sql, database, limit)

        # save to history
        history = QueryHistory(
            sql_text=sql,
            database=database,
            row_count=result["row_count"],
            truncated=result["truncated"],
            elapsed_ms=result["elapsed_ms"],
            status="success",
            executed_by=user_id,
        )
        db.add(history)
        await db.commit()

        return result
    except Exception as e:
        # save error to history
        history = QueryHistory(
            sql_text=sql,
            database=database,
            status="error",
            error_message=str(e),
            executed_by=user_id,
        )
        db.add(history)
        await db.commit()
        raise


async def list_databases(db: AsyncSession) -> list[dict]:
    doris = await get_doris_client(db)
    dbs = await doris.list_databases()
    return [{"name": d} for d in dbs]


async def list_tables(db: AsyncSession, database: str) -> list[dict]:
    doris = await get_doris_client(db)
    return await doris.list_tables(database)


async def get_table_schema(db: AsyncSession, database: str, table: str) -> list[dict]:
    doris = await get_doris_client(db)
    return await doris.get_table_schema(database, table)


# --- saved queries ---

async def list_saved_queries(
    db: AsyncSession, page: int, page_size: int, tags: Optional[str] = None
) -> tuple[list[dict], int]:
    query = select(SavedQuery)
    count_q = select(func.count(SavedQuery.id))
    if tags:
        query = query.where(SavedQuery.tags.ilike(f"%{tags}%"))
        count_q = count_q.where(SavedQuery.tags.ilike(f"%{tags}%"))

    total = (await db.execute(count_q)).scalar_one()
    result = await db.execute(
        query.order_by(SavedQuery.updated_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    queries = result.scalars().all()
    return [_saved_to_dict(q) for q in queries], total


async def save_query(db: AsyncSession, req, user_id: uuid.UUID) -> dict:
    q = SavedQuery(
        query_name=req.query_name,
        description=req.description,
        sql_text=req.sql_text,
        database=req.database,
        tags=req.tags,
        created_by=user_id,
    )
    db.add(q)
    await db.commit()
    await db.refresh(q)
    return _saved_to_dict(q)


async def delete_saved_query(db: AsyncSession, query_id: uuid.UUID) -> bool:
    result = await db.execute(select(SavedQuery).where(SavedQuery.id == query_id))
    q = result.scalar_one_or_none()
    if not q:
        return False
    await db.delete(q)
    await db.commit()
    return True


# --- query history ---

async def list_history(
    db: AsyncSession, page: int, page_size: int, status: Optional[str] = None
) -> tuple[list[dict], int]:
    query = select(QueryHistory)
    count_q = select(func.count(QueryHistory.id))
    if status:
        query = query.where(QueryHistory.status == status)
        count_q = count_q.where(QueryHistory.status == status)

    total = (await db.execute(count_q)).scalar_one()
    result = await db.execute(
        query.order_by(QueryHistory.executed_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    items = result.scalars().all()
    return [_history_to_dict(h) for h in items], total


async def get_history(db: AsyncSession, history_id: uuid.UUID) -> dict | None:
    result = await db.execute(select(QueryHistory).where(QueryHistory.id == history_id))
    h = result.scalar_one_or_none()
    if not h:
        return None
    return _history_to_dict(h)


def _saved_to_dict(q: SavedQuery) -> dict:
    return {
        "id": str(q.id),
        "query_name": q.query_name,
        "description": q.description,
        "sql_text": q.sql_text,
        "database": q.database,
        "tags": q.tags,
        "created_by": str(q.created_by) if q.created_by else None,
        "created_at": q.created_at.isoformat() if q.created_at else None,
        "updated_at": q.updated_at.isoformat() if q.updated_at else None,
    }


def _history_to_dict(h: QueryHistory) -> dict:
    return {
        "id": str(h.id),
        "sql_text": h.sql_text,
        "database": h.database,
        "row_count": h.row_count,
        "truncated": h.truncated,
        "elapsed_ms": h.elapsed_ms,
        "status": h.status,
        "error_message": h.error_message,
        "executed_by": str(h.executed_by) if h.executed_by else None,
        "executed_at": h.executed_at.isoformat() if h.executed_at else None,
    }
