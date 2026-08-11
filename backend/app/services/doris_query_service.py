"""Doris query service: SQL execution + DB/table browsing + saved queries + history."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models import SavedQuery, QueryHistory
from app.services.component_service import get_doris_client
from app.utils.sql_safety import validate_read_only_sql


async def execute_query(
    db: AsyncSession, sql: str, database: Optional[str], limit: int, user_id: uuid.UUID
) -> dict:
    """Execute a SELECT query on Doris and record history."""
    sql_stripped = validate_read_only_sql(sql, allow_with=False)

    doris = await get_doris_client(db)
    try:
        result = await doris.execute_query(sql_stripped, database, limit)

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


# --- storage monitoring ---

_STORAGE_OVERVIEW_SQL = (
    "SELECT TABLE_SCHEMA, COUNT(*) as table_count, "
    "SUM(TABLE_ROWS) as total_rows, "
    "ROUND(SUM(DATA_LENGTH)/1024/1024, 2) as size_mb "
    "FROM information_schema.tables GROUP BY TABLE_SCHEMA"
)


async def get_storage_overview(db: AsyncSession) -> dict:
    """Database-level storage overview.

    Tries information_schema first; falls back to list_databases + list_tables.
    """
    doris = await get_doris_client(db)

    # Try information_schema approach
    try:
        result = await doris.execute_query(_STORAGE_OVERVIEW_SQL, None, 10000)
        if result.get("columns"):
            databases = []
            col_idx = {col.lower(): i for i, col in enumerate(result["columns"])}
            for row in result["rows"]:
                schema = row[col_idx["table_schema"]]
                if not schema or schema.lower() in ("information_schema", "mysql", "__internal_schema"):
                    continue
                databases.append({
                    "name": schema,
                    "table_count": int(row[col_idx["table_count"]] or 0),
                    "total_rows": int(row[col_idx["total_rows"]] or 0),
                    "total_size_mb": float(row[col_idx["size_mb"]] or 0.0),
                })
            return {"databases": databases}
    except Exception as e:
        logger.warning(f"information_schema storage query failed, falling back: {e}")

    # Fallback: iterate databases and tables
    db_names = await doris.list_databases()
    databases = []
    for db_name in db_names:
        if db_name.lower() in ("information_schema", "mysql", "__internal_schema"):
            continue
        try:
            tables = await doris.list_tables(db_name)
        except Exception as e:
            logger.warning(f"Failed to list tables for {db_name}: {e}")
            tables = []

        total_rows = 0
        total_size_mb = 0.0
        for t in tables:
            try:
                total_rows += int(t.get("rows") or 0)
            except (TypeError, ValueError):
                pass
            try:
                total_size_mb += float(t.get("data_size") or 0.0)
            except (TypeError, ValueError):
                pass

        databases.append({
            "name": db_name,
            "table_count": len(tables),
            "total_rows": total_rows,
            "total_size_mb": round(total_size_mb, 2),
        })

    return {"databases": databases}


async def get_table_stats(db: AsyncSession, database: str, table: str) -> dict:
    """Detailed statistics for a single table."""
    doris = await get_doris_client(db)

    stats: dict = {
        "name": table,
        "engine": None,
        "rows": 0,
        "data_size": 0,
        "create_time": None,
        "columns": 0,
    }

    # Use list_tables output (SHOW TABLE STATUS) for base stats
    try:
        tables = await doris.list_tables(database)
        for t in tables:
            if t.get("name") == table:
                stats.update({
                    "name": t.get("name", table),
                    "engine": t.get("engine"),
                    "rows": t.get("rows", 0),
                    "data_size": t.get("data_size", 0),
                    "create_time": t.get("create_time"),
                })
                break
    except Exception as e:
        logger.warning(f"Failed to get table status for {database}.{table}: {e}")

    # Column count via schema
    try:
        schema = await doris.get_table_schema(database, table)
        stats["columns"] = len(schema)
    except Exception as e:
        logger.warning(f"Failed to get schema for {database}.{table}: {e}")

    # Partition info
    partitions: list[dict] = []
    try:
        partitions = await get_table_partitions(db, database, table)
    except Exception as e:
        logger.warning(f"Failed to get partitions for {database}.{table}: {e}")
    stats["partitions"] = partitions
    stats["partition_count"] = len(partitions)

    return stats


async def get_table_partitions(db: AsyncSession, database: str, table: str) -> list[dict]:
    """Partition details via SHOW PARTITIONS."""
    doris = await get_doris_client(db)
    sql = f"SHOW PARTITIONS FROM {database}.{table}"
    result = await doris.execute_query(sql, None, 10000)

    if not result.get("columns") or not result.get("rows"):
        return []

    columns = result["columns"]
    col_idx = {col.lower(): i for i, col in enumerate(columns)}

    partitions = []
    for row in result["rows"]:
        part: dict = {}
        # Map common Apache Doris SHOW PARTITIONS columns
        for field in (
            "partition_name", "partition_key", "partition_value",
            "rows", "data_size", "visible_version",
            "visible_version_time", "visible_version_hash",
        ):
            idx = col_idx.get(field)
            if idx is not None:
                part[field] = row[idx]

        # Normalize commonly expected keys
        if "partition_name" in part:
            part["name"] = part["partition_name"]
        if "data_size" in part:
            try:
                part["data_size"] = float(part["data_size"] or 0)
            except (TypeError, ValueError):
                pass
        if "rows" in part:
            try:
                part["rows"] = int(part["rows"] or 0)
            except (TypeError, ValueError):
                pass

        # Include all raw columns for completeness
        part["raw"] = {columns[i]: row[i] for i in range(len(columns))}
        partitions.append(part)

    return partitions
