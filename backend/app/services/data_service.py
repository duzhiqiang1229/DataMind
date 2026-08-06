"""Data service API service: CRUD + execute."""
import re
import uuid
from typing import Optional

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.data_service import DataServiceApi
from app.schemas.data_service import DataServiceCreate, DataServiceUpdate
from app.services.component_service import get_doris_client


async def list_apis(
    db: AsyncSession, page: int, page_size: int, status: Optional[str] = None
) -> tuple[list[dict], int]:
    """Paginated list of data service APIs."""
    query = select(DataServiceApi)
    count_q = select(func.count(DataServiceApi.id))
    if status:
        query = query.where(DataServiceApi.status == status)
        count_q = count_q.where(DataServiceApi.status == status)

    total = (await db.execute(count_q)).scalar_one()
    result = await db.execute(
        query.order_by(DataServiceApi.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    apis = result.scalars().all()
    return [_to_dict(a) for a in apis], total


async def get_api(db: AsyncSession, api_id: uuid.UUID) -> dict | None:
    result = await db.execute(select(DataServiceApi).where(DataServiceApi.id == api_id))
    a = result.scalar_one_or_none()
    if not a:
        return None
    return _to_dict(a)


async def create_api(
    db: AsyncSession, req: DataServiceCreate, user_id: uuid.UUID
) -> dict:
    api = DataServiceApi(
        api_name=req.api_name,
        api_path=req.api_path,
        method=req.method,
        description=req.description,
        sql_template=req.sql_template,
        parameters=req.parameters,
        database=req.database,
        created_by=user_id,
    )
    db.add(api)
    await db.commit()
    await db.refresh(api)
    return _to_dict(api)


async def update_api(
    db: AsyncSession, api_id: uuid.UUID, req: DataServiceUpdate
) -> dict | None:
    api = await _get_entity(db, api_id)
    if not api:
        return None

    if req.api_name is not None:
        api.api_name = req.api_name
    if req.api_path is not None:
        api.api_path = req.api_path
    if req.method is not None:
        api.method = req.method
    if req.description is not None:
        api.description = req.description
    if req.sql_template is not None:
        api.sql_template = req.sql_template
    if req.parameters is not None:
        api.parameters = req.parameters
    if req.database is not None:
        api.database = req.database
    if req.cache_enabled is not None:
        api.cache_enabled = req.cache_enabled
    if req.cache_ttl is not None:
        api.cache_ttl = req.cache_ttl
    if req.status is not None:
        api.status = req.status

    await db.commit()
    await db.refresh(api)
    return _to_dict(api)


async def delete_api(db: AsyncSession, api_id: uuid.UUID) -> bool:
    api = await _get_entity(db, api_id)
    if not api:
        return False
    await db.delete(api)
    await db.commit()
    return True


async def execute_api(
    db: AsyncSession, api_id: uuid.UUID, params: dict
) -> dict:
    """Load API, substitute ${param} placeholders, run on Doris, increment call_count."""
    api = await _get_entity(db, api_id)
    if not api:
        raise ValueError("API not found")
    if api.status != "active":
        raise ValueError(f"API is not active (status={api.status})")

    # Validate required parameters
    for p in (api.parameters or []):
        name = p.get("name")
        required = p.get("required", False)
        if required and (name not in params or params[name] in (None, "")):
            raise ValueError(f"Missing required parameter: {name}")

    # Substitute ${param_name} placeholders with provided values
    sql = _render_sql(api.sql_template, params)

    # Only allow read queries for safety
    sql_stripped = sql.strip()
    head = sql_stripped.upper()[:16]
    if not (head.startswith("SELECT") or head.startswith("SHOW") or head.startswith("DESC") or head.startswith("WITH")):
        raise ValueError("Only SELECT/SHOW/DESC/WITH queries are allowed")

    doris = await get_doris_client(db)
    try:
        result = await doris.execute_query(sql, api.database if api.database != "default" else None)
    except Exception as e:
        logger.error(f"[DataService] Execute failed for api {api_id}: {e}")
        raise

    # Increment call_count
    await db.execute(
        update(DataServiceApi)
        .where(DataServiceApi.id == api.id)
        .values(call_count=DataServiceApi.call_count + 1)
    )
    await db.commit()

    return {
        "api_id": str(api.id),
        "api_path": api.api_path,
        "columns": result.get("columns", []),
        "rows": result.get("rows", []),
        "row_count": result.get("row_count", 0),
        "truncated": result.get("truncated", False),
        "elapsed_ms": result.get("elapsed_ms", 0),
    }


# --- helpers ---

async def _get_entity(db: AsyncSession, api_id: uuid.UUID) -> DataServiceApi | None:
    result = await db.execute(select(DataServiceApi).where(DataServiceApi.id == api_id))
    return result.scalar_one_or_none()


def _render_sql(sql_template: str, params: dict) -> str:
    """
    Replace ${param_name} placeholders with provided values.
    Values are converted to SQL literals (quoted strings / raw numbers / raw bools)
    to avoid naive string interpolation breaking SQL syntax.
    Unknown placeholders are left as-is so they surface as Doris syntax errors.
    """
    if not sql_template:
        return ""

    def _replace(match: re.Match) -> str:
        key = match.group("key")
        if key not in params or params[key] is None:
            # leave placeholder; Doris will error if unresolved
            return match.group(0)
        return _to_sql_literal(params[key])

    return re.sub(r"\$\{(?P<key>[A-Za-z_][A-Za-z0-9_]*)\}", _replace, sql_template)


def _to_sql_literal(value) -> str:
    """Convert a Python value into a SQL literal string."""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    # string fallback — escape single quotes
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


def _to_dict(a: DataServiceApi) -> dict:
    return {
        "id": str(a.id),
        "api_name": a.api_name,
        "api_path": a.api_path,
        "method": a.method,
        "description": a.description,
        "sql_template": a.sql_template,
        "parameters": a.parameters or [],
        "database": a.database,
        "cache_enabled": a.cache_enabled,
        "cache_ttl": a.cache_ttl,
        "status": a.status,
        "call_count": a.call_count,
        "created_by": str(a.created_by) if a.created_by else None,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "updated_at": a.updated_at.isoformat() if a.updated_at else None,
    }
