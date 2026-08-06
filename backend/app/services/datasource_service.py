"""Data source service: CRUD + connection test + table/column discovery."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.core.security import encrypt_value, decrypt_value
from app.models import DataSource
from app.schemas.datasource import (
    DataSourceCreate, DataSourceUpdate, DataSourceResponse, ConnectionTestResponse,
)

# DB driver map for connection testing
_DRIVER_MAP = {
    "mysql": ("pymysql", "pymysql"),
    "postgresql": ("psycopg2", "psycopg2"),
    "oracle": ("cx_Oracle", "cx_Oracle"),
    "sqlserver": ("pyodbc", "pyodbc"),
}


async def list_datasources(
    db: AsyncSession, page: int, page_size: int,
    source_type: Optional[str] = None, status: Optional[str] = None,
) -> tuple[list[dict], int]:
    query = select(DataSource)
    count_q = select(func.count(DataSource.id))

    if source_type:
        query = query.where(DataSource.source_type == source_type)
        count_q = count_q.where(DataSource.source_type == source_type)
    if status:
        query = query.where(DataSource.status == status)
        count_q = count_q.where(DataSource.status == status)

    total = (await db.execute(count_q)).scalar_one()
    result = await db.execute(
        query.order_by(DataSource.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    sources = result.scalars().all()
    return [_to_response(s) for s in sources], total


async def get_datasource(db: AsyncSession, ds_id: uuid.UUID) -> dict | None:
    result = await db.execute(select(DataSource).where(DataSource.id == ds_id))
    s = result.scalar_one_or_none()
    if not s:
        return None
    return _to_response(s)


async def create_datasource(db: AsyncSession, req: DataSourceCreate, user_id: uuid.UUID) -> dict:
    ds = DataSource(
        source_name=req.source_name,
        source_type=req.source_type,
        host=req.host,
        port=req.port,
        database_name=req.database_name,
        username=req.username,
        password_encrypted=encrypt_value(req.password),
        default_schema=req.default_schema,
        description=req.description,
        created_by=user_id,
    )
    db.add(ds)
    await db.commit()
    await db.refresh(ds)
    return _to_response(ds)


async def update_datasource(
    db: AsyncSession, ds_id: uuid.UUID, req: DataSourceUpdate
) -> dict | None:
    result = await db.execute(select(DataSource).where(DataSource.id == ds_id))
    ds = result.scalar_one_or_none()
    if not ds:
        return None

    if req.source_name is not None:
        ds.source_name = req.source_name
    if req.host is not None:
        ds.host = req.host
    if req.port is not None:
        ds.port = req.port
    if req.database_name is not None:
        ds.database_name = req.database_name
    if req.username is not None:
        ds.username = req.username
    if req.password is not None:
        ds.password_encrypted = encrypt_value(req.password)
    if req.default_schema is not None:
        ds.default_schema = req.default_schema
    if req.description is not None:
        ds.description = req.description
    if req.status is not None:
        ds.status = req.status

    await db.commit()
    await db.refresh(ds)
    return _to_response(ds)


async def delete_datasource(db: AsyncSession, ds_id: uuid.UUID) -> bool:
    result = await db.execute(select(DataSource).where(DataSource.id == ds_id))
    ds = result.scalar_one_or_none()
    if not ds:
        return False
    await db.delete(ds)
    await db.commit()
    return True


async def test_connection(db: AsyncSession, ds_id: uuid.UUID) -> ConnectionTestResponse:
    """Test datasource connectivity."""
    result = await db.execute(select(DataSource).where(DataSource.id == ds_id))
    ds = result.scalar_one_or_none()
    if not ds:
        return ConnectionTestResponse(success=False, message="Data source not found", tested_at=datetime.now(timezone.utc))

    password = decrypt_value(ds.password_encrypted)
    now = datetime.now(timezone.utc)

    try:
        if ds.source_type == "mysql":
            import pymysql
            conn = pymysql.connect(
                host=ds.host, port=ds.port, user=ds.username,
                password=password, database=ds.database_name or "",
                connect_timeout=10,
            )
            cursor = conn.cursor()
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()[0]
            conn.close()
        elif ds.source_type == "postgresql":
            import psycopg2
            conn = psycopg2.connect(
                host=ds.host, port=ds.port, user=ds.username,
                password=password, dbname=ds.database_name or "",
                connect_timeout=10,
            )
            cursor = conn.cursor()
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            conn.close()
        else:
            return ConnectionTestResponse(
                success=False, message=f"Unsupported type: {ds.source_type}", tested_at=now
            )

        # update test result
        await db.execute(
            update(DataSource).where(DataSource.id == ds_id)
            .values(last_connection_test=now, last_connection_ok=True)
        )
        await db.commit()

        return ConnectionTestResponse(success=True, message="Connection OK", version=version, tested_at=now)
    except Exception as e:
        await db.execute(
            update(DataSource).where(DataSource.id == ds_id)
            .values(last_connection_test=now, last_connection_ok=False)
        )
        await db.commit()
        return ConnectionTestResponse(success=False, message=str(e), tested_at=now)


async def list_tables(db: AsyncSession, ds_id: uuid.UUID, schema: Optional[str] = None) -> list[dict]:
    """List tables in the data source."""
    result = await db.execute(select(DataSource).where(DataSource.id == ds_id))
    ds = result.scalar_one_or_none()
    if not ds:
        return []

    password = decrypt_value(ds.password_encrypted)

    if ds.source_type == "mysql":
        import pymysql
        conn = pymysql.connect(
            host=ds.host, port=ds.port, user=ds.username,
            password=password, database=ds.database_name or "",
            connect_timeout=10,
        )
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        conn.close()
        return [{"name": list(t.values())[0]} for t in tables]
    elif ds.source_type == "postgresql":
        import psycopg2
        conn = psycopg2.connect(
            host=ds.host, port=ds.port, user=ds.username,
            password=password, dbname=ds.database_name or "",
            connect_timeout=10,
        )
        cursor = conn.cursor()
        cursor.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = %s ORDER BY table_name
        """, (schema or "public",))
        rows = cursor.fetchall()
        conn.close()
        return [{"name": r[0]} for r in rows]
    return []


