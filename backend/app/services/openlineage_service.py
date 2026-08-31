"""Receive OpenLineage RunEvents and merge them into DataMind runtime lineage."""
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AirflowTaskRun
from app.services.runtime_lineage_service import ingest_event


def _mapping(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _iso_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        text = str(value)
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        result = datetime.fromisoformat(text)
        return result.replace(tzinfo=timezone.utc) if result.tzinfo is None else result
    except (TypeError, ValueError):
        return None


def extract_airflow_identity(event: dict) -> dict | None:
    """Extract Airflow identifiers from the standard AirflowRunFacet."""
    run = _mapping(event.get("run"))
    facets = _mapping(run.get("facets"))
    airflow = _mapping(facets.get("airflow"))
    dag = _mapping(airflow.get("dag"))
    dag_run = _mapping(airflow.get("dagRun"))
    task = _mapping(airflow.get("task"))
    task_instance = _mapping(airflow.get("taskInstance"))
    job = _mapping(event.get("job"))

    dag_id = dag_run.get("dag_id") or dag.get("dag_id")
    dag_run_id = dag_run.get("run_id")
    task_id = task.get("task_id")
    job_name = str(job.get("name") or "")
    if (not dag_id or not task_id) and "." in job_name:
        fallback_dag, fallback_task = job_name.rsplit(".", 1)
        dag_id = dag_id or fallback_dag
        task_id = task_id or fallback_task
    if not dag_id or not dag_run_id or not task_id:
        return None

    try_number = task_instance.get("try_number") or 1
    try:
        try_number = max(int(try_number), 1)
    except (TypeError, ValueError):
        try_number = 1
    return {
        "dag_id": str(dag_id),
        "dag_run_id": str(dag_run_id),
        "task_id": str(task_id),
        "try_number": try_number,
        "run_type": str(dag_run.get("run_type")) if dag_run.get("run_type") else None,
        "execution_date": _iso_datetime(dag_run.get("logical_date") or dag_run.get("execution_date")),
        # dagRun.start_date is the start of the whole DAG and is identical for
        # every task.  Using it here collapses all task nodes into one visual
        # stage and inflates task durations.  Prefer the task-instance time;
        # when the facet does not provide one, the START event time is used by
        # ingest_openlineage_event below.
        "start_date": _iso_datetime(
            task_instance.get("start_date") or task_instance.get("startDate")
        ),
        "operator_type": task.get("operator_class") or task.get("operator_class_path"),
        "openlineage_run_id": str(run.get("runId")) if run.get("runId") else None,
        "openlineage_job_namespace": str(job.get("namespace")) if job.get("namespace") else None,
        "openlineage_job_name": job_name or None,
    }


def extract_parent_run_id(event: dict) -> str | None:
    facets = _mapping(_mapping(event.get("run")).get("facets"))
    parent = _mapping(facets.get("parent"))
    parent_run = _mapping(parent.get("run"))
    return str(parent_run.get("runId")) if parent_run.get("runId") else None


def extract_datasets(event: dict, key: str) -> list[dict]:
    datasets = event.get(key)
    if not isinstance(datasets, list):
        return []
    result = []
    seen = set()
    for item in datasets:
        dataset = _mapping(item)
        namespace = str(dataset.get("namespace") or "").strip()
        name = str(dataset.get("name") or "").strip()
        identity = (namespace.lower(), name.lower())
        if name and identity not in seen:
            result.append({"namespace": namespace, "name": name})
            seen.add(identity)
    return result


def _state(event_type: Any) -> str:
    normalized = str(event_type or "").upper()
    if normalized == "COMPLETE":
        return "success"
    if normalized in {"FAIL", "ABORT"}:
        return "failed"
    return "running"


async def ingest_openlineage_event(db: AsyncSession, event: dict) -> dict:
    """Correlate Airflow and Spark child events, then persist table lineage."""
    identity = extract_airflow_identity(event)
    parent_run_id = extract_parent_run_id(event)
    is_child_event = identity is None and parent_run_id is not None
    if is_child_event:
        parent = (await db.execute(
            select(AirflowTaskRun)
            .where(AirflowTaskRun.openlineage_run_id == parent_run_id)
            .order_by(AirflowTaskRun.updated_at.desc())
            .limit(1)
        )).scalar_one_or_none()
        if not parent:
            return {"accepted": True, "matched": False, "reason": "parent_run_not_received"}
        identity = {
            "dag_id": parent.dag_id,
            "dag_run_id": parent.dag_run_id,
            "task_id": parent.task_id,
            "try_number": parent.try_number,
            "operator_type": parent.operator_type,
        }
        event_state = parent.state if parent.state in {"success", "failed"} else "running"
    else:
        event_state = _state(event.get("eventType"))

    if not identity:
        return {"accepted": True, "matched": False, "reason": "missing_airflow_identity"}

    event_time = _iso_datetime(event.get("eventTime")) or datetime.now(timezone.utc)
    payload = {
        **identity,
        "state": event_state,
        "input_datasets": extract_datasets(event, "inputs"),
        "output_datasets": extract_datasets(event, "outputs"),
        "start_date": identity.get("start_date") or (
            event_time if not is_child_event and event_state == "running" else None
        ),
        "end_date": event_time if event_state in {"success", "failed"} else None,
        "merge_lineage": True,
        "error_message": "OpenLineage event reported task failure" if event_state == "failed" else None,
    }
    result = await ingest_event(db, payload)
    return {
        "accepted": True,
        "matched": True,
        "child_event": is_child_event,
        "event_type": str(event.get("eventType") or ""),
        **result,
    }
