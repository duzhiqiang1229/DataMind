"""Ingest successful Airflow task callbacks and aggregate runtime lineage."""
import hashlib
import uuid
from datetime import datetime, timezone
from urllib.parse import unquote, urlparse

import sqlglot
from sqlglot import expressions as exp
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AirflowDagRun, AirflowTaskRun, AssetLineageEdge, AssetObject,
    DataSource, LineageRunEvent,
)


def _table_ref(table: exp.Table, default_database: str | None = None) -> dict:
    return {
        "name": table.name,
        "database": table.db or default_database,
        "catalog": table.catalog or None,
    }


def parse_runtime_sql(sql: str, default_database: str | None = None) -> tuple[list[dict], list[dict]]:
    """Return input and output physical table references from rendered SQL."""
    inputs: dict[tuple, dict] = {}
    outputs: dict[tuple, dict] = {}
    if not sql or not sql.strip():
        return [], []
    try:
        statements = sqlglot.parse(sql, read="mysql")
    except Exception:
        try:
            statements = sqlglot.parse(sql)
        except Exception:
            return [], []
    for statement in statements:
        if statement is None:
            continue
        target_tables: list[exp.Table] = []
        if isinstance(statement, (exp.Insert, exp.Merge)) and isinstance(statement.this, exp.Table):
            target_tables.append(statement.this)
        elif isinstance(statement, exp.Create) and isinstance(statement.this, exp.Table):
            target_tables.append(statement.this)
        elif isinstance(statement, (exp.Update, exp.Delete)) and isinstance(statement.this, exp.Table):
            target_tables.append(statement.this)
        target_keys = set()
        for table in target_tables:
            ref = _table_ref(table, default_database)
            key = ((ref["catalog"] or "").lower(), (ref["database"] or "").lower(), ref["name"].lower())
            outputs[key] = ref
            target_keys.add(key)
        for table in statement.find_all(exp.Table):
            ref = _table_ref(table, default_database)
            key = ((ref["catalog"] or "").lower(), (ref["database"] or "").lower(), ref["name"].lower())
            if key not in target_keys:
                inputs[key] = ref
    return list(inputs.values()), list(outputs.values())


def _explicit_refs(values: list[str], default_database: str | None) -> list[dict]:
    refs = []
    for value in values:
        parts = [part.strip("`\" ") for part in str(value).split(".") if part.strip("`\" ")]
        if not parts:
            continue
        refs.append({
            "name": parts[-1],
            "database": parts[-2] if len(parts) >= 2 else default_database,
            "catalog": parts[-3] if len(parts) >= 3 else None,
        })
    return refs


def _dataset_refs(values: list[dict], default_database: str | None) -> list[dict]:
    """Convert OpenLineage datasets to physical table references."""
    refs = []
    for dataset in values:
        if not isinstance(dataset, dict):
            continue
        name = str(dataset.get("name") or "").strip()
        if not name:
            continue
        parts = [part.strip("`\" ") for part in name.split(".") if part.strip("`\" ")]
        if not parts:
            continue
        namespace = str(dataset.get("namespace") or "").strip()
        datasource_name = None
        marker = "datamind://datasource/"
        if namespace.lower().startswith(marker):
            datasource_name = unquote(namespace[len(marker):]) or None
        refs.append({
            "name": parts[-1],
            "database": parts[-2] if len(parts) >= 2 else default_database,
            "catalog": parts[-3] if len(parts) >= 3 else None,
            "namespace": namespace or None,
            "datasource_name": datasource_name,
        })
    return refs


def _dedupe_refs(refs: list[dict]) -> list[dict]:
    unique: dict[tuple[str, str, str], dict] = {}
    for ref in refs:
        key = (
            str(ref.get("catalog") or "").lower(),
            str(ref.get("database") or "").lower(),
            str(ref.get("name") or "").lower(),
        )
        if key[2]:
            existing = unique.get(key)
            if not existing or ref.get("namespace") or ref.get("datasource_name"):
                unique[key] = ref
    return list(unique.values())


def _dedupe_datasets(values: list[dict]) -> list[dict]:
    unique: dict[tuple[str, str], dict] = {}
    for value in values:
        if not isinstance(value, dict) or not value.get("name"):
            continue
        normalized = {
            "namespace": str(value.get("namespace") or ""),
            "name": str(value["name"]),
        }
        unique[(normalized["namespace"].lower(), normalized["name"].lower())] = normalized
    return list(unique.values())


