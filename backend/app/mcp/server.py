"""DataMind MCP resources, tools and prompts."""
import contextlib
import inspect
import json
import re
import time
import uuid
from datetime import datetime

from mcp.server.fastmcp import FastMCP
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from app.core.database import async_session
from app.mcp.auth import McpBearerAuthMiddleware
from app.mcp.context import require_principal
from app.models import AirflowDagRun, BusinessDomain, DataDomain, DataModel, DataServiceApi, DataSource, EtlScript, MetricCategory, MetricDefinition, QualityRule
from app.schemas.data_service import DataServiceCreate
from app.services import airflow_service, cube_model_service, data_asset_service, data_model_service, data_service, datasource_service, etl_script_service, mcp_service, metric_category_service, metric_definition_service
from app.utils.sql_safety import validate_read_only_sql


mcp = FastMCP(
    "DataMind",
    instructions=(
        "DataMind enterprise data platform. Read platform resources before creating changes. "
        "All modeling, SQL development and metric writes must use a change set, validate it, show the user the result, "
        "and call commit_change_set only after explicit user confirmation."
    ),
    stateless_http=False,
    json_response=True,
)


_TOOL_DESCRIPTIONS_ZH = {
    "get_platform_overview": "获取DataMind平台的数据域、模型、指标、Cube和数据服务等总体数量。",
    "list_data_domains": "查询全部数据域及其编码、名称和说明。",
    "list_business_processes": "查询业务过程，可按所属数据域筛选。",
    "list_data_models": "查询数据模型设计，可按分层和关键字筛选。",
    "get_data_model": "查看单个数据模型的字段、版本和完整设计信息。",
    "list_datasources": "查询已启用数据源的真实名称和标识，不返回连接密码。",
    "list_datasource_tables": "从指定数据源加载可选择的物理表。",
    "list_table_columns": "加载指定物理表的字段结构，供建模和Cube配置使用。",
    "list_sql_scripts": "查询已保存的SQL开发脚本，不执行SQL。",
    "get_sql_script": "查看单个SQL开发脚本的完整内容。",
    "list_metric_categories": "查询指标分类及其编码。",
    "list_cube_models": "查询Cube模型及真实数据源、维度、度量和时间维度。",
    "get_cube_model": "查看单个Cube模型的完整配置。",
    "refresh_cube": "重启Cube服务并加载已提交的Cube模型，操作前需要人工确认。",
    "list_metric_definitions": "查询原子指标、派生指标和复合指标定义。",
    "preview_sql": "在指定数据源执行单条只读SQL预览，最多返回200行。",
    "list_airflow_dags": "查询Airflow DAG及其启停状态。",
    "get_airflow_dag": "查看单个Airflow DAG的定义和当前状态。",
    "set_airflow_dag_paused": "暂停或启用Airflow DAG，操作前需要人工确认。",
    "trigger_airflow_dag": "手动触发Airflow DAG运行，操作前需要人工确认。",
    "list_airflow_dag_runs": "查询指定DAG最近的运行记录。",
    "get_airflow_run_detail": "查看DAG运行详情及全部任务实例状态。",
    "get_airflow_task_log": "读取指定任务实例的有限长度运行日志。",
    "sync_runtime_lineage": "同步Airflow运行记录并采集任务级运行血缘，需要人工确认。",
    "list_runtime_lineage_runs": "查询DataMind已记录的DAG运行和血缘采集状态。",
    "get_runtime_lineage_tasks": "查看一次DAG运行中各任务的SQL、输入表、输出表和错误。",
    "list_data_services": "查询数据服务目录，可按草稿、已发布或已停用状态筛选。",
    "get_data_service": "查看单个数据API的参数、数据源和生命周期状态。",
    "preview_data_service": "预览执行草稿或已发布的数据API，审计中不保存参数值和结果行。",
    "set_data_service_status": "发布或停用数据API，操作前需要人工确认。",
    "list_data_service_app_keys": "查询数据API的AppKey元数据和状态，不返回密钥明文。",
    "create_data_service_app_key": "为已发布数据API生成只展示一次的AppKey，需要人工确认。",
    "revoke_data_service_app_key": "撤销数据API的AppKey，需要人工确认。",
    "list_data_service_call_logs": "查询数据API调用日志，不返回请求参数值。",
    "get_data_service_call_stats": "查询数据API调用量、成功数、失败数、耗时和每日趋势。",
    "get_data_asset_overview": "获取物理表、字段、运行血缘和质量规则数量。",
    "list_data_assets": "搜索物理表数据目录，不包含逻辑模型。",
    "get_data_asset": "查看物理表字段以及血缘和质量规则数量。",
    "sync_data_catalog": "同步物理表和字段元数据，操作前需要人工确认。",
    "list_asset_runtime_lineage": "查询成功调度任务实际产生的表级运行血缘。",
    "list_quality_rules": "查询质量规则及最近一次检测结果。",
    "run_quality_rule": "执行质量规则并保存检测结果，操作前需要人工确认。",
    "delete_quality_rule": "永久删除质量规则，操作前需要人工确认。",
    "create_change_set": "创建隔离的MCP变更集，后续写操作先进入该变更集。",
    "create_data_domain_draft": "在变更集中新增数据域草稿。",
    "create_business_process_draft": "在变更集中新增业务过程草稿。",
    "create_data_model_draft": "在变更集中新增数据模型和字段设计草稿。",
    "create_sql_script_draft": "在变更集中新增只读SQL脚本草稿。",
    "create_metric_category_draft": "在变更集中新增指标分类草稿。",
    "create_cube_model_draft": "在变更集中新增使用真实数据源的Cube模型草稿。",
    "create_metric_definition_draft": "在变更集中新增原子、派生或复合指标草稿。",
    "create_airflow_sql_dag_draft": "在变更集中新增INSERT INTO SELECT类型的Airflow SQL任务草稿。",
    "create_data_service_draft": "在变更集中新增物理表、自定义SQL或指标数据API草稿。",
    "create_quality_rule_draft": "在变更集中新增非空、唯一、范围或自定义SQL质量规则草稿。",
    "get_change_set": "查看变更集的全部草稿内容和校验结果。",
    "validate_change_set": "校验变更集中的依赖、配置和安全规则，不写入业务对象。",
    "discard_change_set": "废弃尚未提交的变更集，不修改业务对象。",
    "commit_change_set": "经人工确认后提交已校验的变更集。",
}


