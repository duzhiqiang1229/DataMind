"""Data service API service: CRUD + execute + call logs + access control."""
import json
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import delete, select, text, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.data_service import DataServiceApi
from app.models.data_service_log import DataServiceCallLog
from app.models.data_service_permission import DataServicePermission
from app.models.user import Role, UserRole
from app.schemas.data_service import DataServiceCreate, DataServiceUpdate
from app.schemas.data_service_log import DataServicePermissionCreate
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
    db: AsyncSession,
    api_id: uuid.UUID,
    params: dict,
    user_id: uuid.UUID | None = None,
    username: str | None = None,
    ip: str | None = None,
) -> dict:
    """Load API, substitute ${param} placeholders, run on Doris, increment call_count.

    Before execution, the caller's permission is verified via check_permission()
    (users with the 'admin' permission on the API, or a system admin role, bypass).
    After execution, a call log entry is recorded via log_call().
    """
    api = await _get_entity(db, api_id)
    if not api:
        raise ValueError("API not found")
    if api.status != "active":
        raise ValueError(f"API is not active (status={api.status})")

    # --- Access control: verify caller has call/admin permission ---
    if user_id is not None:
        allowed = await check_permission(db, api_id, user_id)
        if not allowed:
            raise PermissionError("No permission to call this API")

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
    params_str = json.dumps(params, ensure_ascii=False, default=str) if params else None
    start_ts = datetime.now(timezone.utc)
    result: dict = {}
    call_status = "success"
    error_msg: str | None = None
    try:
        result = await doris.execute_query(sql, api.database if api.database != "default" else None)
    except Exception as e:
        logger.error(f"[DataService] Execute failed for api {api_id}: {e}")
        call_status = "failed"
        error_msg = str(e)
        raise
    finally:
        elapsed_ms = int((datetime.now(timezone.utc) - start_ts).total_seconds() * 1000)
        # Record the call log regardless of success/failure
        try:
            await log_call(
                db=db,
                api_id=api.id,
                api_path=api.api_path,
                user_id=user_id,
                username=username,
                params=params_str,
                status=call_status,
                row_count=result.get("row_count") if call_status == "success" else None,
                elapsed_ms=elapsed_ms,
                error=error_msg,
                ip=ip,
            )
        except Exception as log_err:
            logger.warning(f"[DataService] Failed to write call log for api {api_id}: {log_err}")

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


# =====================================================================
# Call logging
# =====================================================================


