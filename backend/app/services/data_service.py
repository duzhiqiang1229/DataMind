"""Data service API service: CRUD + execute + call logs + access control."""
import json
import hashlib
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import delete, select, text, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.data_service import DataServiceApi
from app.models.datasource import DataSource
from app.models.data_service_log import DataServiceCallLog
from app.models.data_service_permission import DataServicePermission
from app.models.data_service_app_key import DataServiceAppKey
from app.models.metric_category import MetricDefinition
from app.models.user import Role, UserRole
from app.schemas.data_service import DataServiceCreate, DataServiceUpdate
from app.schemas.data_service_log import DataServicePermissionCreate
from app.services.component_service import get_doris_client
from app.services import datasource_service
from app.services import cube_service
from app.core.redis import redis_client
from app.utils.sql_safety import validate_read_only_sql


async def list_apis(
    db: AsyncSession, page: int, page_size: int, status: Optional[str] = None
) -> tuple[list[dict], int]:
    """Paginated list of data service APIs."""
    query = select(DataServiceApi, DataSource.source_name).outerjoin(
        DataSource, DataServiceApi.datasource_id == DataSource.id
    )
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
    rows = result.all()
    return [_to_dict(api, datasource_name) for api, datasource_name in rows], total


async def get_api(db: AsyncSession, api_id: uuid.UUID) -> dict | None:
    result = await db.execute(
        select(DataServiceApi, DataSource.source_name)
        .outerjoin(DataSource, DataServiceApi.datasource_id == DataSource.id)
        .where(DataServiceApi.id == api_id)
    )
    row = result.one_or_none()
    if not row:
        return None
    return _to_dict(row[0], row[1])


async def get_api_by_code(db: AsyncSession, service_code: str) -> DataServiceApi | None:
    result = await db.execute(
        select(DataServiceApi).where(DataServiceApi.service_code == service_code)
    )
    return result.scalar_one_or_none()


async def create_api(
    db: AsyncSession, req: DataServiceCreate, user_id: uuid.UUID
) -> dict:
    api = DataServiceApi(
        api_name=req.api_name,
        service_code=req.service_code,
        service_type=req.service_type,
        api_path=req.api_path or f"/open-api/v1/{req.service_code}",
        method=req.method,
        description=req.description,
        sql_template=req.sql_template,
        parameters=req.parameters,
        datasource_id=uuid.UUID(req.datasource_id) if req.datasource_id else None,
        database=req.database,
        table_name=req.table_name,
        selected_fields=req.selected_fields,
        filter_fields=req.filter_fields,
        metric_ids=req.metric_ids,
        metric_dimensions=req.metric_dimensions,
        time_dimension=req.time_dimension,
        default_granularity=req.default_granularity,
        max_rows=req.max_rows,
        cache_enabled=req.cache_enabled,
        cache_ttl=req.cache_ttl,
        status="draft",
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
    if req.service_code is not None:
        api.service_code = req.service_code
        api.api_path = f"/open-api/v1/{req.service_code}"
    if req.service_type is not None:
        api.service_type = req.service_type
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
    if "datasource_id" in req.model_fields_set:
        api.datasource_id = uuid.UUID(req.datasource_id) if req.datasource_id else None
    if req.database is not None:
        api.database = req.database
    if "table_name" in req.model_fields_set:
        api.table_name = req.table_name
    if req.selected_fields is not None:
        api.selected_fields = req.selected_fields
    if req.filter_fields is not None:
        api.filter_fields = req.filter_fields
    if req.metric_ids is not None:
        api.metric_ids = req.metric_ids
    if req.metric_dimensions is not None:
        api.metric_dimensions = req.metric_dimensions
    if "time_dimension" in req.model_fields_set:
        api.time_dimension = req.time_dimension
    if req.default_granularity is not None:
        api.default_granularity = req.default_granularity
    if req.max_rows is not None:
        api.max_rows = req.max_rows
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
    allow_draft: bool = False,
) -> dict:
    """Load API, substitute ${param} placeholders, run on Doris, increment call_count.

    Before execution, the caller's permission is verified via check_permission()
    (users with the 'admin' permission on the API, or a system admin role, bypass).
    After execution, a call log entry is recorded via log_call().
    """
    api = await _get_entity(db, api_id)
    if not api:
        raise ValueError("API not found")
    if not allow_draft and api.status not in {"published", "active"}:
        raise ValueError(f"数据服务未发布 (status={api.status})")

    # --- Access control: verify caller has call/admin permission ---
    if user_id is not None and api.created_by != user_id:
        allowed = await check_permission(db, api_id, user_id)
        if not allowed:
            raise PermissionError("No permission to call this API")

    # Validate and normalize declared parameters.
    for p in (api.parameters or []):
        name = p.get("name")
        required = p.get("required", False)
        if required and (name not in params or params[name] in (None, "")):
            raise ValueError(f"Missing required parameter: {name}")

    normalized_params = _normalize_params(api.parameters or [], params)
    datasource = None
    if api.datasource_id:
        datasource = (
            await db.execute(select(DataSource).where(DataSource.id == api.datasource_id))
        ).scalar_one_or_none()
        if not datasource:
            raise ValueError("数据源不存在")

    sql = None
    if api.service_type == "table":
        if not datasource:
            raise ValueError("物理表服务未配置数据源")
        sql = _build_table_sql(api, normalized_params, datasource.source_type)
    elif api.service_type == "custom_sql":
        sql = _render_sql(api.sql_template, normalized_params)
    if sql is not None:
        sql = validate_read_only_sql(sql)
    params_str = json.dumps(params, ensure_ascii=False, default=str) if params else None
    start_ts = datetime.now(timezone.utc)
    result: dict = {}
    cache_hit = False
    call_status = "success"
    error_msg: str | None = None
    try:
        cache_key = _cache_key(api, normalized_params)
        if api.cache_enabled and api.cache_ttl > 0:
            try:
                cached = await redis_client.get(cache_key)
                if cached:
                    result = json.loads(cached)
                    cache_hit = True
            except Exception as cache_error:
                logger.warning(f"[DataService] Cache read failed: {cache_error}")

        if cache_hit:
            pass
        elif api.service_type == "metric":
            result = await _execute_metric_service(db, api, normalized_params)
        elif api.datasource_id:
            result = await datasource_service.execute_query(
                db, api.datasource_id, sql, limit=api.max_rows, database=api.database or None
            )
        else:
            # Compatibility for services created before datasource binding existed.
            doris = await get_doris_client(db)
            result = await doris.execute_query(sql, api.database or None)
        if api.cache_enabled and api.cache_ttl > 0 and not cache_hit:
            try:
                await redis_client.setex(cache_key, api.cache_ttl, json.dumps(result, ensure_ascii=False, default=str))
            except Exception as cache_error:
                logger.warning(f"[DataService] Cache write failed: {cache_error}")
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
        "elapsed_ms": int((datetime.now(timezone.utc) - start_ts).total_seconds() * 1000),
        "cache_hit": cache_hit,
    }