def _tool_module(name: str) -> str:
    if "data_service" in name:
        return "数据服务"
    if "quality" in name:
        return "数据质量"
    if "asset" in name or "catalog" in name:
        return "数据目录"
    if "runtime_lineage" in name:
        return "血缘关系"
    if "airflow" in name:
        return "调度中心"
    if "metric" in name or "cube" in name:
        return "指标建设"
    if "sql" in name:
        return "数据开发"
    if "data_domain" in name or "business_process" in name or "data_model" in name:
        return "数据建模"
    if "change_set" in name:
        return "变更集"
    if "datasource" in name or "table_columns" in name:
        return "元数据"
    return "平台概览"


async def build_tool_catalog() -> dict:
    """Build an always-current management catalog from the live FastMCP registry."""
    result = []
    for item in await mcp.list_tools():
        registered = mcp._tool_manager.get_tool(item.name)
        source = inspect.getsource(registered.fn)
        scope_match = re.search(
            r"_run_tool\(\s*['\"][^'\"]+['\"]\s*,\s*['\"]([^'\"]+)['\"]",
            source, re.DOTALL,
        )
        schema = item.inputSchema or {}
        properties = schema.get("properties") or {}
        confirmation_required = "user_confirmation" in properties
        writes_draft = item.name == "create_change_set" or item.name.endswith("_draft")
        executes_read = item.name in {"preview_sql", "preview_data_service"}
        risk_level = "high" if confirmation_required else "medium" if writes_draft or executes_read else "low"
        result.append({
            "name": item.name,
            "module": _tool_module(item.name),
            "description": _TOOL_DESCRIPTIONS_ZH.get(item.name, "待补充中文功能说明"),
            "scope": scope_match.group(1) if scope_match else "",
            "risk_level": risk_level,
            "confirmation_required": confirmation_required,
            "parameters": [{
                "name": name,
                "type": definition.get("type") or "object",
                "required": name in set(schema.get("required") or []),
                "description": definition.get("description") or "",
                "default": definition.get("default"),
            } for name, definition in properties.items()],
        })
    result.sort(key=lambda value: (value["module"], value["name"]))
    modules = sorted({item["module"] for item in result})
    return {"items": result, "total": len(result), "modules": modules}


async def _run_tool(name: str, scope: str, arguments: dict, operation):
    principal = require_principal(scope)
    started = time.perf_counter()
    change_set_value = arguments.get("change_set_id")
    change_set_id = uuid.UUID(change_set_value) if change_set_value else None
    audit_arguments = arguments
    if name == "preview_data_service":
        audit_arguments = {**arguments, "parameter_names": sorted((arguments.get("params") or {}).keys())}
        audit_arguments.pop("params", None)
    async with async_session() as db:
        try:
            result = await operation(db, principal)
            audit_result = result
            if name in {"preview_sql", "preview_data_service"} and isinstance(result, dict):
                audit_result = {key: value for key, value in result.items() if key != "rows"}
            elif name == "get_airflow_task_log" and isinstance(result, dict):
                audit_result = {key: value for key, value in result.items() if key != "log"}
            elif name == "create_data_service_app_key" and isinstance(result, dict):
                audit_result = {key: value for key, value in result.items() if key != "app_key"}
            await mcp_service.record_tool_call(
                db, principal, name, audit_arguments, "success", started,
                json.dumps(audit_result, ensure_ascii=False, default=str)[:2000], change_set_id,
            )
            return result
        except Exception as exc:
            await db.rollback()
            await mcp_service.record_tool_call(
                db, principal, name, audit_arguments, "failed", started, str(exc), change_set_id,
            )
            raise


@mcp.resource("datamind://platform/overview")
async def platform_overview_resource() -> str:
    """Current counts and capabilities of the DataMind platform."""
    require_principal("metadata:read")
    async with async_session() as db:
        data = {
            "data_domains": (await db.execute(select(func.count(DataDomain.id)))).scalar_one(),
            "business_processes": (await db.execute(select(func.count(BusinessDomain.id)))).scalar_one(),
            "data_models": (await db.execute(select(func.count(DataModel.id)))).scalar_one(),
            "datasources": (await db.execute(select(func.count(DataSource.id)))).scalar_one(),
            "supported_change_objects": [
                "data_domain", "business_process", "data_model", "sql_script",
                "metric_category", "cube_model", "metric_definition", "airflow_sql_dag",
                "data_service_api", "quality_rule",
            ],
        }
    return json.dumps(data, ensure_ascii=False)


@mcp.resource("datamind://modeling/data-domains")
async def data_domains_resource() -> str:
    """All data domains available for model design."""
    require_principal("modeling:read")
    async with async_session() as db:
        rows = (await db.execute(select(DataDomain).order_by(DataDomain.sort_order, DataDomain.domain_name))).scalars().all()
        data = [{"id": str(row.id), "code": row.domain_code, "name": row.domain_name, "description": row.description} for row in rows]
    return json.dumps(data, ensure_ascii=False)


@mcp.resource("datamind://modeling/business-processes")
async def business_processes_resource() -> str:
    """All business processes and their owning data domains."""
    require_principal("modeling:read")
    async with async_session() as db:
        rows = (await db.execute(select(BusinessDomain).order_by(BusinessDomain.sort_order, BusinessDomain.domain_name))).scalars().all()
        data = [{
            "id": str(row.id), "code": row.domain_code, "name": row.domain_name,
            "data_domain": row.data_domain, "description": row.description,
        } for row in rows]
    return json.dumps(data, ensure_ascii=False)


@mcp.resource("datamind://modeling/models/{model_id}")
async def data_model_resource(model_id: str) -> str:
    """A complete data model with fields and version metadata."""
    require_principal("modeling:read")
    async with async_session() as db:
        model = await data_model_service.get_model(db, uuid.UUID(model_id))
    if not model:
        raise ValueError("Data model not found")
    return json.dumps(model, ensure_ascii=False, default=str)


@mcp.resource("datamind://platform/datasources")
async def datasources_resource() -> str:
    """Active datasource identifiers and real names without connection secrets."""
    require_principal("metadata:read")
    async with async_session() as db:
        rows = (await db.execute(
            select(DataSource).where(DataSource.status == "active").order_by(DataSource.source_name)
        )).scalars().all()
    return json.dumps([{
        "id": str(row.id), "source_name": row.source_name, "source_type": row.source_type,
        "database_name": row.database_name, "default_schema": row.default_schema,
    } for row in rows], ensure_ascii=False)


@mcp.resource("datamind://development/sql-scripts")
async def sql_scripts_resource() -> str:
    """Saved read-only SQL development scripts."""
    require_principal("development:read")
    async with async_session() as db:
        items, total = await etl_script_service.list_scripts(db, 1, 200)
    return json.dumps({"items": items, "total": total}, ensure_ascii=False)


