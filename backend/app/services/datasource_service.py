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
    keyword: Optional[str] = None,
) -> tuple[list[dict], int]:
    query = select(DataSource)
    count_q = select(func.count(DataSource.id))

    if keyword:
        kw = f"%{keyword}%"
        query = query.where(
            DataSource.source_name.ilike(kw) | DataSource.host.ilike(kw)
        )
        count_q = count_q.where(
            DataSource.source_name.ilike(kw) | DataSource.host.ilike(kw)
        )
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
        if ds.source_type in ("mysql", "doris"):
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


async def execute_query(
    db: AsyncSession, ds_id: uuid.UUID, sql: str, limit: int = 10000,
    database: Optional[str] = None,
) -> dict:
    """Execute a read-only query against a configured data source.

    Supports MySQL and PostgreSQL sources (same drivers as connection test).
    Returns the same result shape as the Doris query service.
    """
    result = await db.execute(select(DataSource).where(DataSource.id == ds_id))
    ds = result.scalar_one_or_none()
    if not ds:
        raise ValueError("Data source not found")
    if ds.status != "active":
        raise ValueError("Data source is not active")

    sql_stripped = sql.strip()
    head = sql_stripped.upper()[:16]
    if not (
        head.startswith("SELECT")
        or head.startswith("SHOW")
        or head.startswith("DESC")
        or head.startswith("WITH")
    ):
        raise ValueError("Only SELECT/SHOW/DESC/WITH queries are allowed")

    password = decrypt_value(ds.password_encrypted)
    target_db = database or ds.database_name or ""
    import time
    start = time.time()
    rows = []

    if ds.source_type in ("mysql", "doris"):
        import pymysql
        try:
            conn = pymysql.connect(
                host=ds.host, port=ds.port, user=ds.username, password=password,
                database=target_db, charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor,
                connect_timeout=10, read_timeout=300,
            )
        except pymysql.err.MySQLError as e:
            raise ValueError(f"数据库连接失败：{e.args[-1] if e.args else e}") from e
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql)
                rows = cursor.fetchmany(limit + 1)
        except pymysql.err.MySQLError as e:
            raise ValueError(f"查询失败：{e.args[-1] if e.args else e}") from e
        finally:
            conn.close()
    elif ds.source_type == "postgresql":
        import psycopg2
        import psycopg2.extras
        try:
            conn = psycopg2.connect(
                host=ds.host, port=ds.port, user=ds.username, password=password,
                dbname=target_db, connect_timeout=10,
            )
        except psycopg2.Error as e:
            raise ValueError(f"数据库连接失败：{e}") from e
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(sql)
                rows = [dict(r) for r in cursor.fetchmany(limit + 1)]
        except psycopg2.Error as e:
            raise ValueError(f"查询失败：{e}") from e
        finally:
            conn.close()
    else:
        raise ValueError(f"Query not supported for source type: {ds.source_type}")

    truncated = len(rows) > limit
    rows = rows[:limit]
    elapsed_ms = int((time.time() - start) * 1000)
    columns = list(rows[0].keys()) if rows else []
    return {
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
        "truncated": truncated,
        "elapsed_ms": elapsed_ms,
    }


async def list_databases(db: AsyncSession, ds_id: uuid.UUID) -> list[str]:
    """List all databases accessible on the data source server."""
    result = await db.execute(select(DataSource).where(DataSource.id == ds_id))
    ds = result.scalar_one_or_none()
    if not ds:
        return []
    if ds.status != "active":
        return []

    password = decrypt_value(ds.password_encrypted)
    system_dbs = {"information_schema", "mysql", "sys", "performance_schema", "postgres", "template0", "template1"}

    if ds.source_type in ("mysql", "doris"):
        import pymysql
        try:
            conn = pymysql.connect(
                host=ds.host, port=ds.port, user=ds.username, password=password,
                database="", charset="utf8mb4",
                connect_timeout=10, read_timeout=30,
            )
            with conn.cursor() as cursor:
                cursor.execute("SHOW DATABASES")
                rows = cursor.fetchall()
            conn.close()
        except Exception:
            return []
        names = [r[0] for r in rows]
        return [n for n in names if n not in system_dbs]
    elif ds.source_type == "postgresql":
        import psycopg2
        try:
            conn = psycopg2.connect(
                host=ds.host, port=ds.port, user=ds.username, password=password,
                dbname=ds.database_name or "postgres", connect_timeout=10,
            )
            with conn.cursor() as cursor:
                cursor.execute("SELECT datname FROM pg_database ORDER BY datname")
                rows = cursor.fetchall()
            conn.close()
        except Exception:
            return []
        return [r[0] for r in rows if r[0] not in system_dbs]
    return []


async def list_tables(db: AsyncSession, ds_id: uuid.UUID, schema: Optional[str] = None) -> list[dict]:
    """List tables in the data source."""
    result = await db.execute(select(DataSource).where(DataSource.id == ds_id))
    ds = result.scalar_one_or_none()
    if not ds:
        return []

    password = decrypt_value(ds.password_encrypted)

    if ds.source_type in ("mysql", "doris"):
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

    if ds.source_type in ("mysql", "doris"):
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