async def _resolve_asset(
    db: AsyncSession, ref: dict, datasource_name: str | None,
) -> AssetObject | None:
    query = (
        select(AssetObject)
        .join(DataSource, DataSource.id == AssetObject.datasource_id)
        .where(
            AssetObject.asset_type == "table", AssetObject.status == "active",
            func.lower(AssetObject.name) == str(ref["name"]).lower(),
        )
    )
    if ref.get("database"):
        query = query.where(func.lower(AssetObject.database_name) == str(ref["database"]).lower())
    effective_source_name = ref.get("datasource_name") or datasource_name
    if effective_source_name:
        query = query.where(func.lower(DataSource.source_name) == str(effective_source_name).lower())
    elif ref.get("namespace"):
        namespace = str(ref["namespace"])
        if namespace.startswith("jdbc:"):
            namespace = namespace[5:]
        parsed = urlparse(namespace)
        if parsed.hostname:
            query = query.where(func.lower(DataSource.host) == parsed.hostname.lower())
        try:
            namespace_port = parsed.port
        except ValueError:
            namespace_port = None
        if namespace_port:
            query = query.where(DataSource.port == namespace_port)
    matches = list((await db.execute(query.limit(2))).scalars().all())
    return matches[0] if len(matches) == 1 else None


async def ingest_event(db: AsyncSession, payload: dict) -> dict:
    now = datetime.now(timezone.utc)
    dag_run = (await db.execute(select(AirflowDagRun).where(
        AirflowDagRun.dag_id == payload["dag_id"],
        AirflowDagRun.dag_run_id == payload["dag_run_id"],
    ))).scalar_one_or_none()
    if not dag_run:
        dag_run = AirflowDagRun(
            dag_id=payload["dag_id"], dag_run_id=payload["dag_run_id"],
            run_type=payload.get("run_type"), state=payload.get("dag_state") or "running",
            execution_date=payload.get("execution_date"), start_date=payload.get("start_date"),
        )
        db.add(dag_run)
        await db.flush()
    elif payload.get("dag_state"):
        dag_run.state = payload["dag_state"]

    sql = payload.get("sql") or ""
    sql_hash = hashlib.sha256(sql.encode("utf-8")).hexdigest() if sql else None
    task_run = (await db.execute(select(AirflowTaskRun).where(
        AirflowTaskRun.dag_id == payload["dag_id"],
        AirflowTaskRun.dag_run_id == payload["dag_run_id"],
        AirflowTaskRun.task_id == payload["task_id"],
        AirflowTaskRun.try_number == payload.get("try_number", 1),
    ))).scalar_one_or_none()
    if not task_run:
        task_run = AirflowTaskRun(
            dag_run_record_id=dag_run.id, dag_id=payload["dag_id"],
            dag_run_id=payload["dag_run_id"], task_id=payload["task_id"],
            try_number=payload.get("try_number", 1), state=payload["state"],
        )
        db.add(task_run)
        await db.flush()
    if payload.get("operator_type"):
        task_run.operator_type = payload["operator_type"]
    if task_run.state not in {"success", "failed"} or payload["state"] in {"success", "failed"}:
        task_run.state = payload["state"]
    if sql:
        task_run.executed_sql = sql
        task_run.sql_hash = sql_hash
    if payload.get("affected_rows") is not None:
        task_run.affected_rows = payload["affected_rows"]
    if payload.get("error_message"):
        task_run.error_message = payload["error_message"]
    if payload.get("start_date") and (
        payload.get("start_date_authoritative")
        or task_run.start_date is None
        or payload["start_date"] < task_run.start_date
    ):
        task_run.start_date = payload["start_date"]
    if payload.get("end_date"):
        task_run.end_date = payload["end_date"]
    elif payload["state"] in {"success", "failed"}:
        task_run.end_date = now
    if payload.get("openlineage_run_id"):
        task_run.openlineage_run_id = payload["openlineage_run_id"]
    if payload.get("openlineage_job_namespace"):
        task_run.openlineage_job_namespace = payload["openlineage_job_namespace"]
    if payload.get("openlineage_job_name"):
        task_run.openlineage_job_name = payload["openlineage_job_name"]
    if task_run.start_date and task_run.end_date:
        task_run.duration_seconds = max(int((task_run.end_date - task_run.start_date).total_seconds()), 0)

    default_database = payload.get("default_database")
    explicit_inputs = _explicit_refs(payload.get("input_tables") or [], default_database)
    explicit_outputs = _explicit_refs(payload.get("output_tables") or [], default_database)
    input_datasets = _dedupe_datasets(
        (task_run.openlineage_inputs or []) + (payload.get("input_datasets") or [])
    )
    output_datasets = _dedupe_datasets(
        (task_run.openlineage_outputs or []) + (payload.get("output_datasets") or [])
    )
    if "input_datasets" in payload or payload.get("merge_lineage"):
        task_run.openlineage_inputs = input_datasets
    if "output_datasets" in payload or payload.get("merge_lineage"):
        task_run.openlineage_outputs = output_datasets
    dataset_inputs = _dataset_refs(input_datasets, default_database)
    dataset_outputs = _dataset_refs(output_datasets, default_database)
    has_both_sides = (explicit_inputs or dataset_inputs) and (explicit_outputs or dataset_outputs)
    parsed_inputs, parsed_outputs = (
        ([], []) if has_both_sides else parse_runtime_sql(sql, default_database)
    )
    input_refs = _dedupe_refs(dataset_inputs + explicit_inputs + parsed_inputs)
    output_refs = _dedupe_refs(dataset_outputs + explicit_outputs + parsed_outputs)
    if payload.get("merge_lineage"):
        input_refs = _dedupe_refs(_explicit_refs(task_run.input_tables or [], default_database) + input_refs)
        output_refs = _dedupe_refs(_explicit_refs(task_run.output_tables or [], default_database) + output_refs)
    task_run.input_tables = [".".join(filter(None, [ref.get("database"), ref["name"]])) for ref in input_refs]
    task_run.output_tables = [".".join(filter(None, [ref.get("database"), ref["name"]])) for ref in output_refs]

    resolved_inputs = [(ref, await _resolve_asset(db, ref, payload.get("datasource_name"))) for ref in input_refs]
    resolved_outputs = [(ref, await _resolve_asset(db, ref, payload.get("datasource_name"))) for ref in output_refs]
    unresolved = [ref for ref, asset in resolved_inputs + resolved_outputs if not asset]
    created_events = 0
    if payload["state"] == "success":
        for _, source in resolved_inputs:
            if not source:
                continue
            for _, target in resolved_outputs:
                if not target or target.id == source.id:
                    continue
                event = (await db.execute(select(LineageRunEvent).where(
                    LineageRunEvent.task_run_id == task_run.id,
                    LineageRunEvent.source_asset_id == source.id,
                    LineageRunEvent.target_asset_id == target.id,
                ))).scalar_one_or_none()
                if event:
                    continue
                db.add(LineageRunEvent(
                    task_run_id=task_run.id, source_asset_id=source.id, target_asset_id=target.id,
                    dag_id=payload["dag_id"], dag_run_id=payload["dag_run_id"],
                    task_id=payload["task_id"], sql_hash=sql_hash, occurred_at=now,
                ))
                edge = (await db.execute(select(AssetLineageEdge).where(
                    AssetLineageEdge.source_asset_id == source.id,
                    AssetLineageEdge.target_asset_id == target.id,
                    AssetLineageEdge.source_type == "runtime",
                ))).scalar_one_or_none()
                if not edge:
                    edge = AssetLineageEdge(
                        source_asset_id=source.id, target_asset_id=target.id,
                        lineage_type="table", source_type="runtime", confidence=100,
                        status="active", first_seen_at=now, success_count=0,
                    )
                    db.add(edge)
                edge.last_seen_at = now
                edge.success_count += 1
                edge.last_dag_run_id = payload["dag_run_id"]
                edge.last_task_id = payload["task_id"]
                created_events += 1

    runs = list((await db.execute(select(AirflowTaskRun).where(
        AirflowTaskRun.dag_run_record_id == dag_run.id
    ))).scalars().all())
    dag_run.task_count = len(runs)
    dag_run.success_task_count = sum(1 for run in runs if run.state == "success")
    dag_run.failed_task_count = sum(1 for run in runs if run.state == "failed")
    dag_run.input_asset_count = len({name for run in runs for name in (run.input_tables or [])})
    dag_run.output_asset_count = len({name for run in runs for name in (run.output_tables or [])})
    successful_runs = [run for run in runs if run.state == "success"]
    has_complete_lineage = any(run.input_tables and run.output_tables for run in successful_runs)
    has_incomplete_lineage = any(bool(run.input_tables) != bool(run.output_tables) for run in successful_runs)
    if has_complete_lineage:
        dag_run.lineage_status = "partial" if unresolved else "collected"
    elif has_incomplete_lineage:
        dag_run.lineage_status = "partial"
    elif any(run.state == "running" for run in runs):
        dag_run.lineage_status = "pending"
    else:
        dag_run.lineage_status = "none"
    dag_run.lineage_collected_at = now
    await db.commit()
    return {
        "task_run_id": str(task_run.id), "state": task_run.state,
        "inputs": task_run.input_tables, "outputs": task_run.output_tables,
        "created_events": created_events,
        "unresolved": [".".join(filter(None, [ref.get("database"), ref["name"]])) for ref in unresolved],
    }