async def log_call(
    db: AsyncSession,
    api_id: uuid.UUID,
    api_path: str,
    user_id: uuid.UUID | None,
    username: str | None,
    params: str | None,
    status: str,
    row_count: int | None,
    elapsed_ms: int | None,
    error: str | None,
    ip: str | None,
) -> dict:
    """Create a data service call log entry."""
    log = DataServiceCallLog(
        api_id=api_id,
        api_path=api_path,
        caller_user_id=user_id,
        caller_username=username,
        request_params=params,
        status=status,
        row_count=row_count,
        elapsed_ms=elapsed_ms,
        error_message=error,
        ip_address=ip,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return _call_log_to_dict(log)


async def list_call_logs(
    db: AsyncSession,
    page: int,
    page_size: int,
    api_id: uuid.UUID | None = None,
) -> tuple[list[dict], int]:
    """Paginated list of data service call logs."""
    query = select(DataServiceCallLog)
    count_q = select(func.count(DataServiceCallLog.id))
    if api_id is not None:
        query = query.where(DataServiceCallLog.api_id == api_id)
        count_q = count_q.where(DataServiceCallLog.api_id == api_id)

    total = (await db.execute(count_q)).scalar_one()
    result = await db.execute(
        query.order_by(DataServiceCallLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    logs = result.scalars().all()
    return [_call_log_to_dict(l) for l in logs], total


async def get_call_stats(db: AsyncSession, days: int = 7) -> dict:
    """Daily call statistics over the last N days."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    base = select(DataServiceCallLog).where(DataServiceCallLog.created_at >= since)

    # Aggregate totals
    totals_q = select(
        func.count(DataServiceCallLog.id).label("total_calls"),
        func.count().filter(DataServiceCallLog.status == "success").label("success_count"),
        func.count().filter(DataServiceCallLog.status == "failed").label("failed_count"),
        func.avg(DataServiceCallLog.elapsed_ms).label("avg_elapsed_ms"),
    ).where(DataServiceCallLog.created_at >= since)

    totals = (await db.execute(totals_q)).one()

    # Daily trend: group by DATE(created_at)
    daily_q = (
        select(
            func.date(DataServiceCallLog.created_at).label("d"),
            func.count(DataServiceCallLog.id).label("count"),
            func.count().filter(DataServiceCallLog.status == "success").label("success"),
            func.count().filter(DataServiceCallLog.status == "failed").label("failed"),
        )
        .where(DataServiceCallLog.created_at >= since)
        .group_by(func.date(DataServiceCallLog.created_at))
        .order_by(func.date(DataServiceCallLog.created_at))
    )
    daily_rows = (await db.execute(daily_q)).all()

    daily_trend = []
    for row in daily_rows:
        d = row.d
        daily_trend.append(
            {
                "date": d.isoformat() if hasattr(d, "isoformat") else str(d),
                "count": int(row.count or 0),
                "success": int(row.success or 0),
                "failed": int(row.failed or 0),
            }
        )

    avg_ms = totals.avg_elapsed_ms
    return {
        "total_calls": int(totals.total_calls or 0),
        "success_count": int(totals.success_count or 0),
        "failed_count": int(totals.failed_count or 0),
        "avg_elapsed_ms": float(avg_ms) if avg_ms is not None else 0,
        "daily_trend": daily_trend,
    }


# =====================================================================
# Access control (permissions)
# =====================================================================


async def assign_permission(
    db: AsyncSession, req: DataServicePermissionCreate
) -> dict:
    """Upsert a data service permission for a role.

    If a (api_id, role_id) entry already exists, update the permission level;
    otherwise insert a new row.
    """
    api_id = req.api_id
    role_id = req.role_id

    existing_q = select(DataServicePermission).where(
        DataServicePermission.api_id == api_id,
        DataServicePermission.role_id == role_id,
    )
    existing = (await db.execute(existing_q)).scalar_one_or_none()

    if existing:
        existing.permission = req.permission
        await db.commit()
        await db.refresh(existing)
        perm = existing
    else:
        perm = DataServicePermission(
            api_id=api_id,
            role_id=role_id,
            permission=req.permission,
        )
        db.add(perm)
        await db.commit()
        await db.refresh(perm)

    return _permission_to_dict(perm)


async def list_permissions(
    db: AsyncSession, api_id: uuid.UUID
) -> list[dict]:
    """List roles that have access to a data service API."""
    query = (
        select(DataServicePermission, Role)
        .join(Role, DataServicePermission.role_id == Role.id)
        .where(DataServicePermission.api_id == api_id)
    )
    rows = (await db.execute(query)).all()
    return [
        {
            "id": str(perm.id),
            "api_id": str(perm.api_id),
            "role_id": str(perm.role_id),
            "role_code": role.role_code,
            "role_name": role.role_name,
            "permission": perm.permission,
            "created_at": perm.created_at.isoformat() if perm.created_at else None,
        }
        for perm, role in rows
    ]


async def revoke_permission(
    db: AsyncSession, api_id: uuid.UUID, role_id: uuid.UUID
) -> bool:
    """Revoke a role's access to a data service API."""
    existing_q = select(DataServicePermission).where(
        DataServicePermission.api_id == api_id,
        DataServicePermission.role_id == role_id,
    )
    existing = (await db.execute(existing_q)).scalar_one_or_none()
    if not existing:
        return False
    await db.delete(existing)
    await db.commit()
    return True


async def check_permission(
    db: AsyncSession, api_id: uuid.UUID, user_id: uuid.UUID
) -> bool:
    """Check if a user's roles grant access to a data service API.

    - A permission row with 'admin' level bypasses (grants call access too).
    - 'call' level grants normal execution access.
    - System admin role (role_code='admin') is always allowed.
    """
    # Fast path: system admin role
    admin_role_q = (
        select(Role.id)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user_id, Role.role_code == "admin")
    )
    admin_role = (await db.execute(admin_role_q)).first()
    if admin_role:
        return True

    # Otherwise, check data_service_permissions for the user's roles
    perm_q = (
        select(DataServicePermission.permission)
        .join(UserRole, UserRole.role_id == DataServicePermission.role_id)
        .where(
            DataServicePermission.api_id == api_id,
            UserRole.user_id == user_id,
            DataServicePermission.permission.in_(["call", "admin"]),
        )
    )
    perm = (await db.execute(perm_q)).first()
    return perm is not None


# =====================================================================
# Call log / permission helpers
# =====================================================================


def _call_log_to_dict(l: DataServiceCallLog) -> dict:
    return {
        "id": str(l.id),
        "api_id": str(l.api_id),
        "api_path": l.api_path,
        "caller_user_id": str(l.caller_user_id) if l.caller_user_id else None,
        "caller_username": l.caller_username,
        "request_params": l.request_params,
        "status": l.status,
        "row_count": l.row_count,
        "elapsed_ms": l.elapsed_ms,
        "error_message": l.error_message,
        "ip_address": l.ip_address,
        "created_at": l.created_at.isoformat() if l.created_at else None,
    }


def _permission_to_dict(p: DataServicePermission) -> dict:
    return {
        "id": str(p.id),
        "api_id": str(p.api_id),
        "role_id": str(p.role_id),
        "permission": p.permission,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }
