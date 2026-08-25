"""MCP client credentials, audit and safe modeling change-set operations."""
import hashlib
import re
import secrets
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    AssetObject, BusinessDomain, DataDomain, DataModel, DataModelField, DataModelVersion,
    DataServiceApi, DataSource, EtlScript, McpChangeSet, McpChangeSetItem, McpClient, McpToken,
    McpToolCall, MetricCategory, MetricDefinition, QualityRule, User,
)
from app.schemas.data_service import DataServiceCreate
from app.schemas.data_model import DataModelFieldItem
from app.services import airflow_service, cube_model_service
from app.services.data_model_service import _generate_ddl
from app.services.mcp_execution_service import render_airflow_dag, validate_dag_payload
from app.utils.sql_safety import validate_read_only_sql


DEFAULT_SCOPES = [
    "metadata:read", "modeling:read", "modeling:draft",
    "development:read", "development:draft", "metrics:read", "metrics:draft",
    "development:execute", "scheduling:read", "scheduling:write", "scheduling:execute",
    "lineage:read", "changeset:draft", "changeset:commit",
    "data_service:read", "data_service:draft", "data_service:execute",
    "data_service:publish", "data_service:credentials", "data_service:monitor",
    "catalog:read", "catalog:sync", "quality:read", "quality:draft", "quality:execute",
]
ALL_SCOPES = set(DEFAULT_SCOPES)


async def list_clients(db: AsyncSession) -> list[dict]:
    rows = (await db.execute(select(McpClient).order_by(McpClient.created_at.desc()))).scalars().all()
    return [_client_dict(row) for row in rows]


async def create_client(
    db: AsyncSession, client_name: str, client_code: str, service_user_id: uuid.UUID,
    scopes: list[str], created_by: uuid.UUID,
) -> dict:
    if not (await db.execute(select(User.id).where(User.id == service_user_id, User.status == "active"))).scalar_one_or_none():
        raise ValueError("绑定的服务用户不存在或已停用")
    if (await db.execute(select(McpClient.id).where(McpClient.client_code == client_code))).scalar_one_or_none():
        raise ValueError("MCP客户端编码已存在")
    normalized_scopes = sorted(set(scopes or DEFAULT_SCOPES))
    unknown_scopes = set(normalized_scopes) - ALL_SCOPES
    if unknown_scopes:
        raise ValueError(f"不支持的授权范围: {', '.join(sorted(unknown_scopes))}")
    entity = McpClient(
        client_name=client_name, client_code=client_code, service_user_id=service_user_id,
        scopes=normalized_scopes, created_by=created_by,
    )
    db.add(entity)
    await db.commit()
    await db.refresh(entity)
    return _client_dict(entity)


async def update_client_scopes(db: AsyncSession, client_id: uuid.UUID, scopes: list[str]) -> dict:
    entity = (await db.execute(select(McpClient).where(McpClient.id == client_id))).scalar_one_or_none()
    if not entity:
        raise ValueError("MCP客户端不存在")
    normalized_scopes = sorted(set(scopes))
    unknown_scopes = set(normalized_scopes) - ALL_SCOPES
    if unknown_scopes:
        raise ValueError(f"不支持的授权范围: {', '.join(sorted(unknown_scopes))}")
    entity.scopes = normalized_scopes
    await db.commit()
    await db.refresh(entity)
    return _client_dict(entity)


async def issue_token(
    db: AsyncSession, client_id: uuid.UUID, token_name: str,
    expires_at: datetime | None = None,
) -> dict:
    client = (await db.execute(select(McpClient).where(McpClient.id == client_id))).scalar_one_or_none()
    if not client:
        raise ValueError("MCP客户端不存在")
    raw_token = "dmmcp_" + secrets.token_urlsafe(36)
    entity = McpToken(
        client_id=client_id, token_name=token_name, token_prefix=raw_token[:16],
        token_hash=hashlib.sha256(raw_token.encode()).hexdigest(), expires_at=expires_at,
    )
    db.add(entity)
    await db.commit()
    await db.refresh(entity)
    return {
        "id": str(entity.id), "token_name": token_name, "access_token": raw_token,
        "token_prefix": entity.token_prefix,
        "expires_at": expires_at.isoformat() if expires_at else None,
    }


async def list_tokens(db: AsyncSession, client_id: uuid.UUID) -> list[dict]:
    rows = (await db.execute(
        select(McpToken)
        .where(McpToken.client_id == client_id)
        .order_by(McpToken.created_at.desc())
    )).scalars().all()
    return [{
        "id": str(row.id), "token_name": row.token_name, "token_prefix": row.token_prefix,
        "status": row.status,
        "expires_at": row.expires_at.isoformat() if row.expires_at else None,
        "last_used_at": row.last_used_at.isoformat() if row.last_used_at else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    } for row in rows]


