"""Data catalog metadata sync, lineage building and quality execution."""
import re
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    AssetColumn, AssetLineageEdge, AssetObject, DataSource,
    QualityRule, QualityRuleRun,
)
from app.services import datasource_service


_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]*$")


def _asset_dict(asset: AssetObject, datasource_name: str = "", column_count: int | None = None) -> dict:
    return {
        "id": str(asset.id),
        "datasource_id": str(asset.datasource_id),
        "datasource_name": datasource_name,
        "asset_type": asset.asset_type,
        "name": asset.name,
        "fqn": asset.fqn,
        "database_name": asset.database_name,
        "schema_name": asset.schema_name,
        "description": asset.description,
        "status": asset.status,
        "properties": asset.properties or {},
        "column_count": column_count if column_count is not None else len(asset.columns or []),
        "last_synced_at": asset.last_synced_at.isoformat() if asset.last_synced_at else None,
    }


async def sync_catalog(db: AsyncSession, datasource_id: uuid.UUID | None = None) -> dict:
    query = select(DataSource).where(DataSource.status == "active")
    if datasource_id:
        query = query.where(DataSource.id == datasource_id)
    datasources = list((await db.execute(query)).scalars().all())
    if not datasources:
        raise ValueError("没有可同步的启用数据源")

    # The catalog contains physical database objects only. Logical model assets
    # from the early MVP are removed; model definitions remain in data_models.
    await db.execute(delete(AssetObject).where(AssetObject.asset_type != "table"))
    await db.commit()

    summary = {"datasources": 0, "tables": 0, "columns": 0, "errors": []}
    now = datetime.now(timezone.utc)
    for ds in datasources:
        try:
            await db.execute(
                update(AssetObject).where(
                    AssetObject.datasource_id == ds.id,
                    AssetObject.asset_type == "table",
                ).values(status="stale")
            )
            databases = [ds.database_name or ""]
            if ds.source_type == "doris":
                visible_databases = await datasource_service.list_databases(db, ds.id)
                databases = [name for name in visible_databases if name and not name.startswith("__")]
            for database_name in databases:
                tables = await datasource_service.list_tables(db, ds.id, ds.default_schema, database_name)
                for table_info in tables:
                    table_name = str(table_info.get("name") or table_info.get("table_name") or "")
                    if not table_name:
                        continue
                    schema_name = ds.default_schema or ("public" if ds.source_type == "postgresql" else None)
                    parts = [ds.source_name, database_name, schema_name, table_name]
                    fqn = ".".join(str(part) for part in parts if part)
                    asset = (await db.execute(select(AssetObject).where(AssetObject.fqn == fqn))).scalar_one_or_none()
                    if not asset:
                        asset = AssetObject(
                            datasource_id=ds.id, asset_type="table", name=table_name, fqn=fqn,
                            database_name=database_name or None, schema_name=schema_name,
                        )
                        db.add(asset)
                        await db.flush()
                    asset.status = "active"
                    asset.last_synced_at = now
                    columns = await datasource_service.get_table_columns(
                        db, ds.id, table_name, schema_name, database_name
                    )
                    await db.execute(delete(AssetColumn).where(AssetColumn.asset_id == asset.id))
                    for index, column in enumerate(columns, start=1):
                        db.add(AssetColumn(
                            asset_id=asset.id,
                            name=str(column.get("field") or column.get("column_name") or ""),
                            data_type=str(column.get("type") or column.get("column_type") or ""),
                            nullable=str(column.get("null") or column.get("is_nullable") or "").upper() == "YES",
                            primary_key=str(column.get("key") or column.get("column_key") or "").upper() == "PRI",
                            default_value=None if column.get("default") is None else str(column.get("default")),
                            ordinal_position=index,
                        ))
                    summary["tables"] += 1
                    summary["columns"] += len(columns)
            summary["datasources"] += 1
            await db.commit()
        except Exception as exc:
            await db.rollback()
            summary["errors"].append({"datasource": ds.source_name, "message": str(exc)[:300]})
    return summary


async def list_assets(
    db: AsyncSession, page: int, page_size: int, keyword: str | None = None,
    datasource_id: uuid.UUID | None = None, status: str | None = "active",
    asset_type: str | None = None,
) -> tuple[list[dict], int]:
    filters = []
    if keyword:
        pattern = f"%{keyword.strip()}%"
        filters.append(or_(AssetObject.name.ilike(pattern), AssetObject.fqn.ilike(pattern), AssetObject.description.ilike(pattern)))
    if datasource_id:
        filters.append(AssetObject.datasource_id == datasource_id)
    if status:
        filters.append(AssetObject.status == status)
    filters.append(AssetObject.asset_type == "table")
    count = (await db.execute(select(func.count(AssetObject.id)).where(*filters))).scalar_one()
    rows = await db.execute(
        select(AssetObject, DataSource.source_name, func.count(AssetColumn.id))
        .join(DataSource, DataSource.id == AssetObject.datasource_id)
        .outerjoin(AssetColumn, AssetColumn.asset_id == AssetObject.id)
        .where(*filters)
        .group_by(AssetObject.id, DataSource.source_name)
        .order_by(DataSource.source_name, AssetObject.database_name, AssetObject.name)
        .offset((page - 1) * page_size).limit(page_size)
    )
    return [_asset_dict(asset, ds_name, int(column_count)) for asset, ds_name, column_count in rows.all()], count


