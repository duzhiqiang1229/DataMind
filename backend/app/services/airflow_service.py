"""Airflow DAG management service: list, trigger, pause/resume, logs, retry."""
import os
import re
import uuid
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.services.component_service import get_airflow_client


def _slugify(name: str) -> str:
    """Turn a script name into a safe file-name fragment."""
    s = re.sub(r"[^A-Za-z0-9_\-]+", "_", (name or "").strip()).strip("_")
    return s or "dag"


def _dags_root() -> Path:
    root = Path(os.getenv("AIRFLOW_DAGS_PATH", "/airflow/dags")).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _dag_file(fileloc: str) -> Path:
    """Map Airflow's container path to the shared local DAG directory."""
    filename = Path(fileloc).name
    if not filename.endswith(".py") or filename in {".py", "..py"}:
        raise ValueError("无效的 DAG 文件路径")
    return _dags_root() / filename


def _read_dag_file(fileloc: str) -> str | None:
    path = _dag_file(fileloc)
    return path.read_text(encoding="utf-8") if path.is_file() else None


def _write_dag_file(fileloc: str, content: str) -> None:
    _dag_file(fileloc).write_text(content, encoding="utf-8", newline="\n")


async def create_dag_file(db: AsyncSession, script_name: str, content: str) -> dict:
    """Write a new scheduling script (.py) into the Airflow dags folder.

    The file is a self-contained Airflow DAG definition; the scheduler parses
    it automatically, so DAG name / schedule / status come from the script.
    """
    if not content or not content.strip():
        raise ValueError("脚本内容不能为空")
    filename = f"datamind_{_slugify(script_name)}_{uuid.uuid4().hex[:8]}.py"
    local_path = _dags_root() / filename
    local_path.write_text(content, encoding="utf-8", newline="\n")
    return {"fileloc": f"/opt/airflow/dags/{filename}", "filename": filename}


async def get_dag_file(db: AsyncSession, dag_id: str) -> Optional[dict]:
    """Read the source file of a DAG from the Airflow node."""
    dag = await get_dag(db, dag_id)
    if not dag:
        return None
    fileloc = dag.get("fileloc")
    if not fileloc:
        return None
    content = _read_dag_file(fileloc)
    if content is None:
        return None
    return {"dag_id": dag_id, "fileloc": fileloc, "content": content}


async def update_dag_file(db: AsyncSession, dag_id: str, content: str) -> Optional[dict]:
    """Overwrite the source file of a DAG; Airflow re-parses automatically."""
    if not content or not content.strip():
        raise ValueError("脚本内容不能为空")
    dag = await get_dag(db, dag_id)
    if not dag:
        return None
    fileloc = dag.get("fileloc")
    if not fileloc:
        return None
    _write_dag_file(fileloc, content)
    return {"dag_id": dag_id, "fileloc": fileloc}


async def list_dags(db: AsyncSession, limit: int = 100, offset: int = 0) -> list[dict]:
    """List all DAGs from Airflow.

    Args:
        db: Database session (used to load Airflow component config).
        limit: Maximum number of DAGs to return.
        offset: Pagination offset.

    Returns:
        List of DAG dictionaries. Returns an empty list if Airflow is not
        configured or the request fails.
    """
    try:
        client = await get_airflow_client(db)
        return await client.list_dags(limit=limit, offset=offset)
    except RuntimeError as e:
        logger.warning(f"[airflow] list_dags skipped: {e}")
        return []
    except Exception as e:
        logger.error(f"[airflow] list_dags failed: {e}")
        return []


async def get_dag(db: AsyncSession, dag_id: str) -> Optional[dict]:
    """Get details of a specific DAG.

    Args:
        db: Database session.
        dag_id: The DAG identifier.

    Returns:
        DAG detail dictionary, or None if Airflow is not configured / DAG not found.
    """
    try:
        client = await get_airflow_client(db)
        return await client.get_dag(dag_id)
    except RuntimeError as e:
        logger.warning(f"[airflow] get_dag skipped: {e}")
        return None
    except Exception as e:
        logger.error(f"[airflow] get_dag failed: {e}")
        return None