async def revoke_token(db: AsyncSession, client_id: uuid.UUID, token_id: uuid.UUID) -> bool:
    token = (await db.execute(select(McpToken).where(
        McpToken.id == token_id, McpToken.client_id == client_id,
    ))).scalar_one_or_none()
    if not token:
        return False
    token.status = "revoked"
    await db.commit()
    return True


async def validate_token(db: AsyncSession, raw_token: str) -> dict | None:
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    row = (await db.execute(
        select(McpToken, McpClient, User)
        .join(McpClient, McpToken.client_id == McpClient.id)
        .join(User, McpClient.service_user_id == User.id)
        .where(
            McpToken.token_hash == token_hash, McpToken.status == "active",
            McpClient.status == "active", User.status == "active",
        )
    )).first()
    if not row:
        return None
    token, client, user = row
    now = datetime.now(timezone.utc)
    expires_at = token.expires_at
    if expires_at and (expires_at if expires_at.tzinfo else expires_at.replace(tzinfo=timezone.utc)) <= now:
        return None
    token.last_used_at = now
    client.last_connected_at = now
    await db.commit()
    return {
        "client_id": client.id, "client_code": client.client_code,
        "user_id": user.id, "username": user.username, "scopes": set(client.scopes or []),
    }


async def create_change_set(
    db: AsyncSession, principal: dict, title: str, description: str | None,
) -> dict:
    entity = McpChangeSet(
        change_set_code=f"cs_{datetime.now(timezone.utc):%Y%m%d%H%M%S}_{secrets.token_hex(3)}",
        title=title, description=description, client_id=principal["client_id"],
        created_by=principal["user_id"],
    )
    db.add(entity)
    await db.commit()
    await db.refresh(entity)
    return _change_set_dict(entity)


async def add_change_item(
    db: AsyncSession, principal: dict, change_set_id: uuid.UUID,
    object_type: str, payload: dict,
) -> dict:
    change_set = await _owned_change_set(db, principal, change_set_id)
    if change_set.status != "draft":
        raise ValueError("只有草稿变更集可以增加内容")
    allowed = {
        "data_domain", "business_process", "data_model", "sql_script",
        "metric_category", "cube_model", "metric_definition", "airflow_sql_dag",
        "data_service_api", "quality_rule",
    }
    if object_type not in allowed:
        raise ValueError(f"暂不支持的变更对象: {object_type}")
    next_order = (await db.execute(select(func.coalesce(func.max(McpChangeSetItem.sort_order), 0)).where(
        McpChangeSetItem.change_set_id == change_set_id
    ))).scalar_one() + 1
    item = McpChangeSetItem(
        change_set_id=change_set_id, object_type=object_type, action="create",
        payload=payload, sort_order=next_order,
    )
    db.add(item)
    change_set.validation_status = "pending"
    await db.commit()
    await db.refresh(item)
    return {"item_id": str(item.id), "object_type": object_type, "status": "draft", "payload": payload}


async def get_change_set(db: AsyncSession, principal: dict, change_set_id: uuid.UUID) -> dict:
    entity = await _owned_change_set(db, principal, change_set_id, include_items=True)
    return _change_set_dict(entity, include_items=True)