async def set_status(db: AsyncSession, api_id: uuid.UUID, status: str) -> dict | None:
    if status not in {"draft", "published", "offline"}:
        raise ValueError("Invalid data service status")
    api = await _get_entity(db, api_id)
    if not api:
        return None
    api.status = status
    await db.commit()
    await db.refresh(api)
    return _to_dict(api)


async def execute_by_code(
    db: AsyncSession,
    service_code: str,
    params: dict,
    user_id: uuid.UUID | None = None,
    username: str | None = None,
    ip: str | None = None,
) -> dict:
    api = await get_api_by_code(db, service_code)
    if not api:
        raise ValueError("数据服务不存在")
    return await execute_api(db, api.id, params, user_id, username, ip)


async def create_app_key(
    db: AsyncSession,
    api_id: uuid.UUID,
    key_name: str,
    created_by: uuid.UUID,
    expires_at: datetime | None = None,
) -> dict:
    if not await _get_entity(db, api_id):
        raise ValueError("数据服务不存在")
    raw_key = "dmk_" + secrets.token_urlsafe(32)
    entity = DataServiceAppKey(
        api_id=api_id,
        key_name=key_name,
        key_prefix=raw_key[:12],
        key_hash=hashlib.sha256(raw_key.encode()).hexdigest(),
        expires_at=expires_at,
        created_by=created_by,
    )
    db.add(entity)
    await db.commit()
    await db.refresh(entity)
    return {
        "id": str(entity.id),
        "key_name": entity.key_name,
        "app_key": raw_key,
        "key_prefix": entity.key_prefix,
        "expires_at": entity.expires_at.isoformat() if entity.expires_at else None,
    }


async def list_app_keys(db: AsyncSession, api_id: uuid.UUID) -> list[dict]:
    result = await db.execute(
        select(DataServiceAppKey)
        .where(DataServiceAppKey.api_id == api_id)
        .order_by(DataServiceAppKey.created_at.desc())
    )
    return [
        {
            "id": str(item.id),
            "key_name": item.key_name,
            "key_prefix": item.key_prefix,
            "status": item.status,
            "expires_at": item.expires_at.isoformat() if item.expires_at else None,
            "last_used_at": item.last_used_at.isoformat() if item.last_used_at else None,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        }
        for item in result.scalars().all()
    ]


async def revoke_app_key(db: AsyncSession, api_id: uuid.UUID, key_id: uuid.UUID) -> bool:
    result = await db.execute(
        select(DataServiceAppKey).where(
            DataServiceAppKey.id == key_id, DataServiceAppKey.api_id == api_id
        )
    )
    entity = result.scalar_one_or_none()
    if not entity:
        return False
    entity.status = "revoked"
    await db.commit()
    return True