async def get_asset(db: AsyncSession, asset_id: uuid.UUID) -> dict | None:
    row = (await db.execute(
        select(AssetObject, DataSource.source_name)
        .join(DataSource, DataSource.id == AssetObject.datasource_id)
        .options(selectinload(AssetObject.columns))
        .where(AssetObject.id == asset_id)
    )).first()
    if not row:
        return None
    asset, datasource_name = row
    data = _asset_dict(asset, datasource_name)
    data["columns"] = [{
        "id": str(column.id), "name": column.name, "data_type": column.data_type,
        "description": column.description, "nullable": column.nullable,
        "primary_key": column.primary_key, "default_value": column.default_value,
        "ordinal_position": column.ordinal_position,
    } for column in asset.columns]
    data["quality_rules"] = (await db.execute(
        select(func.count(QualityRule.id)).where(QualityRule.asset_id == asset.id)
    )).scalar_one()
    data["upstream_count"] = (await db.execute(
        select(func.count(AssetLineageEdge.id)).where(AssetLineageEdge.target_asset_id == asset.id)
    )).scalar_one()
    data["downstream_count"] = (await db.execute(
        select(func.count(AssetLineageEdge.id)).where(AssetLineageEdge.source_asset_id == asset.id)
    )).scalar_one()
    return data


async def catalog_overview(db: AsyncSession) -> dict:
    return {
        "assets": (await db.execute(select(func.count(AssetObject.id)).where(
            AssetObject.status == "active", AssetObject.asset_type == "table"
        ))).scalar_one(),
        "columns": (await db.execute(select(func.count(AssetColumn.id)).join(
            AssetObject, AssetObject.id == AssetColumn.asset_id
        ).where(AssetObject.asset_type == "table"))).scalar_one(),
        "lineage_edges": (await db.execute(select(func.count(AssetLineageEdge.id)).where(AssetLineageEdge.status == "active"))).scalar_one(),
        "quality_rules": (await db.execute(select(func.count(QualityRule.id)).where(QualityRule.enabled.is_(True)))).scalar_one(),
    }


async def list_lineage(db: AsyncSession, keyword: str | None = None) -> dict:
    source = AssetObject.__table__.alias("source_asset")
    target = AssetObject.__table__.alias("target_asset")
    query = (
        select(AssetLineageEdge, source.c.name.label("source_name"), source.c.fqn.label("source_fqn"),
               target.c.name.label("target_name"), target.c.fqn.label("target_fqn"))
        .join(source, source.c.id == AssetLineageEdge.source_asset_id)
        .join(target, target.c.id == AssetLineageEdge.target_asset_id)
        .where(AssetLineageEdge.status == "active", AssetLineageEdge.source_type == "runtime")
        .order_by(AssetLineageEdge.last_seen_at.desc().nullslast(), target.c.name, source.c.name)
    )
    if keyword:
        pattern = f"%{keyword}%"
        query = query.where(or_(source.c.name.ilike(pattern), target.c.name.ilike(pattern)))
    rows = (await db.execute(query)).all()
    return {"edges": [{
        "id": str(edge.id), "source_asset_id": str(edge.source_asset_id), "target_asset_id": str(edge.target_asset_id),
        "source_name": source_name, "source_fqn": source_fqn, "target_name": target_name, "target_fqn": target_fqn,
        "lineage_type": edge.lineage_type, "source_type": edge.source_type, "confidence": edge.confidence,
        "first_seen_at": edge.first_seen_at.isoformat() if edge.first_seen_at else None,
        "last_seen_at": edge.last_seen_at.isoformat() if edge.last_seen_at else None,
        "success_count": edge.success_count, "last_dag_run_id": edge.last_dag_run_id,
        "last_task_id": edge.last_task_id,
    } for edge, source_name, source_fqn, target_name, target_fqn in rows], "total": len(rows)}