@mcp.resource("datamind://metrics/catalog")
async def metrics_catalog_resource() -> str:
    """Metric categories, Cube models and metric definitions."""
    require_principal("metrics:read")
    async with async_session() as db:
        categories = await metric_category_service.list_categories(db)
        definitions, total = await metric_definition_service.list_definitions(db, 1, 500)
    return json.dumps({
        "categories": categories, "cubes": cube_model_service.list_models()["cubes"],
        "metric_definitions": definitions, "metric_definition_total": total,
    }, ensure_ascii=False)


@mcp.resource("datamind://scheduling/runtime-lineage")
async def runtime_lineage_resource() -> str:
    """Recent Airflow runs and their runtime-lineage collection state."""
    require_principal("lineage:read")
    async with async_session() as db:
        items, total = await airflow_service.list_dag_runs_page(db, 1, 100)
    return json.dumps({"items": items, "total": total}, ensure_ascii=False)


@mcp.resource("datamind://data-service/catalog")
async def data_service_catalog_resource() -> str:
    """Data service catalog including draft, published and offline APIs."""
    require_principal("data_service:read")
    async with async_session() as db:
        items, total = await data_service.list_apis(db, 1, 500)
    return json.dumps({"items": items, "total": total}, ensure_ascii=False)


@mcp.resource("datamind://assets/catalog")
async def asset_catalog_resource() -> str:
    """Physical table catalog with field counts and real datasource names."""
    require_principal("catalog:read")
    async with async_session() as db:
        items, total = await data_asset_service.list_assets(db, 1, 500)
    return json.dumps({"items": items, "total": total}, ensure_ascii=False)


@mcp.resource("datamind://assets/quality")
async def asset_quality_resource() -> str:
    """Quality rules and their latest execution results."""
    require_principal("quality:read")
    async with async_session() as db:
        items = await data_asset_service.list_quality_rules(db)
    return json.dumps({"items": items, "total": len(items)}, ensure_ascii=False)


@mcp.tool()
async def get_platform_overview() -> dict:
    """Return DataMind modeling counts and supported MCP change objects."""
    async def operation(db, principal):
        return {
            "data_domains": (await db.execute(select(func.count(DataDomain.id)))).scalar_one(),
            "business_processes": (await db.execute(select(func.count(BusinessDomain.id)))).scalar_one(),
            "data_models": (await db.execute(select(func.count(DataModel.id)))).scalar_one(),
            "datasources": (await db.execute(select(func.count(DataSource.id)))).scalar_one(),
            "sql_scripts": (await db.execute(select(func.count(EtlScript.id)))).scalar_one(),
            "metric_categories": (await db.execute(select(func.count(MetricCategory.id)))).scalar_one(),
            "metric_definitions": (await db.execute(select(func.count(MetricDefinition.id)))).scalar_one(),
            "cube_models": len(cube_model_service.list_models()["cubes"]),
            "data_services": (await db.execute(select(func.count(DataServiceApi.id)))).scalar_one(),
        }
    return await _run_tool("get_platform_overview", "metadata:read", {}, operation)


@mcp.tool()
async def list_data_domains() -> dict:
    """List stable identifiers, names and descriptions of all data domains."""
    async def operation(db, principal):
        rows = (await db.execute(select(DataDomain).order_by(DataDomain.sort_order))).scalars().all()
        return {"items": [{"id": str(row.id), "domain_code": row.domain_code, "domain_name": row.domain_name, "description": row.description} for row in rows]}
    return await _run_tool("list_data_domains", "modeling:read", {}, operation)


@mcp.tool()
async def list_business_processes(data_domain: str | None = None) -> dict:
    """List business processes, optionally filtered by owning data-domain name."""
    async def operation(db, principal):
        query = select(BusinessDomain).order_by(BusinessDomain.sort_order)
        if data_domain:
            query = query.where(BusinessDomain.data_domain == data_domain)
        rows = (await db.execute(query)).scalars().all()
        return {"items": [{
            "id": str(row.id), "process_code": row.domain_code, "process_name": row.domain_name,
            "data_domain": row.data_domain, "description": row.description,
        } for row in rows]}
    args = {"data_domain": data_domain}
    return await _run_tool("list_business_processes", "modeling:read", args, operation)


@mcp.tool()
async def list_data_models(layer: str | None = None, keyword: str | None = None, limit: int = 50) -> dict:
    """List model designs with fields, domain, process, layer and draft/published status."""
    async def operation(db, principal):
        items, total = await data_model_service.list_models(db, 1, min(max(limit, 1), 100), layer=layer, keyword=keyword)
        return {"items": items, "total": total}
    args = {"layer": layer, "keyword": keyword, "limit": limit}
    return await _run_tool("list_data_models", "modeling:read", args, operation)


@mcp.tool()
async def get_data_model(model_id: str) -> dict:
    """Get one model design including its fields and version history."""
    async def operation(db, principal):
        result = await data_model_service.get_model(db, uuid.UUID(model_id))
        if not result:
            raise ValueError("Data model not found")
        return result
    return await _run_tool("get_data_model", "modeling:read", {"model_id": model_id}, operation)


@mcp.tool()
async def list_datasources() -> dict:
    """List active datasource IDs and real names without passwords, hosts or usernames."""
    async def operation(db, principal):
        rows = (await db.execute(
            select(DataSource).where(DataSource.status == "active").order_by(DataSource.source_name)
        )).scalars().all()
        return {"items": [{
            "id": str(row.id), "source_name": row.source_name, "source_type": row.source_type,
            "database_name": row.database_name, "default_schema": row.default_schema,
        } for row in rows]}
    return await _run_tool("list_datasources", "metadata:read", {}, operation)


@mcp.tool()
async def list_datasource_tables(
    datasource_id: str, schema: str | None = None, database: str | None = None,
) -> dict:
    """Load selectable physical tables from a DataMind datasource."""
    async def operation(db, principal):
        source = await datasource_service.get_datasource(db, uuid.UUID(datasource_id))
        if not source or source["status"] != "active":
            raise ValueError("Datasource not found or inactive")
        tables = await datasource_service.list_tables(db, uuid.UUID(datasource_id), schema, database)
        return {"datasource": source["source_name"], "database": database or source["database_name"], "tables": tables}
    args = {"datasource_id": datasource_id, "schema": schema, "database": database}
    return await _run_tool("list_datasource_tables", "metadata:read", args, operation)