async def pause_dag(db: AsyncSession, dag_id: str) -> Optional[dict]:
    """Pause a DAG so it will no longer be scheduled.

    Args:
        db: Database session.
        dag_id: The DAG identifier.

    Returns:
        Updated DAG dictionary, or None on failure.
    """
    try:
        client = await get_airflow_client(db)
        return await client.patch_dag(dag_id, is_paused=True)
    except RuntimeError as e:
        logger.warning(f"[airflow] pause_dag skipped: {e}")
        return None
    except Exception as e:
        logger.error(f"[airflow] pause_dag failed: {e}")
        return None


async def resume_dag(db: AsyncSession, dag_id: str) -> Optional[dict]:
    """Resume (unpause) a DAG so the scheduler picks it up again.

    Args:
        db: Database session.
        dag_id: The DAG identifier.

    Returns:
        Updated DAG dictionary, or None on failure.
    """
    try:
        client = await get_airflow_client(db)
        return await client.patch_dag(dag_id, is_paused=False)
    except RuntimeError as e:
        logger.warning(f"[airflow] resume_dag skipped: {e}")
        return None
    except Exception as e:
        logger.error(f"[airflow] resume_dag failed: {e}")
        return None


async def trigger_dag(db: AsyncSession, dag_id: str, conf: Optional[dict] = None) -> Optional[dict]:
    """Trigger a new DAG run with optional configuration.

    Args:
        db: Database session.
        dag_id: The DAG identifier.
        conf: Optional configuration parameters passed to the DAG run.

    Returns:
        DAG run info dictionary (includes state, run_id, etc.), or None on failure.
    """
    try:
        client = await get_airflow_client(db)
        return await client.trigger_dag_run(dag_id, conf=conf)
    except RuntimeError as e:
        logger.warning(f"[airflow] trigger_dag skipped: {e}")
        return None
    except Exception as e:
        logger.error(f"[airflow] trigger_dag failed: {e}")
        return None


async def list_dag_runs(
    db: AsyncSession, dag_id: str, limit: int = 50, offset: int = 0
) -> list[dict]:
    """List recent DAG runs for a given DAG.

    Args:
        db: Database session.
        dag_id: The DAG identifier.
        limit: Maximum number of runs to return.
        offset: Pagination offset.

    Returns:
        List of DAG run dictionaries. Empty list on failure.
    """
    try:
        client = await get_airflow_client(db)
        return await client.list_dag_runs(dag_id, limit=limit, offset=offset)
    except RuntimeError as e:
        logger.warning(f"[airflow] list_dag_runs skipped: {e}")
        return []
    except Exception as e:
        logger.error(f"[airflow] list_dag_runs failed: {e}")
        return []


async def get_dag_run_detail(db: AsyncSession, dag_id: str, run_id: str) -> Optional[dict]:
    """Get DAG run detail including its task instances.

    Combines the DAG run info and the task instances list into a single
    response payload for convenience.

    Args:
        db: Database session.
        dag_id: The DAG identifier.
        run_id: The DAG run identifier.

    Returns:
        Dictionary with ``run`` (DAG run info) and ``task_instances`` keys,
        or None on failure.
    """
    try:
        client = await get_airflow_client(db)
        run = await client.get_dag_run(dag_id, run_id)
        task_instances = await client.get_task_instances(dag_id, run_id)
        return {
            "run": run,
            "task_instances": task_instances,
        }
    except RuntimeError as e:
        logger.warning(f"[airflow] get_dag_run_detail skipped: {e}")
        return None
    except Exception as e:
        logger.error(f"[airflow] get_dag_run_detail failed: {e}")
        return None