async def validate_app_key(db: AsyncSession, service_code: str, raw_key: str) -> bool:
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    result = await db.execute(
        select(DataServiceAppKey)
        .join(DataServiceApi, DataServiceAppKey.api_id == DataServiceApi.id)
        .where(
            DataServiceApi.service_code == service_code,
            DataServiceApi.status == "published",
            DataServiceAppKey.key_hash == key_hash,
            DataServiceAppKey.status == "active",
        )
    )
    entity = result.scalar_one_or_none()
    if not entity:
        return False
    now = datetime.now(timezone.utc)
    if entity.expires_at:
        expires_at = entity.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= now:
            return False
    entity.last_used_at = now
    await db.commit()
    return True


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
    if isinstance(value, (list, tuple)):
        if not value:
            return "(NULL)"
        return "(" + ", ".join(_to_sql_literal(item) for item in value) + ")"
    # string fallback — escape single quotes
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


def _normalize_params(definitions: list[dict], params: dict) -> dict:
    definitions_by_name = {item.get("name"): item for item in definitions if item.get("name")}
    unknown = set(params) - set(definitions_by_name)
    if unknown:
        raise ValueError(f"未知参数: {', '.join(sorted(unknown))}")
    normalized = {}
    for name, value in params.items():
        kind = str(definitions_by_name[name].get("type", "string")).lower()
        try:
            if kind in {"integer", "int"}:
                normalized[name] = int(value)
            elif kind in {"float", "number"}:
                normalized[name] = float(value)
            elif kind in {"boolean", "bool"}:
                if isinstance(value, bool):
                    normalized[name] = value
                elif str(value).lower() in {"true", "1", "yes"}:
                    normalized[name] = True
                elif str(value).lower() in {"false", "0", "no"}:
                    normalized[name] = False
                else:
                    raise ValueError
            elif kind in {"array", "list"}:
                normalized[name] = value if isinstance(value, list) else [part.strip() for part in str(value).split(",") if part.strip()]
            else:
                normalized[name] = str(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"参数 {name} 类型错误，应为 {kind}") from exc
    return normalized


def _qualify_cube_member(cube_name: str, member: str) -> str:
    """Return a Cube member in ``cube.member`` form without double-prefixing."""
    value = str(member or "").strip()
    if not value or "." in value:
        return value
    return f"{cube_name}.{value}"


def _cube_member_name(member: str) -> str:
    """Return the member portion used when validating saved short/full names."""
    value = str(member or "").strip()
    return value.split(".", 1)[1] if "." in value else value


def _quote_identifier(identifier: str, source_type: str) -> str:
    parts = identifier.split(".")
    if not parts or any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", part) for part in parts):
        raise ValueError(f"非法字段或表名: {identifier}")
    quote = '"' if source_type == "postgresql" else "`"
    return ".".join(f"{quote}{part}{quote}" for part in parts)


def _build_table_sql(api: DataServiceApi, params: dict, source_type: str) -> str:
    if not api.table_name or not api.selected_fields:
        raise ValueError("物理表服务配置不完整")
    fields = ", ".join(_quote_identifier(field, source_type) for field in api.selected_fields)
    table = _quote_identifier(api.table_name, source_type)
    operator_map = {"eq": "=", "ne": "<>", "gt": ">", "gte": ">=", "lt": "<", "lte": "<=", "like": "LIKE", "in": "IN"}
    conditions = []
    for config in api.filter_fields or []:
        field = config.get("field")
        parameter = config.get("parameter") or field
        if not field or parameter not in params:
            continue
        operator = operator_map.get(config.get("operator", "eq"))
        if not operator:
            raise ValueError(f"不支持的过滤操作符: {config.get('operator')}")
        conditions.append(
            f"{_quote_identifier(field, source_type)} {operator} {_to_sql_literal(params[parameter])}"
        )
    where_clause = f" WHERE {' AND '.join(conditions)}" if conditions else ""
    return f"SELECT {fields} FROM {table}{where_clause} LIMIT {api.max_rows}"


def _cache_key(api: DataServiceApi, params: dict) -> str:
    config = {
        "service_type": api.service_type,
        "sql_template": api.sql_template,
        "datasource_id": str(api.datasource_id) if api.datasource_id else None,
        "database": api.database,
        "table_name": api.table_name,
        "selected_fields": api.selected_fields or [],
        "filter_fields": api.filter_fields or [],
        "metric_ids": api.metric_ids or [],
        "metric_dimensions": api.metric_dimensions or [],
        "time_dimension": api.time_dimension,
        "default_granularity": api.default_granularity,
        "max_rows": api.max_rows,
    }
    payload = json.dumps({"params": params, "config": config}, sort_keys=True, ensure_ascii=False, default=str)
    digest = hashlib.sha256(payload.encode()).hexdigest()
    return f"data_service:{api.id}:{digest}"