@mcp.tool()
async def list_table_columns(
    datasource_id: str, table_name: str, schema: str | None = None, database: str | None = None,
) -> dict:
    """Load physical table columns before configuring Cube dimensions and measures."""
    async def operation(db, principal):
        source = await datasource_service.get_datasource(db, uuid.UUID(datasource_id))
        if not source or source["status"] != "active":
            raise ValueError("Datasource not found or inactive")
        columns = await datasource_service.get_table_columns(
            db, uuid.UUID(datasource_id), table_name, schema, database,
        )
        return {
            "datasource": source["source_name"], "database": database or source["database_name"],
            "table_name": table_name, "columns": columns,
        }
    args = {"datasource_id": datasource_id, "table_name": table_name, "schema": schema, "database": database}
    return await _run_tool("list_table_columns", "metadata:read", args, operation)


@mcp.tool()
async def list_sql_scripts(keyword: str | None = None, limit: int = 50) -> dict:
    """List saved SQL development scripts without executing them."""
    async def operation(db, principal):
        items, total = await etl_script_service.list_scripts(db, 1, min(max(limit, 1), 100), keyword=keyword)
        return {"items": items, "total": total}
    args = {"keyword": keyword, "limit": limit}
    return await _run_tool("list_sql_scripts", "development:read", args, operation)


@mcp.tool()
async def get_sql_script(script_id: str) -> dict:
    """Get one saved SQL development script. This tool never executes SQL."""
    async def operation(db, principal):
        result = await etl_script_service.get_script(db, uuid.UUID(script_id))
        if not result:
            raise ValueError("SQL script not found")
        return result
    return await _run_tool("get_sql_script", "development:read", {"script_id": script_id}, operation)


@mcp.tool()
async def list_metric_categories() -> dict:
    """List metric category codes for metric-definition design."""
    async def operation(db, principal):
        return {"items": await metric_category_service.list_categories(db)}
    return await _run_tool("list_metric_categories", "metrics:read", {}, operation)


@mcp.tool()
async def list_cube_models() -> dict:
    """List Cube models with their real datasource, measures, dimensions and time dimensions."""
    async def operation(db, principal):
        return cube_model_service.list_models()
    return await _run_tool("list_cube_models", "metrics:read", {}, operation)


@mcp.tool()
async def get_cube_model(name: str) -> dict:
    """Get a Cube model used for building metric definitions."""
    async def operation(db, principal):
        result = cube_model_service.get_cube(name)
        if not result:
            raise ValueError("Cube model not found")
        return result
    return await _run_tool("get_cube_model", "metrics:read", {"name": name}, operation)


@mcp.tool()
async def refresh_cube(user_confirmation: bool = False) -> dict:
    """Restart Cube and load committed models after explicit user confirmation."""
    async def operation(db, principal):
        if not user_confirmation:
            raise ValueError("Explicit user confirmation is required before refreshing Cube")
        result = await cube_model_service.refresh_cube()
        if not result.get("ok"):
            raise RuntimeError(result.get("message") or "Cube refresh failed")
        return result
    return await _run_tool(
        "refresh_cube", "metrics:execute",
        {"user_confirmation": user_confirmation}, operation,
    )


@mcp.tool()
async def list_metric_definitions(
    keyword: str | None = None, metric_type: str | None = None, limit: int = 50,
) -> dict:
    """List atomic, derived and composite metric definitions."""
    async def operation(db, principal):
        items, total = await metric_definition_service.list_definitions(
            db, 1, min(max(limit, 1), 100), keyword=keyword, metric_type=metric_type,
        )
        return {"items": items, "total": total}
    args = {"keyword": keyword, "metric_type": metric_type, "limit": limit}
    return await _run_tool("list_metric_definitions", "metrics:read", args, operation)


@mcp.tool()
async def preview_sql(
    datasource_id: str, sql: str, database: str | None = None, limit: int = 100,
) -> dict:
    """Execute one read-only SELECT preview against a selected datasource, capped at 200 rows."""
    async def operation(db, principal):
        return await datasource_service.execute_query(
            db, uuid.UUID(datasource_id), sql, min(max(limit, 1), 200), database=database,
        )
    args = {"datasource_id": datasource_id, "sql": sql, "database": database, "limit": limit}
    return await _run_tool("preview_sql", "development:execute", args, operation)


@mcp.tool()
async def list_airflow_dags(limit: int = 100) -> dict:
    """List Airflow DAGs and paused state."""
    async def operation(db, principal):
        return {"items": await airflow_service.list_dags(db, limit=min(max(limit, 1), 500))}
    return await _run_tool("list_airflow_dags", "scheduling:read", {"limit": limit}, operation)


@mcp.tool()
async def get_airflow_dag(dag_id: str) -> dict:
    """Get an Airflow DAG definition and current paused state."""
    async def operation(db, principal):
        result = await airflow_service.get_dag(db, dag_id)
        if not result:
            raise ValueError("Airflow DAG not found")
        return result
    return await _run_tool("get_airflow_dag", "scheduling:read", {"dag_id": dag_id}, operation)


@mcp.tool()
async def set_airflow_dag_paused(
    dag_id: str, paused: bool, user_confirmation: bool = False,
) -> dict:
    """Pause or activate a DAG. Requires explicit confirmation because it changes scheduling state."""
    async def operation(db, principal):
        if not user_confirmation:
            raise ValueError("Explicit user confirmation is required before changing DAG state")
        result = await (airflow_service.pause_dag(db, dag_id) if paused else airflow_service.resume_dag(db, dag_id))
        if not result:
            raise ValueError("Airflow DAG not found or state update failed")
        return result
    args = {"dag_id": dag_id, "paused": paused, "user_confirmation": user_confirmation}
    return await _run_tool("set_airflow_dag_paused", "scheduling:write", args, operation)


@mcp.tool()
async def trigger_airflow_dag(
    dag_id: str, conf: dict | None = None, user_confirmation: bool = False,
) -> dict:
    """Trigger an Airflow DAG run after explicit user confirmation."""
    async def operation(db, principal):
        if not user_confirmation:
            raise ValueError("Explicit user confirmation is required before triggering a DAG")
        result = await airflow_service.trigger_dag(db, dag_id, conf or {})
        if not result:
            raise ValueError("Airflow DAG trigger failed")
        return result
    args = {"dag_id": dag_id, "conf": conf or {}, "user_confirmation": user_confirmation}
    return await _run_tool("trigger_airflow_dag", "scheduling:execute", args, operation)


@mcp.tool()
async def list_airflow_dag_runs(dag_id: str, limit: int = 50) -> dict:
    """List recent live runs for one Airflow DAG."""
    async def operation(db, principal):
        return {"items": await airflow_service.list_dag_runs(db, dag_id, limit=min(max(limit, 1), 100))}
    args = {"dag_id": dag_id, "limit": limit}
    return await _run_tool("list_airflow_dag_runs", "scheduling:read", args, operation)