async def validate_change_set(db: AsyncSession, principal: dict, change_set_id: uuid.UUID) -> dict:
    entity = await _owned_change_set(db, principal, change_set_id, include_items=True)
    errors: list[dict] = []
    warnings: list[dict] = []

    existing_domains = set((await db.execute(select(DataDomain.domain_code))).scalars().all())
    existing_processes = set((await db.execute(select(BusinessDomain.domain_code))).scalars().all())
    existing_models = set((await db.execute(select(DataModel.model_code))).scalars().all())
    existing_scripts = set((await db.execute(select(EtlScript.script_code))).scalars().all())
    existing_categories = set((await db.execute(select(MetricCategory.category_code))).scalars().all())
    existing_metrics = set((await db.execute(select(MetricDefinition.metric_code))).scalars().all())
    existing_service_codes = set((await db.execute(select(DataServiceApi.service_code))).scalars().all())
    existing_cubes = {item["name"]: item for item in cube_model_service.list_models()["cubes"]}
    datasource_types = dict((await db.execute(
        select(DataSource.source_name, DataSource.source_type).where(DataSource.status == "active")
    )).all())
    datasource_names = set(datasource_types)
    existing_dag_ids = {row.get("dag_id") for row in await airflow_service.list_dags(db, limit=500) if row.get("dag_id")}
    draft_domains: set[str] = set()
    draft_processes: set[str] = set()
    draft_models: set[str] = set()
    draft_scripts: set[str] = set()
    draft_categories: set[str] = set()
    draft_cubes: dict[str, dict] = {}
    draft_metrics: set[str] = set()
    draft_service_codes: set[str] = set()
    draft_quality_rules: set[tuple[str, str]] = set()

    declared_domains = {str((item.payload or {}).get("domain_code") or "").strip() for item in entity.items if item.object_type == "data_domain"}
    declared_processes = {str((item.payload or {}).get("process_code") or "").strip() for item in entity.items if item.object_type == "business_process"}
    declared_categories = {str((item.payload or {}).get("category_code") or "").strip() for item in entity.items if item.object_type == "metric_category"}
    declared_cubes = {str((item.payload or {}).get("name") or "").strip() for item in entity.items if item.object_type == "cube_model"}

    for item in entity.items:
        payload = item.payload or {}
        item_errors: list[str] = []
        if item.object_type == "data_domain":
            code = str(payload.get("domain_code") or "").strip()
            if not code or not payload.get("domain_name"):
                item_errors.append("domain_code和domain_name不能为空")
            if code in existing_domains or code in draft_domains:
                item_errors.append(f"数据域编码重复: {code}")
            draft_domains.add(code)
        elif item.object_type == "business_process":
            code = str(payload.get("process_code") or "").strip()
            domain_code = str(payload.get("data_domain_code") or "").strip()
            if not code or not payload.get("process_name"):
                item_errors.append("process_code和process_name不能为空")
            if code in existing_processes or code in draft_processes:
                item_errors.append(f"业务过程编码重复: {code}")
            if domain_code not in existing_domains | declared_domains:
                item_errors.append(f"数据域不存在: {domain_code}")
            draft_processes.add(code)
        elif item.object_type == "data_model":
            code = str(payload.get("model_code") or "").strip()
            domain_code = str(payload.get("data_domain_code") or "").strip()
            process_code = str(payload.get("business_process_code") or "").strip()
            if not code or not payload.get("model_name") or not payload.get("table_name"):
                item_errors.append("model_code、model_name和table_name不能为空")
            if payload.get("layer") not in {"ods", "dim", "dwd", "dws", "ads"}:
                item_errors.append("layer必须是ods/dim/dwd/dws/ads之一")
            if code in existing_models or code in draft_models:
                item_errors.append(f"模型编码重复: {code}")
            if not payload.get("fields"):
                item_errors.append("模型至少需要配置一个字段")
            if domain_code and domain_code not in existing_domains | declared_domains:
                item_errors.append(f"数据域不存在: {domain_code}")
            if process_code and process_code not in existing_processes | declared_processes:
                item_errors.append(f"业务过程不存在: {process_code}")
            draft_models.add(code)
        elif item.object_type == "sql_script":
            code = str(payload.get("script_code") or "").strip()
            if not code or not payload.get("script_name") or not str(payload.get("content") or "").strip():
                item_errors.append("script_code、script_name和content不能为空")
            if not _safe_identifier(code):
                item_errors.append("script_code仅支持字母、数字、下划线和短横线")
            if code in existing_scripts or code in draft_scripts:
                item_errors.append(f"SQL脚本编码重复: {code}")
            try:
                validate_read_only_sql(str(payload.get("content") or ""))
            except ValueError as exc:
                item_errors.append(f"SQL校验失败: {exc}")
            draft_scripts.add(code)
        elif item.object_type == "metric_category":
            code = str(payload.get("category_code") or "").strip()
            if not code or not payload.get("category_name"):
                item_errors.append("category_code和category_name不能为空")
            if not _safe_identifier(code):
                item_errors.append("category_code仅支持字母、数字、下划线和短横线")
            if code in existing_categories or code in draft_categories:
                item_errors.append(f"指标分类编码重复: {code}")
            draft_categories.add(code)
        elif item.object_type == "cube_model":
            name = str(payload.get("name") or "").strip()
            source_name = str(payload.get("data_source") or "").strip()
            if not _safe_cube_identifier(name):
                item_errors.append("Cube名称不能为空且仅支持字母、数字和下划线")
            if name in existing_cubes or name in draft_cubes:
                item_errors.append(f"Cube名称重复: {name}")
            if not source_name or source_name == "default":
                item_errors.append("Cube必须选择真实数据源，不能使用default")
            elif source_name not in datasource_names:
                item_errors.append(f"数据源不存在或未启用: {source_name}")
            if bool(payload.get("sql_table")) == bool(payload.get("sql")):
                item_errors.append("sql_table和sql必须且只能填写一个")
            if "`" in str(payload.get("sql_table") or "") or "`" in str(payload.get("title") or ""):
                item_errors.append("Cube标题和底层表不能包含反引号")
            if payload.get("sql"):
                try:
                    validate_read_only_sql(str(payload["sql"]))
                except ValueError as exc:
                    item_errors.append(f"Cube SQL校验失败: {exc}")
            dimensions = payload.get("dimensions") or []
            measures = payload.get("measures") or []
            if not dimensions:
                item_errors.append("Cube至少需要一个维度")
            if not measures:
                item_errors.append("Cube至少需要一个度量")
            item_errors.extend(_validate_cube_entries(dimensions, "维度", {"string", "number", "time", "boolean", "geo"}))
            item_errors.extend(_validate_cube_entries(measures, "度量", {"count", "sum", "avg", "min", "max", "countDistinct", "number", "string", "time", "boolean"}, allow_count_without_sql=True))
            item_errors.extend(_validate_cube_links(payload.get("joins") or [], "关系", require_relationship=True))
            item_errors.extend(_validate_cube_links(payload.get("segments") or [], "条件"))
            draft_cubes[name] = payload
        elif item.object_type == "metric_definition":
            code = str(payload.get("metric_code") or "").strip()
            category_code = str(payload.get("category_code") or "").strip()
            cube_name = str(payload.get("cube_name") or "").strip()
            cube_measure = str(payload.get("cube_measure") or "").strip()
            if not code or not payload.get("metric_name"):
                item_errors.append("metric_code和metric_name不能为空")
            if not _safe_identifier(code):
                item_errors.append("metric_code仅支持字母、数字、下划线和短横线")
            if payload.get("metric_type") not in {"atomic", "derived", "composite"}:
                item_errors.append("metric_type必须是atomic/derived/composite之一")
            if code in existing_metrics or code in draft_metrics:
                item_errors.append(f"指标编码重复: {code}")
            if category_code and category_code not in existing_categories | declared_categories:
                item_errors.append(f"指标分类不存在: {category_code}")
            cube = existing_cubes.get(cube_name) or draft_cubes.get(cube_name)
            if not cube and cube_name in declared_cubes:
                cube = next((i.payload for i in entity.items if i.object_type == "cube_model" and i.payload.get("name") == cube_name), None)
            if not cube:
                item_errors.append(f"Cube不存在: {cube_name}")
            else:
                measure_names = {entry.get("name") for entry in cube.get("measures") or []}
                dimension_map = {entry.get("name"): entry for entry in cube.get("dimensions") or []}
                local_measure = cube_measure.split(".")[-1]
                if not cube_measure or local_measure not in measure_names:
                    item_errors.append(f"Cube度量不存在: {cube_measure}")
                for dimension in payload.get("dimensions") or []:
                    if dimension.split(".")[-1] not in dimension_map:
                        item_errors.append(f"Cube维度不存在: {dimension}")
                time_dimension = str(payload.get("default_time_dimension") or "").strip()
                if time_dimension:
                    entry = dimension_map.get(time_dimension.split(".")[-1])
                    if not entry or entry.get("type") != "time":
                        item_errors.append(f"默认时间维度不存在或不是time类型: {time_dimension}")
            if payload.get("metric_type") in {"derived", "composite"} and not payload.get("calculation"):
                item_errors.append("派生指标和复合指标必须填写calculation")
            draft_metrics.add(code)
        elif item.object_type == "airflow_sql_dag":
            datasource_name = str(payload.get("datasource_name") or "").strip()
            if datasource_types.get(datasource_name) != "doris":
                item_errors.append(f"调度任务必须选择已启用的Doris数据源: {datasource_name}")
            try:
                validated_dag = validate_dag_payload(payload)
                if validated_dag["dag_id"] in existing_dag_ids:
                    item_errors.append(f"Airflow DAG编码已存在: {validated_dag['dag_id']}")
                if any(
                    str((other.payload or {}).get("dag_id") or "").strip() == validated_dag["dag_id"]
                    for other in entity.items if other.id != item.id and other.object_type == "airflow_sql_dag"
                ):
                    item_errors.append(f"变更集中DAG编码重复: {validated_dag['dag_id']}")
            except ValueError as exc:
                item_errors.append(str(exc))
        elif item.object_type == "data_service_api":
            service_code = str(payload.get("service_code") or "").strip()
            try:
                request = DataServiceCreate.model_validate(payload)
                if request.method.upper() not in {"GET", "POST"}:
                    item_errors.append("method必须是GET或POST")
                if service_code in existing_service_codes or service_code in draft_service_codes:
                    item_errors.append(f"数据服务编码重复: {service_code}")
                if request.datasource_id:
                    source = (await db.execute(select(DataSource).where(
                        DataSource.id == uuid.UUID(request.datasource_id), DataSource.status == "active",
                    ))).scalar_one_or_none()
                    if not source:
                        item_errors.append("数据源不存在或未启用")
                if request.service_type == "custom_sql":
                    validate_read_only_sql(request.sql_template)
                    declared = {str(entry.get("name") or "") for entry in request.parameters}
                    placeholders = set(re.findall(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", request.sql_template))
                    missing = placeholders - declared
                    if missing:
                        item_errors.append(f"SQL参数未声明: {', '.join(sorted(missing))}")
                if request.service_type == "metric":
                    metric_ids = []
                    for value in request.metric_ids:
                        try:
                            metric_ids.append(uuid.UUID(str(value)))
                        except ValueError:
                            item_errors.append(f"指标ID格式错误: {value}")
                    if metric_ids:
                        found = set((await db.execute(select(MetricDefinition.id).where(
                            MetricDefinition.id.in_(metric_ids), MetricDefinition.status.in_(["published", "active"]),
                        ))).scalars().all())
                        if len(found) != len(set(metric_ids)):
                            item_errors.append("指标服务包含不存在或未发布的指标")
            except (ValueError, TypeError) as exc:
                item_errors.append(f"数据服务配置无效: {exc}")
            draft_service_codes.add(service_code)
        elif item.object_type == "quality_rule":
            asset_id = str(payload.get("asset_id") or "").strip()
            rule_name = str(payload.get("rule_name") or "").strip()
            rule_type = str(payload.get("rule_type") or "").strip()
            column_name = str(payload.get("column_name") or "").strip() or None
            config = payload.get("config") or {}
            try:
                asset_uuid = uuid.UUID(asset_id)
            except ValueError:
                asset_uuid = None
                item_errors.append("asset_id格式错误")
            asset = None
            if asset_uuid:
                asset = (await db.execute(select(AssetObject).where(
                    AssetObject.id == asset_uuid, AssetObject.status == "active",
                    AssetObject.asset_type == "table",
                ))).scalar_one_or_none()
                if not asset:
                    item_errors.append("物理表资产不存在或未启用")
                elif rule_name and (await db.execute(select(QualityRule.id).where(
                    QualityRule.asset_id == asset_uuid, QualityRule.rule_name == rule_name,
                ).limit(1))).scalar_one_or_none():
                    item_errors.append("同一资产下的质量规则名称已存在")
            if not rule_name:
                item_errors.append("rule_name不能为空")
            if rule_type not in {"not_null", "unique", "range", "custom_sql"}:
                item_errors.append("rule_type必须是not_null/unique/range/custom_sql之一")
            if rule_type in {"not_null", "unique", "range"}:
                if not column_name:
                    item_errors.append("字段级质量规则必须选择字段")
                elif asset and column_name not in {column.name for column in asset.columns}:
                    item_errors.append(f"字段不属于所选资产: {column_name}")
            if rule_type == "range":
                try:
                    minimum, maximum = float(config["min"]), float(config["max"])
                    if minimum > maximum:
                        item_errors.append("范围检查的最小值不能大于最大值")
                except (KeyError, TypeError, ValueError):
                    item_errors.append("范围检查必须配置数值型min和max")
            if rule_type == "custom_sql":
                try:
                    validate_read_only_sql(str(config.get("sql") or ""))
                except ValueError as exc:
                    item_errors.append(f"自定义质量SQL校验失败: {exc}")
            identity = (asset_id, rule_name)
            if identity in draft_quality_rules:
                item_errors.append("变更集中同一资产的质量规则名称重复")
            draft_quality_rules.add(identity)
        item.validation_result = {"passed": not item_errors, "errors": item_errors}
        errors.extend({"item_id": str(item.id), "message": message} for message in item_errors)

    passed = not errors and bool(entity.items)
    if not entity.items:
        errors.append({"item_id": None, "message": "变更集没有任何变更项"})
    result = {"passed": passed, "errors": errors, "warnings": warnings, "item_count": len(entity.items)}
    entity.validation_status = "passed" if passed else "failed"
    entity.validation_result = result
    await db.commit()
    return result


async def commit_change_set(db: AsyncSession, principal: dict, change_set_id: uuid.UUID) -> dict:
    entity = await _owned_change_set(db, principal, change_set_id, include_items=True)
    if entity.status != "draft":
        raise ValueError("变更集已经提交或废弃")
    validation = await validate_change_set(db, principal, change_set_id)
    if not validation["passed"]:
        raise ValueError("变更集校验未通过")
    entity = await _owned_change_set(db, principal, change_set_id, include_items=True)
    created: list[dict] = []
    domain_names = dict((await db.execute(select(DataDomain.domain_code, DataDomain.domain_name))).all())
    process_names = dict((await db.execute(select(BusinessDomain.domain_code, BusinessDomain.domain_name))).all())

    category_ids = dict((await db.execute(select(MetricCategory.category_code, MetricCategory.id))).all())
    created_cubes: list[str] = []
    created_dags: list[str] = []
    order = {
        "data_domain": 1, "business_process": 2, "data_model": 3, "sql_script": 4,
        "metric_category": 5, "cube_model": 6, "metric_definition": 7,
        "airflow_sql_dag": 8, "data_service_api": 9, "quality_rule": 10,
    }
    for item in sorted(entity.items, key=lambda value: (order[value.object_type], value.sort_order)):
        payload = item.payload
        if item.object_type == "data_domain":
            obj = DataDomain(
                domain_name=payload["domain_name"], domain_code=payload["domain_code"],
                description=payload.get("description"), sort_order=int(payload.get("sort_order") or 0),
            )
            db.add(obj); await db.flush(); domain_names[obj.domain_code] = obj.domain_name
        elif item.object_type == "business_process":
            obj = BusinessDomain(
                domain_name=payload["process_name"], domain_code=payload["process_code"],
                data_domain=domain_names.get(payload.get("data_domain_code")),
                description=payload.get("description"), sort_order=int(payload.get("sort_order") or 0),
            )
            db.add(obj); await db.flush(); process_names[obj.domain_code] = obj.domain_name
        elif item.object_type == "data_model":
            obj = DataModel(
                model_name=payload["model_name"], model_code=payload["model_code"],
                layer=payload["layer"], database=payload["database"], table_name=payload["table_name"],
                description=payload.get("description"), etl_sql=payload.get("etl_sql"),
                data_domain=domain_names.get(payload.get("data_domain_code")),
                business_domain=process_names.get(payload.get("business_process_code")),
                model_grain=payload.get("model_grain"), update_strategy=payload.get("update_strategy"),
                source_tables=payload.get("source_tables") or [], is_external=bool(payload.get("is_external", False)),
                status="draft", created_by=principal["user_id"],
            )
            db.add(obj); await db.flush()
            fields = [DataModelFieldItem.model_validate(field) for field in payload.get("fields") or []]
            for field in fields:
                db.add(DataModelField(model_id=obj.id, **field.model_dump()))
            db.add(DataModelVersion(
                model_id=obj.id, version=1, table_ddl=_generate_ddl(obj, fields),
                field_snapshot=[field.model_dump() for field in fields], change_log="Created through MCP change set",
                created_by=principal["user_id"],
            ))
        elif item.object_type == "sql_script":
            obj = EtlScript(
                script_name=payload["script_name"], script_code=payload["script_code"],
                language="sql", content=validate_read_only_sql(payload["content"]),
                description=payload.get("description"), created_by=principal["user_id"],
            )
            db.add(obj); await db.flush()
        elif item.object_type == "metric_category":
            obj = MetricCategory(
                category_name=payload["category_name"], category_code=payload["category_code"],
                description=payload.get("description"), sort_order=int(payload.get("sort_order") or 0),
            )
            db.add(obj); await db.flush(); category_ids[obj.category_code] = obj.id
        elif item.object_type == "cube_model":
            result = cube_model_service.save_cube(payload)
            created_cubes.append(payload["name"])
            item.object_id = None
            created.append({"object_type": item.object_type, "object_id": payload["name"], "file": result["file"]})
            continue
        elif item.object_type == "metric_definition":
            obj = MetricDefinition(
                metric_code=payload["metric_code"], metric_name=payload["metric_name"],
                metric_type=payload["metric_type"], cube_name=payload["cube_name"],
                cube_measure=payload["cube_measure"], category_id=category_ids.get(payload.get("category_code")),
                dimensions=payload.get("dimensions") or [],
                default_time_dimension=payload.get("default_time_dimension"), calculation=payload.get("calculation"),
                business_domain=payload.get("business_domain"), unit=payload.get("unit"),
                description=payload.get("description"), status="draft",
            )
            db.add(obj); await db.flush()
        elif item.object_type == "airflow_sql_dag":
            result = await airflow_service.create_dag_file(
                db, payload["dag_id"], render_airflow_dag(payload),
            )
            item.object_id = None
            created_dags.append(payload["dag_id"])
            created.append({
                "object_type": item.object_type, "object_id": payload["dag_id"],
                "file": result["fileloc"], "paused_upon_creation": True,
            })
            continue
        elif item.object_type == "data_service_api":
            request = DataServiceCreate.model_validate(payload)
            obj = DataServiceApi(
                api_name=request.api_name, service_code=request.service_code,
                service_type=request.service_type,
                api_path=request.api_path or f"/open-api/v1/{request.service_code}",
                method=request.method.upper(), description=request.description,
                sql_template=request.sql_template, parameters=request.parameters,
                datasource_id=uuid.UUID(request.datasource_id) if request.datasource_id else None,
                database=request.database, table_name=request.table_name,
                selected_fields=request.selected_fields, filter_fields=request.filter_fields,
                metric_ids=request.metric_ids, metric_dimensions=request.metric_dimensions,
                time_dimension=request.time_dimension, default_granularity=request.default_granularity,
                max_rows=request.max_rows, cache_enabled=request.cache_enabled,
                cache_ttl=request.cache_ttl, status="draft", created_by=principal["user_id"],
            )
            db.add(obj); await db.flush()
        else:
            obj = QualityRule(
                asset_id=uuid.UUID(payload["asset_id"]), rule_name=payload["rule_name"],
                rule_type=payload["rule_type"], column_name=payload.get("column_name") or None,
                config=payload.get("config") or {}, enabled=bool(payload.get("enabled", True)),
                created_by=principal["user_id"],
            )
            db.add(obj); await db.flush()
        item.object_id = obj.id
        created.append({"object_type": item.object_type, "object_id": str(obj.id)})
    entity.status = "committed"
    entity.committed_at = datetime.now(timezone.utc)
    await db.commit()
    return {
        "success": True, "change_set_id": str(entity.id), "status": entity.status,
        "created": created, "cube_refresh_required": bool(created_cubes),
        "cube_models_pending_refresh": created_cubes,
        "airflow_activation_required": bool(created_dags),
        "airflow_dags_pending_activation": created_dags,
        "data_services_pending_publish": [
            item["object_id"] for item in created if item["object_type"] == "data_service_api"
        ],
        "quality_rules_pending_execution": [
            item["object_id"] for item in created if item["object_type"] == "quality_rule"
        ],
    }


async def discard_change_set(db: AsyncSession, principal: dict, change_set_id: uuid.UUID) -> dict:
    entity = await _owned_change_set(db, principal, change_set_id)
    if entity.status != "draft":
        raise ValueError("只有草稿变更集可以废弃")
    entity.status = "discarded"
    await db.commit()
    return {"success": True, "change_set_id": str(entity.id), "status": entity.status}


async def record_tool_call(
    db: AsyncSession, principal: dict, tool_name: str, arguments: dict,
    status: str, started_at: float, result_summary: str | None = None,
    change_set_id: uuid.UUID | None = None,
) -> None:
    db.add(McpToolCall(
        client_id=principal.get("client_id"), user_id=principal.get("user_id"),
        change_set_id=change_set_id, tool_name=tool_name, arguments_json=arguments,
        status=status, elapsed_ms=int((time.perf_counter() - started_at) * 1000),
        result_summary=(result_summary or "")[:2000],
    ))
    await db.commit()


async def list_tool_calls(db: AsyncSession, limit: int = 100) -> list[dict]:
    rows = (await db.execute(select(McpToolCall).order_by(McpToolCall.created_at.desc()).limit(limit))).scalars().all()
    return [{
        "id": str(row.id), "client_id": str(row.client_id) if row.client_id else None,
        "user_id": str(row.user_id) if row.user_id else None, "tool_name": row.tool_name,
        "status": row.status, "elapsed_ms": row.elapsed_ms, "arguments": row.arguments_json,
        "result_summary": row.result_summary, "created_at": row.created_at.isoformat(),
    } for row in rows]


async def list_change_sets_admin(
    db: AsyncSession, status: str | None = None, limit: int = 200,
) -> list[dict]:
    query = (
        select(McpChangeSet, McpClient)
        .join(McpClient, McpChangeSet.client_id == McpClient.id)
        .order_by(McpChangeSet.created_at.desc())
        .limit(limit)
    )
    if status:
        query = query.where(McpChangeSet.status == status)
    rows = (await db.execute(query)).all()
    result = []
    for entity, client in rows:
        data = _change_set_dict(entity)
        data.update({
            "client_name": client.client_name, "client_code": client.client_code,
            "item_count": (await db.execute(select(func.count(McpChangeSetItem.id)).where(
                McpChangeSetItem.change_set_id == entity.id
            ))).scalar_one(),
        })
        result.append(data)
    return result


async def get_change_set_admin(db: AsyncSession, change_set_id: uuid.UUID) -> dict | None:
    row = (await db.execute(
        select(McpChangeSet, McpClient)
        .join(McpClient, McpChangeSet.client_id == McpClient.id)
        .where(McpChangeSet.id == change_set_id)
        .options(selectinload(McpChangeSet.items))
    )).first()
    if not row:
        return None
    entity, client = row
    data = _change_set_dict(entity, include_items=True)
    data.update({"client_name": client.client_name, "client_code": client.client_code})
    return data


async def validate_change_set_admin(
    db: AsyncSession, change_set_id: uuid.UUID, user_id: uuid.UUID,
) -> dict:
    entity = (await db.execute(select(McpChangeSet).where(McpChangeSet.id == change_set_id))).scalar_one_or_none()
    if not entity:
        raise ValueError("变更集不存在")
    if entity.status != "draft":
        raise ValueError("只有草稿变更集可以重新校验")
    return await validate_change_set(db, {"client_id": entity.client_id, "user_id": user_id}, change_set_id)


async def commit_change_set_admin(
    db: AsyncSession, change_set_id: uuid.UUID, user_id: uuid.UUID,
) -> dict:
    entity = (await db.execute(select(McpChangeSet).where(McpChangeSet.id == change_set_id))).scalar_one_or_none()
    if not entity:
        raise ValueError("变更集不存在")
    return await commit_change_set(db, {"client_id": entity.client_id, "user_id": user_id}, change_set_id)


async def discard_change_set_admin(
    db: AsyncSession, change_set_id: uuid.UUID, user_id: uuid.UUID,
) -> dict:
    entity = (await db.execute(select(McpChangeSet).where(McpChangeSet.id == change_set_id))).scalar_one_or_none()
    if not entity:
        raise ValueError("变更集不存在")
    return await discard_change_set(db, {"client_id": entity.client_id, "user_id": user_id}, change_set_id)


async def _owned_change_set(db, principal, change_set_id, include_items=False):
    query = select(McpChangeSet).where(
        McpChangeSet.id == change_set_id, McpChangeSet.client_id == principal["client_id"],
    )
    if include_items:
        query = query.options(selectinload(McpChangeSet.items))
    entity = (await db.execute(query)).scalar_one_or_none()
    if not entity:
        raise ValueError("变更集不存在或不属于当前MCP客户端")
    return entity


def _client_dict(entity: McpClient) -> dict:
    return {
        "id": str(entity.id), "client_name": entity.client_name, "client_code": entity.client_code,
        "service_user_id": str(entity.service_user_id), "scopes": entity.scopes or [], "status": entity.status,
        "last_connected_at": entity.last_connected_at.isoformat() if entity.last_connected_at else None,
        "created_at": entity.created_at.isoformat() if entity.created_at else None,
    }


def _change_set_dict(entity: McpChangeSet, include_items=False) -> dict:
    data = {
        "id": str(entity.id), "change_set_code": entity.change_set_code, "title": entity.title,
        "description": entity.description, "status": entity.status,
        "validation_status": entity.validation_status, "validation_result": entity.validation_result or {},
        "created_at": entity.created_at.isoformat() if entity.created_at else None,
    }
    if include_items:
        data["items"] = [{
            "id": str(item.id), "object_type": item.object_type, "action": item.action,
            "object_id": str(item.object_id) if item.object_id else None, "payload": item.payload,
            "validation_result": item.validation_result,
        } for item in entity.items]
    return data


def _safe_identifier(value: str) -> bool:
    import re
    return bool(value and re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", value))


def _safe_cube_identifier(value: str) -> bool:
    import re
    return bool(value and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value))


def _validate_cube_entries(
    entries: list[dict], label: str, allowed_types: set[str], allow_count_without_sql: bool = False,
) -> list[str]:
    errors: list[str] = []
    names: set[str] = set()
    for entry in entries:
        name = str(entry.get("name") or "").strip()
        entry_type = str(entry.get("type") or "").strip()
        if not _safe_cube_identifier(name):
            errors.append(f"{label}名称不能为空且仅支持字母、数字和下划线")
        if name in names:
            errors.append(f"{label}名称重复: {name}")
        names.add(name)
        if entry_type not in allowed_types:
            errors.append(f"{label}{name}的type不受支持: {entry_type}")
        if not entry.get("sql") and not (allow_count_without_sql and entry_type == "count"):
            errors.append(f"{label}{name}缺少sql表达式")
        if "`" in str(entry.get("sql") or "") or "`" in str(entry.get("title") or ""):
            errors.append(f"{label}{name}不能包含反引号")
    return errors


def _validate_cube_links(entries: list[dict], label: str, require_relationship: bool = False) -> list[str]:
    errors: list[str] = []
    names: set[str] = set()
    relationships = {"one_to_one", "one_to_many", "many_to_one"}
    for entry in entries:
        name = str(entry.get("name") or "").strip()
        if not _safe_cube_identifier(name):
            errors.append(f"{label}名称不能为空且仅支持字母、数字和下划线")
        if name in names:
            errors.append(f"{label}名称重复: {name}")
        names.add(name)
        if not entry.get("sql"):
            errors.append(f"{label}{name}缺少sql表达式")
        if require_relationship and entry.get("relationship") not in relationships:
            errors.append(f"{label}{name}的relationship必须是one_to_one/one_to_many/many_to_one之一")
        if any("`" in str(entry.get(key) or "") for key in ("sql", "title", "relationship")):
            errors.append(f"{label}{name}不能包含反引号")
    return errors