async def _execute_metric_service(db: AsyncSession, api: DataServiceApi, params: dict) -> dict:
    try:
        metric_ids = [uuid.UUID(value) for value in api.metric_ids or []]
    except (TypeError, ValueError) as exc:
        raise ValueError("指标服务配置包含无效指标") from exc
    if not metric_ids:
        raise ValueError("指标服务未配置指标")
    result = await db.execute(select(MetricDefinition).where(MetricDefinition.id.in_(metric_ids)))
    definitions_by_id = {item.id: item for item in result.scalars().all()}
    definitions = [definitions_by_id[item_id] for item_id in metric_ids if item_id in definitions_by_id]
    if len(definitions) != len(metric_ids) or any(not item.cube_measure for item in definitions):
        raise ValueError("部分指标不存在或未绑定 Cube 度量")
    cube_names = {item.cube_name for item in definitions}
    if len(cube_names) != 1:
        raise ValueError("同一指标服务中的指标必须属于同一个 Cube")
    cube_name = next(iter(cube_names))

    allowed_dimensions = {
        _cube_member_name(dimension)
        for definition in definitions
        for dimension in (definition.dimensions or [])
    }
    if api.time_dimension:
        allowed_dimensions.add(_cube_member_name(api.time_dimension))
    invalid_dimensions = {
        dimension for dimension in (api.metric_dimensions or [])
        if _cube_member_name(dimension) not in allowed_dimensions
    }
    if invalid_dimensions:
        raise ValueError(f"指标维度配置无效: {', '.join(sorted(invalid_dimensions))}")

    query: dict = {
        "measures": [
            _qualify_cube_member(item.cube_name, item.cube_measure)
            for item in definitions
        ],
        "dimensions": [
            _qualify_cube_member(cube_name, dimension)
            for dimension in (api.metric_dimensions or [])
        ],
        "limit": api.max_rows,
    }
    filters = []
    allowed_operators = {"equals", "notEquals", "contains", "notContains", "gt", "gte", "lt", "lte"}
    for config in api.filter_fields or []:
        member = config.get("member") or config.get("field")
        parameter = config.get("parameter") or member
        if not member or parameter not in params:
            continue
        if _cube_member_name(member) not in allowed_dimensions:
            raise ValueError(f"指标过滤维度无效: {member}")
        operator = config.get("operator", "equals")
        if operator not in allowed_operators:
            raise ValueError(f"指标过滤操作符无效: {operator}")
        value = params[parameter]
        filters.append({
            "member": _qualify_cube_member(cube_name, member),
            "operator": operator,
            "values": [str(item) for item in value] if isinstance(value, list) else [str(value)],
        })
    if filters:
        query["filters"] = filters
    if api.time_dimension:
        time_dimension: dict = {
            "dimension": _qualify_cube_member(cube_name, api.time_dimension),
            "granularity": params.get("granularity") or api.default_granularity or "day",
        }
        start_date, end_date = params.get("start_date"), params.get("end_date")
        if start_date and end_date:
            time_dimension["dateRange"] = [start_date, end_date]
        query["timeDimensions"] = [time_dimension]

    cube_result = await cube_service.load_data(db, query)
    payload = cube_result
    if isinstance(cube_result.get("results"), list) and cube_result["results"]:
        payload = cube_result["results"][0]
    rows = payload.get("data", []) if isinstance(payload, dict) else []
    columns = list(rows[0].keys()) if rows else [*query["dimensions"], *query["measures"]]
    return {
        "columns": columns,
        "rows": rows[: api.max_rows],
        "row_count": min(len(rows), api.max_rows),
        "truncated": len(rows) > api.max_rows,
    }


def _to_dict(a: DataServiceApi, datasource_name: str | None = None) -> dict:
    return {
        "id": str(a.id),
        "api_name": a.api_name,
        "service_code": a.service_code,
        "service_type": a.service_type,
        "api_path": a.api_path,
        "method": a.method,
        "description": a.description,
        "sql_template": a.sql_template,
        "parameters": a.parameters or [],
        "datasource_id": str(a.datasource_id) if a.datasource_id else None,
        "datasource_name": datasource_name,
        "database": a.database,
        "table_name": a.table_name,
        "selected_fields": a.selected_fields or [],
        "filter_fields": a.filter_fields or [],
        "metric_ids": a.metric_ids or [],
        "metric_dimensions": a.metric_dimensions or [],
        "time_dimension": a.time_dimension,
        "default_granularity": a.default_granularity,
        "max_rows": a.max_rows,
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
        "avg_elapsed_ms": int(round(float(avg_ms))) if avg_ms is not None else 0,
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