@mcp.tool()
async def get_airflow_run_detail(dag_id: str, run_id: str) -> dict:
    """Get a DAG run and all task-instance states."""
    async def operation(db, principal):
        result = await airflow_service.get_dag_run_detail(db, dag_id, run_id)
        if not result:
            raise ValueError("Airflow DAG run not found")
        return result
    args = {"dag_id": dag_id, "run_id": run_id}
    return await _run_tool("get_airflow_run_detail", "scheduling:read", args, operation)


@mcp.tool()
async def get_airflow_task_log(
    dag_id: str, run_id: str, task_id: str, try_number: int = 1, max_chars: int = 20000,
) -> dict:
    """Get a bounded Airflow task log for diagnosis."""
    async def operation(db, principal):
        log = await airflow_service.get_dag_run_log(db, dag_id, run_id, task_id, max(try_number, 1))
        bounded = log[:min(max(max_chars, 1000), 50000)]
        return {"log": bounded, "truncated": len(log) > len(bounded), "total_chars": len(log)}
    args = {"dag_id": dag_id, "run_id": run_id, "task_id": task_id, "try_number": try_number, "max_chars": max_chars}
    return await _run_tool("get_airflow_task_log", "scheduling:read", args, operation)


@mcp.tool()
async def sync_runtime_lineage(user_confirmation: bool = False) -> dict:
    """Synchronize Airflow runs and collect task-level runtime lineage after explicit confirmation."""
    async def operation(db, principal):
        if not user_confirmation:
            raise ValueError("Explicit user confirmation is required before synchronizing runtime lineage")
        return await airflow_service.sync_dag_runs(db)
    args = {"user_confirmation": user_confirmation}
    return await _run_tool("sync_runtime_lineage", "scheduling:execute", args, operation)


@mcp.tool()
async def list_runtime_lineage_runs(
    dag_id: str | None = None, status: str | None = None, limit: int = 50,
) -> dict:
    """List DataMind-recorded DAG runs with runtime-lineage status and asset counts."""
    async def operation(db, principal):
        items, total = await airflow_service.list_dag_runs_page(
            db, 1, min(max(limit, 1), 100), dag_id=dag_id, status=status,
        )
        return {"items": items, "total": total}
    args = {"dag_id": dag_id, "status": status, "limit": limit}
    return await _run_tool("list_runtime_lineage_runs", "lineage:read", args, operation)


@mcp.tool()
async def get_runtime_lineage_tasks(record_id: str) -> dict:
    """Get task SQL, inputs, outputs and errors for one synchronized DAG run record."""
    async def operation(db, principal):
        record = (await db.execute(select(AirflowDagRun).where(AirflowDagRun.id == uuid.UUID(record_id)))).scalar_one_or_none()
        if not record:
            raise ValueError("Runtime lineage run not found")
        return {
            "record_id": record_id, "dag_id": record.dag_id, "dag_run_id": record.dag_run_id,
            "state": record.state, "lineage_status": record.lineage_status,
            "tasks": await airflow_service.list_recorded_task_runs(db, record.id),
        }
    return await _run_tool("get_runtime_lineage_tasks", "lineage:read", {"record_id": record_id}, operation)


@mcp.tool()
async def list_data_services(status: str | None = None, limit: int = 50) -> dict:
    """List data APIs in the service catalog, optionally filtered by lifecycle status."""
    async def operation(db, principal):
        items, total = await data_service.list_apis(db, 1, min(max(limit, 1), 200), status)
        return {"items": items, "total": total}
    return await _run_tool("list_data_services", "data_service:read", {"status": status, "limit": limit}, operation)


@mcp.tool()
async def get_data_service(api_id: str) -> dict:
    """Get a data API definition, parameters, datasource and current lifecycle status."""
    async def operation(db, principal):
        result = await data_service.get_api(db, uuid.UUID(api_id))
        if not result:
            raise ValueError("Data service not found")
        return result
    return await _run_tool("get_data_service", "data_service:read", {"api_id": api_id}, operation)


@mcp.tool()
async def preview_data_service(api_id: str, params: dict | None = None) -> dict:
    """Execute a bounded draft or published data API preview; parameter values and result rows are omitted from MCP audit."""
    async def operation(db, principal):
        return await data_service.execute_api(
            db, uuid.UUID(api_id), params or {}, user_id=principal["user_id"],
            username=principal.get("username") or "MCP", ip="mcp", allow_draft=True,
        )
    return await _run_tool("preview_data_service", "data_service:execute", {"api_id": api_id, "params": params or {}}, operation)


@mcp.tool()
async def set_data_service_status(
    api_id: str, status: str, user_confirmation: bool = False,
) -> dict:
    """Publish or take a data API offline after explicit user confirmation."""
    async def operation(db, principal):
        if not user_confirmation:
            raise ValueError("Explicit user confirmation is required before changing data service status")
        normalized = status.strip().lower()
        if normalized not in {"published", "offline"}:
            raise ValueError("status must be published or offline")
        current = await data_service.get_api(db, uuid.UUID(api_id))
        if not current:
            raise ValueError("Data service not found")
        if normalized == "published":
            validated = DataServiceCreate.model_validate(current)
            if validated.service_type == "custom_sql":
                validate_read_only_sql(validated.sql_template)
        result = await data_service.set_status(db, uuid.UUID(api_id), normalized)
        return result
    args = {"api_id": api_id, "status": status, "user_confirmation": user_confirmation}
    return await _run_tool("set_data_service_status", "data_service:publish", args, operation)


@mcp.tool()
async def list_data_service_app_keys(api_id: str) -> dict:
    """List AppKey metadata and status without exposing any recoverable secret."""
    async def operation(db, principal):
        if not await data_service.get_api(db, uuid.UUID(api_id)):
            raise ValueError("Data service not found")
        return {"items": await data_service.list_app_keys(db, uuid.UUID(api_id))}
    return await _run_tool("list_data_service_app_keys", "data_service:credentials", {"api_id": api_id}, operation)


@mcp.tool()
async def create_data_service_app_key(
    api_id: str, key_name: str, expires_at: str | None = None,
    user_confirmation: bool = False,
) -> dict:
    """Generate an AppKey for a published API. The secret is shown once and excluded from MCP audit."""
    async def operation(db, principal):
        if not user_confirmation:
            raise ValueError("Explicit user confirmation is required before generating an AppKey")
        api = await data_service.get_api(db, uuid.UUID(api_id))
        if not api or api["status"] != "published":
            raise ValueError("Only a published data service can receive an AppKey")
        expiration = datetime.fromisoformat(expires_at.replace("Z", "+00:00")) if expires_at else None
        return await data_service.create_app_key(db, uuid.UUID(api_id), key_name, principal["user_id"], expiration)
    args = {"api_id": api_id, "key_name": key_name, "expires_at": expires_at, "user_confirmation": user_confirmation}
    return await _run_tool("create_data_service_app_key", "data_service:credentials", args, operation)