async def get_table_columns(
    db: AsyncSession, ds_id: uuid.UUID, table_name: str, schema: Optional[str] = None
) -> list[dict]:
    """Get column definitions of a table."""
    result = await db.execute(select(DataSource).where(DataSource.id == ds_id))
    ds = result.scalar_one_or_none()
    if not ds:
        return []

    password = decrypt_value(ds.password_encrypted)

    if ds.source_type == "mysql":
        import pymysql
        conn = pymysql.connect(
            host=ds.host, port=ds.port, user=ds.username,
            password=password, database=ds.database_name or "",
            connect_timeout=10,
        )
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(f"DESC `{table_name}`")
        cols = cursor.fetchall()
        conn.close()
        return [{
            "field": c.get("Field", ""),
            "type": c.get("Type", ""),
            "null": c.get("Null", ""),
            "key": c.get("Key", ""),
            "default": c.get("Default"),
            "extra": c.get("Extra", ""),
        } for c in cols]
    elif ds.source_type == "postgresql":
        import psycopg2
        conn = psycopg2.connect(
            host=ds.host, port=ds.port, user=ds.username,
            password=password, dbname=ds.database_name or "",
            connect_timeout=10,
        )
        cursor = conn.cursor()
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = %s AND table_schema = %s
            ORDER BY ordinal_position
        """, (table_name, schema or "public"))
        rows = cursor.fetchall()
        conn.close()
        return [{
            "field": r[0], "type": r[1], "null": r[2], "default": r[3], "key": "", "extra": "",
        } for r in rows]
    return []


def _to_response(ds: DataSource) -> dict:
    return {
        "id": str(ds.id),
        "source_name": ds.source_name,
        "source_type": ds.source_type,
        "host": ds.host,
        "port": ds.port,
        "database_name": ds.database_name,
        "username": ds.username,
        "default_schema": ds.default_schema,
        "description": ds.description,
        "status": ds.status,
        "last_connection_test": ds.last_connection_test.isoformat() if ds.last_connection_test else None,
        "last_connection_ok": ds.last_connection_ok,
        "created_at": ds.created_at.isoformat() if ds.created_at else None,
        "updated_at": ds.updated_at.isoformat() if ds.updated_at else None,
    }