async def get_dag_run_log(
    db: AsyncSession, dag_id: str, run_id: str, task_id: str, try_number: int = 1
) -> str:
    """Fetch execution log text for a specific task instance.

    Args:
        db: Database session.
        dag_id: The DAG identifier.
        run_id: The DAG run identifier.
        task_id: The task instance identifier.
        try_number: The attempt number (1-based). Defaults to 1.

    Returns:
        Log text. Empty string on failure.
    """
    try:
        client = await get_airflow_client(db)
        return await client.get_task_log(
            dag_id, run_id, task_id, try_number=try_number
        )
    except RuntimeError as e:
        logger.warning(f"[airflow] get_dag_run_log skipped: {e}")
        return ""
    except Exception as e:
        logger.error(f"[airflow] get_dag_run_log failed: {e}")
        return ""


async def retry_dag_run(
    db: AsyncSession, dag_id: str, run_id: str, task_id: str
) -> dict:
    """Retry a failed task instance within a DAG run.

    Clear the selected failed task through Airflow's stable
    ``clearTaskInstances`` endpoint. Once cleared, the scheduler picks the
    task up and re-executes it.

    Args:
        db: Database session.
        dag_id: The DAG identifier.
        run_id: The DAG run identifier.
        task_id: The task instance to retry.

    Returns:
        Dictionary describing the retry outcome::

            {"success": bool, "dag_id": str, "run_id": str,
             "task_id": str, "message": str, "detail": dict | None}
    """
    result: dict[str, Any] = {
        "success": False,
        "dag_id": dag_id,
        "run_id": run_id,
        "task_id": task_id,
        "message": "",
        "detail": None,
    }

    try:
        client = await get_airflow_client(db)
        # Airflow 2.x only accepts success/failed/skipped in the single-task
        # state endpoint. Retrying must use the dedicated clear endpoint.
        resp = await client._request(
            "POST",
            f"/api/v2/dags/{dag_id}/clearTaskInstances",
            json={
                "dag_run_id": run_id,
                "task_ids": [task_id],
                "only_failed": True,
                "include_downstream": True,
                "reset_dag_runs": True,
                "dry_run": False,
            },
        )
        detail = resp.json() if resp.content else {}
        result["success"] = True
        result["detail"] = detail
        result["message"] = (
            f"Task instance '{task_id}' in run '{run_id}' cleared for retry. "
            "The Airflow scheduler will pick it up shortly."
        )
        logger.info(
            f"[airflow] retry_dag_run: cleared task {task_id} "
            f"in dag={dag_id} run={run_id}"
        )
    except RuntimeError as e:
        result["message"] = f"Airflow not configured: {e}"
        logger.warning(f"[airflow] retry_dag_run skipped: {e}")
    except Exception as e:
        result["message"] = f"Failed to retry task instance: {e}"
        logger.error(f"[airflow] retry_dag_run failed: {e}")

    return result


async def update_dag_schedule(db: AsyncSession, dag_id: str, schedule_interval: str) -> dict | None:
    """Update the schedule in the shared DAG source file."""
    try:
        source = await get_dag_file(db, dag_id)
        if not source:
            return None
        replacement = repr(schedule_interval) if schedule_interval else "None"
        content, count = re.subn(
            r"(?m)(\bschedule\s*=\s*)([^,\n)]+)",
            lambda match: match.group(1) + replacement,
            source["content"], count=1,
        )
        if count == 0:
            content, count = re.subn(
                r"(?m)(\bschedule_interval\s*=\s*)([^,\n)]+)",
                lambda match: match.group(1) + replacement,
                source["content"], count=1,
            )
        if count == 0:
            raise ValueError("DAG 脚本中未找到 schedule 配置")
        _write_dag_file(source["fileloc"], content)
        return {"dag_id": dag_id, "schedule": schedule_interval, "fileloc": source["fileloc"]}
    except RuntimeError:
        return None
    except Exception as e:
        logger.error(f"Failed to update DAG schedule: {e}")
        return None