@mcp.tool()
async def revoke_data_service_app_key(
    api_id: str, key_id: str, user_confirmation: bool = False,
) -> dict:
    """Revoke an AppKey after explicit user confirmation."""
    async def operation(db, principal):
        if not user_confirmation:
            raise ValueError("Explicit user confirmation is required before revoking an AppKey")
        if not await data_service.revoke_app_key(db, uuid.UUID(api_id), uuid.UUID(key_id)):
            raise ValueError("AppKey not found")
        return {"success": True, "api_id": api_id, "key_id": key_id, "status": "revoked"}
    args = {"api_id": api_id, "key_id": key_id, "user_confirmation": user_confirmation}
    return await _run_tool("revoke_data_service_app_key", "data_service:credentials", args, operation)


@mcp.tool()
async def list_data_service_call_logs(api_id: str | None = None, limit: int = 50) -> dict:
    """List data API calls without returning request parameter values."""
    async def operation(db, principal):
        parsed_id = uuid.UUID(api_id) if api_id else None
        items, total = await data_service.list_call_logs(db, 1, min(max(limit, 1), 200), parsed_id)
        safe_items = []
        for item in items:
            raw = item.pop("request_params", None)
            try:
                parameter_names = sorted(json.loads(raw).keys()) if raw else []
            except (ValueError, TypeError, AttributeError):
                parameter_names = []
            safe_items.append({**item, "parameter_names": parameter_names})
        return {"items": safe_items, "total": total}
    args = {"api_id": api_id, "limit": limit}
    return await _run_tool("list_data_service_call_logs", "data_service:monitor", args, operation)


@mcp.tool()
async def get_data_service_call_stats(days: int = 7) -> dict:
    """Get total, success, failure, latency and daily call trends for data APIs."""
    async def operation(db, principal):
        return await data_service.get_call_stats(db, min(max(days, 1), 90))
    return await _run_tool("get_data_service_call_stats", "data_service:monitor", {"days": days}, operation)


@mcp.tool()
async def get_data_asset_overview() -> dict:
    """Get physical-table, column, runtime-lineage and enabled quality-rule counts."""
    async def operation(db, principal):
        return await data_asset_service.catalog_overview(db)
    return await _run_tool("get_data_asset_overview", "catalog:read", {}, operation)


@mcp.tool()
async def list_data_assets(
    keyword: str | None = None, datasource_id: str | None = None, limit: int = 50,
) -> dict:
    """Search physical table assets only; logical models are intentionally excluded."""
    async def operation(db, principal):
        parsed_id = uuid.UUID(datasource_id) if datasource_id else None
        items, total = await data_asset_service.list_assets(
            db, 1, min(max(limit, 1), 200), keyword, parsed_id, "active", "table",
        )
        return {"items": items, "total": total}
    args = {"keyword": keyword, "datasource_id": datasource_id, "limit": limit}
    return await _run_tool("list_data_assets", "catalog:read", args, operation)


@mcp.tool()
async def get_data_asset(asset_id: str) -> dict:
    """Get one physical table asset including fields and lineage/quality counts."""
    async def operation(db, principal):
        result = await data_asset_service.get_asset(db, uuid.UUID(asset_id))
        if not result:
            raise ValueError("Data asset not found")
        return result
    return await _run_tool("get_data_asset", "catalog:read", {"asset_id": asset_id}, operation)


@mcp.tool()
async def sync_data_catalog(
    datasource_id: str | None = None, user_confirmation: bool = False,
) -> dict:
    """Synchronize physical table and field metadata after explicit user confirmation."""
    async def operation(db, principal):
        if not user_confirmation:
            raise ValueError("Explicit user confirmation is required before synchronizing the data catalog")
        parsed_id = uuid.UUID(datasource_id) if datasource_id else None
        return await data_asset_service.sync_catalog(db, parsed_id)
    args = {"datasource_id": datasource_id, "user_confirmation": user_confirmation}
    return await _run_tool("sync_data_catalog", "catalog:sync", args, operation)


@mcp.tool()
async def list_asset_runtime_lineage(keyword: str | None = None) -> dict:
    """List table-to-table lineage observed from successful task runs only."""
    async def operation(db, principal):
        return await data_asset_service.list_lineage(db, keyword)
    return await _run_tool("list_asset_runtime_lineage", "lineage:read", {"keyword": keyword}, operation)


@mcp.tool()
async def list_quality_rules(asset_id: str | None = None) -> dict:
    """List quality rules and latest run results, optionally for one asset."""
    async def operation(db, principal):
        items = await data_asset_service.list_quality_rules(db)
        if asset_id:
            items = [item for item in items if item["asset_id"] == asset_id]
        return {"items": items, "total": len(items)}
    return await _run_tool("list_quality_rules", "quality:read", {"asset_id": asset_id}, operation)


@mcp.tool()
async def run_quality_rule(rule_id: str, user_confirmation: bool = False) -> dict:
    """Execute one quality rule and persist its result after explicit user confirmation."""
    async def operation(db, principal):
        if not user_confirmation:
            raise ValueError("Explicit user confirmation is required before executing a quality rule")
        return await data_asset_service.run_quality_rule(db, uuid.UUID(rule_id))
    args = {"rule_id": rule_id, "user_confirmation": user_confirmation}
    return await _run_tool("run_quality_rule", "quality:execute", args, operation)


@mcp.tool()
async def delete_quality_rule(rule_id: str, user_confirmation: bool = False) -> dict:
    """Permanently delete one quality rule after explicit user confirmation."""
    async def operation(db, principal):
        if not user_confirmation:
            raise ValueError("Explicit user confirmation is required before deleting a quality rule")
        entity = (await db.execute(select(QualityRule).where(QualityRule.id == uuid.UUID(rule_id)))).scalar_one_or_none()
        if not entity:
            raise ValueError("Quality rule not found")
        await db.delete(entity)
        await db.commit()
        return {"success": True, "rule_id": rule_id, "status": "deleted"}
    args = {"rule_id": rule_id, "user_confirmation": user_confirmation}
    return await _run_tool("delete_quality_rule", "quality:execute", args, operation)


@mcp.tool()
async def create_change_set(title: str, description: str | None = None) -> dict:
    """Create an isolated modeling change set. Do this before any draft write."""
    async def operation(db, principal):
        return await mcp_service.create_change_set(db, principal, title, description)
    return await _run_tool("create_change_set", "changeset:draft", {"title": title, "description": description}, operation)