def _rule_dict(rule: QualityRule, asset: AssetObject, run: QualityRuleRun | None = None) -> dict:
    return {
        "id": str(rule.id), "asset_id": str(rule.asset_id), "asset_name": asset.name, "asset_fqn": asset.fqn,
        "rule_name": rule.rule_name, "rule_type": rule.rule_type, "column_name": rule.column_name,
        "config": rule.config or {}, "enabled": rule.enabled,
        "last_run": None if not run else {
            "id": str(run.id), "status": run.status, "total_count": run.total_count,
            "failed_count": run.failed_count, "pass_rate": float(run.pass_rate),
            "message": run.message, "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        },
    }


async def list_quality_rules(db: AsyncSession) -> list[dict]:
    rules = list((await db.execute(
        select(QualityRule, AssetObject).join(AssetObject, AssetObject.id == QualityRule.asset_id)
        .order_by(QualityRule.created_at.desc())
    )).all())
    result = []
    for rule, asset in rules:
        run = (await db.execute(
            select(QualityRuleRun).where(QualityRuleRun.rule_id == rule.id)
            .order_by(QualityRuleRun.started_at.desc()).limit(1)
        )).scalar_one_or_none()
        result.append(_rule_dict(rule, asset, run))
    return result


async def create_quality_rule(db: AsyncSession, data: dict, user_id: uuid.UUID) -> dict:
    asset = (await db.execute(select(AssetObject).where(AssetObject.id == data["asset_id"]))).scalar_one_or_none()
    if not asset:
        raise ValueError("资产不存在")
    if data.get("column_name") and data["column_name"] not in {column.name for column in asset.columns}:
        raise ValueError("字段不属于所选资产")
    rule = QualityRule(**data, created_by=user_id)
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return _rule_dict(rule, asset)


def _quote(name: str, source_type: str) -> str:
    if not _IDENTIFIER.match(name):
        raise ValueError(f"不安全的标识符：{name}")
    return f'"{name}"' if source_type == "postgresql" else f'`{name}`'


async def run_quality_rule(db: AsyncSession, rule_id: uuid.UUID) -> dict:
    row = (await db.execute(
        select(QualityRule, AssetObject, DataSource)
        .join(AssetObject, AssetObject.id == QualityRule.asset_id)
        .join(DataSource, DataSource.id == AssetObject.datasource_id)
        .where(QualityRule.id == rule_id)
    )).first()
    if not row:
        raise ValueError("质量规则不存在")
    rule, asset, datasource = row
    if not rule.enabled:
        raise ValueError("质量规则已停用")
    table = _quote(asset.name, datasource.source_type)
    column = _quote(rule.column_name, datasource.source_type) if rule.column_name else None
    config = rule.config or {}
    if rule.rule_type == "not_null" and column:
        sql = f"SELECT COUNT(*) AS total_count, SUM(CASE WHEN {column} IS NULL THEN 1 ELSE 0 END) AS failed_count FROM {table}"
    elif rule.rule_type == "unique" and column:
        sql = f"SELECT COUNT(*) AS total_count, COUNT(*) - COUNT(DISTINCT {column}) AS failed_count FROM {table}"
    elif rule.rule_type == "range" and column:
        minimum, maximum = config.get("min"), config.get("max")
        if minimum is None or maximum is None:
            raise ValueError("范围检查必须配置最小值和最大值")
        sql = f"SELECT COUNT(*) AS total_count, SUM(CASE WHEN {column} < {float(minimum)} OR {column} > {float(maximum)} THEN 1 ELSE 0 END) AS failed_count FROM {table}"
    elif rule.rule_type == "custom_sql":
        custom_sql = str(config.get("sql") or "").strip().rstrip(";")
        if not custom_sql:
            raise ValueError("自定义 SQL 不能为空")
        result = await datasource_service.execute_query(db, datasource.id, custom_sql, 10000, asset.database_name)
        total = failed = int(result["row_count"])
        return await _save_run(db, rule, total, failed, "自定义 SQL 返回的每一行均视为异常记录")
    else:
        raise ValueError("规则类型或字段配置无效")
    result = await datasource_service.execute_query(db, datasource.id, sql, 1, asset.database_name)
    values = result["rows"][0] if result["rows"] else {}
    total = int(values.get("total_count") or 0)
    failed = int(values.get("failed_count") or 0)
    return await _save_run(db, rule, total, failed)


async def _save_run(db: AsyncSession, rule: QualityRule, total: int, failed: int, message: str | None = None) -> dict:
    passed = max(total - failed, 0)
    pass_rate = Decimal("100") if total == 0 else (Decimal(passed) * Decimal("100") / Decimal(total))
    run = QualityRuleRun(
        rule_id=rule.id, status="passed" if failed == 0 else "failed",
        total_count=total, failed_count=failed, pass_rate=pass_rate,
        message=message, finished_at=datetime.now(timezone.utc),
    )
    db.add(run)
    await db.commit()
    return {
        "id": str(run.id), "status": run.status, "total_count": total,
        "failed_count": failed, "pass_rate": float(pass_rate), "message": message,
    }