async def sync_dag_runs(db: AsyncSession) -> dict:
    """Sync runs and actively collect task-level runtime lineage from Airflow."""
    from datetime import datetime, timezone

    from app.models import AirflowDagRun
    from app.services.component_service import get_airflow_client
    from app.services.runtime_lineage_service import ingest_event

    def _parse(iso):
        if not iso:
            return None
        try:
            s = str(iso)
            if s.endswith("Z"):
                s = s[:-1] + "+00:00"
            dt = datetime.fromisoformat(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            return None

    try:
        airflow = await get_airflow_client(db)
    except RuntimeError as e:
        logger.warning(f"[airflow] sync_dag_runs skipped: {e}")
        return {"synced": 0, "dags": 0}

    dags = await airflow.list_dags(limit=100)
    total = 0
    lineage_candidates: list[dict] = []
    for dag in dags:
        dag_id = dag.get("dag_id")
        if not dag_id:
            continue
        try:
            runs = await airflow.list_dag_runs(dag_id, limit=50)
        except Exception:
            continue
        for run in runs:
            run_id = run.get("dag_run_id")
            if not run_id:
                continue
            start = _parse(run.get("start_date"))
            end = _parse(run.get("end_date"))
            duration = int((end - start).total_seconds()) if start and end else None

            existing = await db.execute(
                select(AirflowDagRun).where(
                    AirflowDagRun.dag_id == dag_id,
                    AirflowDagRun.dag_run_id == run_id,
                )
            )
            row = existing.scalar_one_or_none()
            if row:
                row.state = run.get("state")
                row.start_date = start
                row.end_date = end
                row.duration_seconds = duration
                row.run_type = run.get("run_type")
                row.execution_date = _parse(run.get("logical_date") or run.get("execution_date"))
            else:
                row = AirflowDagRun(
                    dag_id=dag_id,
                    dag_run_id=run_id,
                    run_type=run.get("run_type"),
                    state=run.get("state"),
                    execution_date=_parse(run.get("logical_date") or run.get("execution_date")),
                    start_date=start,
                    end_date=end,
                    duration_seconds=duration,
                )
                db.add(row)
            if run.get("state") in {"success", "failed"} and row.lineage_status == "pending":
                lineage_candidates.append({
                    "dag_id": dag_id, "dag_run_id": run_id, "dag_state": run.get("state"),
                    "run_type": run.get("run_type"),
                    "execution_date": _parse(run.get("logical_date") or run.get("execution_date")),
                })
            total += 1
    await db.commit()

    def _extract_log_lineage(log: str) -> tuple[list[str], list[str], str]:
        """Extract physical reads/writes and SQL from concrete task execution logs."""
        inputs = {
            match.lower() for match in re.findall(
                r"(?i)(?:get query plan for table|BatchScan)\s+[`\"]?([A-Za-z0-9_]+\.[A-Za-z0-9_]+)",
                log or "",
            )
        }
        outputs = {
            match.lower() for match in re.findall(
                r"(?im)INFO\s+-\s+([A-Za-z0-9_]+\.[A-Za-z0-9_]+):\s+(?:load_completed|write_completed|transformed_rows)\b",
                log or "",
            )
        }
        sql_parts = []
        for match in re.findall(
            r"(?im)(?:Executing|Running)\s+statement:\s*(.+?)(?:,\s*parameters:.*)?$", log or ""
        ):
            statement = match.strip()
            if statement and statement not in sql_parts:
                sql_parts.append(statement)
        return sorted(inputs - outputs), sorted(outputs), ";\n".join(sql_parts)

    collected_tasks = 0
    lineage_errors = 0
    # Bound each sync so large task logs cannot monopolize the API.
    candidate_limit = 3
    for candidate in lineage_candidates[:candidate_limit]:
        try:
            tasks = await airflow.get_task_instances(candidate["dag_id"], candidate["dag_run_id"])
        except Exception as exc:
            logger.warning(f"[airflow] task sync failed for {candidate['dag_id']}: {exc}")
            lineage_errors += 1
            continue
        for task in tasks:
            state = task.get("state")
            if state not in {"success", "failed", "upstream_failed"}:
                continue
            task_id = task.get("task_id")
            if not task_id:
                continue
            log = ""
            try:
                log = await airflow.get_task_log(
                    candidate["dag_id"], candidate["dag_run_id"], task_id,
                    max(int(task.get("try_number") or 1), 1),
                )
            except Exception as exc:
                logger.debug(f"[airflow] task log unavailable for {task_id}: {exc}")
            input_tables, output_tables, executed_sql = _extract_log_lineage(log)
            try:
                await ingest_event(db, {
                    **candidate, "task_id": task_id,
                    "try_number": max(int(task.get("try_number") or 1), 1),
                    "state": "success" if state == "success" else "failed",
                    "operator_type": task.get("operator_name") or task.get("operator"),
                    "sql": executed_sql,
                    "input_tables": input_tables, "output_tables": output_tables,
                    "start_date": _parse(task.get("start_date")),
                    "end_date": _parse(task.get("end_date")),
                    "error_message": None if state == "success" else f"Airflow task state: {state}",
                })
                collected_tasks += 1
            except Exception as exc:
                await db.rollback()
                lineage_errors += 1
                logger.warning(f"[airflow] runtime lineage ingest failed for {task_id}: {exc}")
    logger.info(
        f"[airflow] synced {total} runs from {len(dags)} dags; collected {collected_tasks} task records"
    )
    return {
        "synced": total, "dags": len(dags), "lineage_tasks": collected_tasks,
        "lineage_candidates": min(len(lineage_candidates), candidate_limit), "lineage_errors": lineage_errors,
    }


async def list_dag_runs_page(
    db: AsyncSession, page: int, page_size: int,
    dag_id: Optional[str] = None, status: Optional[str] = None,
) -> tuple[list[dict], int]:
    """Paginated list of synced Airflow DAG runs."""
    from app.models import AirflowDagRun

    query = select(AirflowDagRun)
    count_q = select(func.count(AirflowDagRun.id))
    if dag_id:
        query = query.where(AirflowDagRun.dag_id == dag_id)
        count_q = count_q.where(AirflowDagRun.dag_id == dag_id)
    if status:
        query = query.where(AirflowDagRun.state == status)
        count_q = count_q.where(AirflowDagRun.state == status)

    total = (await db.execute(count_q)).scalar_one()
    result = await db.execute(
        query.order_by(AirflowDagRun.start_date.desc().nullslast())
        .offset((page - 1) * page_size).limit(page_size)
    )
    items = []
    for r in result.scalars().all():
        items.append({
            "id": str(r.id),
            "dag_id": r.dag_id,
            "dag_run_id": r.dag_run_id,
            "run_type": r.run_type,
            "state": r.state,
            "execution_date": r.execution_date.isoformat() if r.execution_date else None,
            "start_date": r.start_date.isoformat() if r.start_date else None,
            "end_date": r.end_date.isoformat() if r.end_date else None,
            "duration_seconds": r.duration_seconds,
            "task_count": r.task_count,
            "success_task_count": r.success_task_count,
            "failed_task_count": r.failed_task_count,
            "input_asset_count": r.input_asset_count,
            "output_asset_count": r.output_asset_count,
            "lineage_status": r.lineage_status,
            "lineage_collected_at": r.lineage_collected_at.isoformat() if r.lineage_collected_at else None,
        })
    return items, total


async def list_recorded_task_runs(db: AsyncSession, dag_run_record_id: uuid.UUID) -> list[dict]:
    """Return task-level callback records belonging to a synced DAG run."""
    from app.models import AirflowTaskRun

    rows = list((await db.execute(
        select(AirflowTaskRun)
        .where(AirflowTaskRun.dag_run_record_id == dag_run_record_id)
        .order_by(AirflowTaskRun.start_date.asc().nullsfirst(), AirflowTaskRun.task_id)
    )).scalars().all())
    return [{
        "id": str(row.id), "task_id": row.task_id, "try_number": row.try_number,
        "operator_type": row.operator_type, "state": row.state,
        "input_tables": row.input_tables or [], "output_tables": row.output_tables or [],
        "affected_rows": row.affected_rows, "error_message": row.error_message,
        "start_date": row.start_date.isoformat() if row.start_date else None,
        "end_date": row.end_date.isoformat() if row.end_date else None,
        "duration_seconds": row.duration_seconds,
    } for row in rows]