@mcp.tool()
async def create_data_domain_draft(
    change_set_id: str, domain_code: str, domain_name: str,
    description: str | None = None, sort_order: int = 0,
) -> dict:
    """Add a new data-domain draft to an existing change set."""
    payload = {"domain_code": domain_code, "domain_name": domain_name, "description": description, "sort_order": sort_order}
    async def operation(db, principal):
        return await mcp_service.add_change_item(db, principal, uuid.UUID(change_set_id), "data_domain", payload)
    return await _run_tool("create_data_domain_draft", "modeling:draft", {"change_set_id": change_set_id, **payload}, operation)


@mcp.tool()
async def create_business_process_draft(
    change_set_id: str, process_code: str, process_name: str, data_domain_code: str,
    description: str | None = None, sort_order: int = 0,
) -> dict:
    """Add a business-process draft under a data-domain code."""
    payload = {
        "process_code": process_code, "process_name": process_name,
        "data_domain_code": data_domain_code, "description": description, "sort_order": sort_order,
    }
    async def operation(db, principal):
        return await mcp_service.add_change_item(db, principal, uuid.UUID(change_set_id), "business_process", payload)
    return await _run_tool("create_business_process_draft", "modeling:draft", {"change_set_id": change_set_id, **payload}, operation)


@mcp.tool()
async def create_data_model_draft(
    change_set_id: str, model_code: str, model_name: str, layer: str,
    database: str, table_name: str, fields: list[dict],
    data_domain_code: str | None = None, business_process_code: str | None = None,
    model_grain: str | None = None, description: str | None = None,
    update_strategy: str | None = None, source_tables: list[str] | None = None,
    etl_sql: str | None = None, is_external: bool = False,
) -> dict:
    """Add a DWD/DWS/ADS/ODS/DIM model design draft; this never executes DDL."""
    payload = {
        "model_code": model_code, "model_name": model_name, "layer": layer,
        "database": database, "table_name": table_name, "fields": fields,
        "data_domain_code": data_domain_code, "business_process_code": business_process_code,
        "model_grain": model_grain, "description": description, "update_strategy": update_strategy,
        "source_tables": source_tables or [], "etl_sql": etl_sql, "is_external": is_external,
    }
    async def operation(db, principal):
        return await mcp_service.add_change_item(db, principal, uuid.UUID(change_set_id), "data_model", payload)
    return await _run_tool("create_data_model_draft", "modeling:draft", {"change_set_id": change_set_id, **payload}, operation)


@mcp.tool()
async def create_sql_script_draft(
    change_set_id: str, script_code: str, script_name: str, content: str,
    description: str | None = None,
) -> dict:
    """Add a saved read-only SQL development script to a change set; it is never executed here."""
    payload = {
        "script_code": script_code, "script_name": script_name,
        "content": content, "description": description,
    }
    async def operation(db, principal):
        return await mcp_service.add_change_item(db, principal, uuid.UUID(change_set_id), "sql_script", payload)
    return await _run_tool("create_sql_script_draft", "development:draft", {"change_set_id": change_set_id, **payload}, operation)


@mcp.tool()
async def create_metric_category_draft(
    change_set_id: str, category_code: str, category_name: str,
    description: str | None = None, sort_order: int = 0,
) -> dict:
    """Add a metric-category draft to a change set."""
    payload = {
        "category_code": category_code, "category_name": category_name,
        "description": description, "sort_order": sort_order,
    }
    async def operation(db, principal):
        return await mcp_service.add_change_item(db, principal, uuid.UUID(change_set_id), "metric_category", payload)
    return await _run_tool("create_metric_category_draft", "metrics:draft", {"change_set_id": change_set_id, **payload}, operation)


@mcp.tool()
async def create_cube_model_draft(
    change_set_id: str, name: str, data_source: str,
    dimensions: list[dict], measures: list[dict], sql_table: str = "", sql: str = "",
    title: str = "", joins: list[dict] | None = None, segments: list[dict] | None = None,
) -> dict:
    """Add a Cube draft using a real DataMind datasource; default is forbidden. Commit writes the schema file but does not restart Cube."""
    payload = {
        "name": name, "title": title, "sql_table": sql_table, "sql": sql,
        "data_source": data_source, "joins": joins or [], "dimensions": dimensions,
        "measures": measures, "segments": segments or [],
    }
    async def operation(db, principal):
        return await mcp_service.add_change_item(db, principal, uuid.UUID(change_set_id), "cube_model", payload)
    return await _run_tool("create_cube_model_draft", "metrics:draft", {"change_set_id": change_set_id, **payload}, operation)


@mcp.tool()
async def create_metric_definition_draft(
    change_set_id: str, metric_code: str, metric_name: str, metric_type: str,
    cube_name: str, cube_measure: str, category_code: str | None = None,
    dimensions: list[str] | None = None, default_time_dimension: str | None = None,
    calculation: str | None = None, business_domain: str | None = None,
    unit: str | None = None, description: str | None = None,
) -> dict:
    """Add an atomic, derived or composite metric definition draft referencing a validated Cube measure."""
    payload = {
        "metric_code": metric_code, "metric_name": metric_name, "metric_type": metric_type,
        "cube_name": cube_name, "cube_measure": cube_measure, "category_code": category_code,
        "dimensions": dimensions or [], "default_time_dimension": default_time_dimension,
        "calculation": calculation, "business_domain": business_domain,
        "unit": unit, "description": description,
    }
    async def operation(db, principal):
        return await mcp_service.add_change_item(db, principal, uuid.UUID(change_set_id), "metric_definition", payload)
    return await _run_tool("create_metric_definition_draft", "metrics:draft", {"change_set_id": change_set_id, **payload}, operation)


@mcp.tool()
async def create_airflow_sql_dag_draft(
    change_set_id: str, dag_id: str, datasource_name: str, database: str, sql: str,
    schedule: str | None = None, task_id: str = "execute_sql", description: str | None = None,
) -> dict:
    """Stage a paused Airflow DAG for one INSERT INTO ... SELECT transformation and runtime lineage reporting."""
    payload = {
        "dag_id": dag_id, "task_id": task_id, "datasource_name": datasource_name,
        "database": database, "sql": sql, "schedule": schedule, "description": description,
    }
    async def operation(db, principal):
        return await mcp_service.add_change_item(db, principal, uuid.UUID(change_set_id), "airflow_sql_dag", payload)
    return await _run_tool("create_airflow_sql_dag_draft", "scheduling:write", {"change_set_id": change_set_id, **payload}, operation)


@mcp.tool()
async def create_data_service_draft(
    change_set_id: str, api_name: str, service_code: str, service_type: str,
    method: str = "GET", datasource_id: str | None = None, database: str = "",
    sql_template: str = "", parameters: list[dict] | None = None,
    table_name: str | None = None, selected_fields: list[str] | None = None,
    filter_fields: list[dict] | None = None, metric_ids: list[str] | None = None,
    metric_dimensions: list[str] | None = None, time_dimension: str | None = None,
    default_granularity: str | None = "day", max_rows: int = 1000,
    cache_enabled: bool = False, cache_ttl: int = 300, description: str | None = None,
) -> dict:
    """Stage a table, read-only custom SQL or metric data API; commit creates it as an unpublished draft."""
    payload = {
        "api_name": api_name, "service_code": service_code, "service_type": service_type,
        "method": method.upper(), "datasource_id": datasource_id, "database": database,
        "sql_template": sql_template, "parameters": parameters or [], "table_name": table_name,
        "selected_fields": selected_fields or [], "filter_fields": filter_fields or [],
        "metric_ids": metric_ids or [], "metric_dimensions": metric_dimensions or [],
        "time_dimension": time_dimension, "default_granularity": default_granularity,
        "max_rows": max_rows, "cache_enabled": cache_enabled, "cache_ttl": cache_ttl,
        "description": description,
    }
    async def operation(db, principal):
        return await mcp_service.add_change_item(db, principal, uuid.UUID(change_set_id), "data_service_api", payload)
    return await _run_tool("create_data_service_draft", "data_service:draft", {"change_set_id": change_set_id, **payload}, operation)


@mcp.tool()
async def create_quality_rule_draft(
    change_set_id: str, asset_id: str, rule_name: str, rule_type: str,
    column_name: str | None = None, config: dict | None = None, enabled: bool = True,
) -> dict:
    """Stage a not-null, unique, numeric-range or read-only custom SQL quality rule."""
    payload = {
        "asset_id": asset_id, "rule_name": rule_name, "rule_type": rule_type,
        "column_name": column_name, "config": config or {}, "enabled": enabled,
    }
    async def operation(db, principal):
        return await mcp_service.add_change_item(db, principal, uuid.UUID(change_set_id), "quality_rule", payload)
    return await _run_tool("create_quality_rule_draft", "quality:draft", {"change_set_id": change_set_id, **payload}, operation)


@mcp.tool()
async def get_change_set(change_set_id: str) -> dict:
    """Return the full modeling change set and validation result for user review."""
    async def operation(db, principal):
        return await mcp_service.get_change_set(db, principal, uuid.UUID(change_set_id))
    return await _run_tool("get_change_set", "modeling:read", {"change_set_id": change_set_id}, operation)


@mcp.tool()
async def validate_change_set(change_set_id: str) -> dict:
    """Validate all dependencies and drafts without modifying published platform objects."""
    async def operation(db, principal):
        return await mcp_service.validate_change_set(db, principal, uuid.UUID(change_set_id))
    return await _run_tool("validate_change_set", "modeling:draft", {"change_set_id": change_set_id}, operation)


@mcp.tool()
async def discard_change_set(change_set_id: str) -> dict:
    """Discard an uncommitted modeling change set and keep platform objects unchanged."""
    async def operation(db, principal):
        return await mcp_service.discard_change_set(db, principal, uuid.UUID(change_set_id))
    return await _run_tool("discard_change_set", "modeling:draft", {"change_set_id": change_set_id}, operation)


@mcp.tool()
async def commit_change_set(change_set_id: str, user_confirmation: bool = False) -> dict:
    """Commit validated objects after explicit confirmation. Never executes SQL or Doris DDL; Cube files require a separate refresh."""
    async def operation(db, principal):
        if not user_confirmation:
            raise ValueError("Explicit user confirmation is required before committing a change set")
        return await mcp_service.commit_change_set(db, principal, uuid.UUID(change_set_id))
    return await _run_tool(
        "commit_change_set", "changeset:commit",
        {"change_set_id": change_set_id, "user_confirmation": user_confirmation}, operation,
    )


@mcp.prompt()
def build_data_model(goal: str) -> str:
    """Safe workflow for building domains, processes and model designs."""
    return (
        f"目标：{goal}\n"
        "先读取DataMind数据域、业务过程和相关模型资源；创建变更集；只向变更集写入草稿；"
        "调用validate_change_set并向用户展示全部错误、警告和变更；未经用户明确确认不得调用commit_change_set。"
    )


@mcp.prompt()
def build_data_development_and_metrics(goal: str) -> str:
    """Safe workflow for SQL development, Cube modeling and metric construction."""
    return (
        f"目标：{goal}\n"
        "先读取数据源、SQL脚本、指标分类、Cube模型和指标定义；创建变更集；"
        "SQL脚本只能保存单条只读SQL且不会自动执行；Cube必须使用真实数据源名称，不能使用default；"
        "指标必须引用有效Cube度量，默认时间维度必须是time类型；调用validate_change_set并展示结果；"
        "未经用户明确确认不得调用commit_change_set。提交Cube模型后若结果提示需要刷新，先向用户说明影响；"
        "只有再次取得明确确认后，才能调用refresh_cube并将user_confirmation设为true。"
    )


@mcp.prompt()
def build_data_service(goal: str) -> str:
    """Safe workflow for designing, previewing and publishing a data API."""
    return (
        f"目标：{goal}\n"
        "先读取数据服务目录、数据源或指标目录；创建变更集并调用create_data_service_draft；"
        "自定义SQL只能是只读查询，SQL占位符必须声明为参数；校验后向用户展示服务路径、方法、参数、"
        "数据源、最大行数和缓存配置；未经确认不得提交变更集。提交后服务仍为草稿，可先预览；"
        "未经再次明确确认不得发布、停用、生成或撤销AppKey。AppKey只展示一次。"
    )


@mcp.prompt()
def build_data_assets(goal: str) -> str:
    """Safe workflow for physical catalog, runtime lineage and data quality."""
    return (
        f"目标：{goal}\n"
        "数据目录只包含物理表。先检索资产和字段，再读取成功任务产生的运行血缘；"
        "质量规则必须先写入变更集并校验，未经确认不得提交。规则提交后不会自动执行；"
        "执行质量检测、同步目录和删除规则前必须再次取得明确确认。"
    )


async def health(request):
    return JSONResponse({"status": "ok", "service": "datamind-mcp"})


@contextlib.asynccontextmanager
async def lifespan(app):
    async with mcp.session_manager.run():
        yield


app = Starlette(
    routes=[
        Route("/health", health),
        Mount("/", app=McpBearerAuthMiddleware(mcp.streamable_http_app())),
    ],
    lifespan=lifespan,
)
