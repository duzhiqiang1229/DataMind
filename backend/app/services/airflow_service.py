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


async def _airflow_ssh_config(db: AsyncSession) -> dict:
    """Load SSH connection params for the Airflow node."""
    from app.services.component_service import _load_config

    config = await _load_config(db, "airflow")
    if not config:
        raise RuntimeError("Airflow component not configured")
    ssh_password = config.get("ssh_password") or ""
    if not ssh_password:
        raise ValueError("请先在 Airflow 组件配置中填写 SSH 密码")
    return {
        "host": config.get("ssh_host") or "192.168.1.4",
        "port": int(config.get("ssh_port") or 22),
        "user": config.get("ssh_user") or "root",
        "password": ssh_password,
        "dags_path": (config.get("dags_path") or "/home/airflow/dags").rstrip("/"),
    }


async def _read_remote_file(db: AsyncSession, remote_path: str) -> str | None:
    """Read a text file from the Airflow node via SFTP."""
    import paramiko

    ssh_cfg = await _airflow_ssh_config(db)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        ssh_cfg["host"], port=ssh_cfg["port"],
        username=ssh_cfg["user"], password=ssh_cfg["password"], timeout=15,
    )
    try:
        with client.open_sftp() as sftp:
            with sftp.open(remote_path, "r") as f:
                return f.read().decode("utf-8", errors="replace")
    except FileNotFoundError:
        return None
    finally:
        client.close()


async def _write_remote_file(db: AsyncSession, remote_path: str, content: str) -> None:
    """Write a text file to the Airflow node via SFTP (UTF-8)."""
    import paramiko

    ssh_cfg = await _airflow_ssh_config(db)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        ssh_cfg["host"], port=ssh_cfg["port"],
        username=ssh_cfg["user"], password=ssh_cfg["password"], timeout=15,
    )
    try:
        with client.open_sftp() as sftp:
            with sftp.open(remote_path, "w") as f:
                f.write(content.encode("utf-8"))
    finally:
        client.close()


async def create_dag_file(db: AsyncSession, script_name: str, content: str) -> dict:
    """Write a new scheduling script (.py) into the Airflow dags folder.

    The file is a self-contained Airflow DAG definition; the scheduler parses
    it automatically, so DAG name / schedule / status come from the script.
    """
    if not content or not content.strip():
        raise ValueError("脚本内容不能为空")
    ssh_cfg = await _airflow_ssh_config(db)
    filename = f"datamind_{_slugify(script_name)}_{uuid.uuid4().hex[:8]}.py"
    remote_path = f"{ssh_cfg['dags_path']}/{filename}"
    await _write_remote_file(db, remote_path, content)
    return {"fileloc": remote_path, "filename": filename}


async def get_dag_file(db: AsyncSession, dag_id: str) -> Optional[dict]:
    """Read the source file of a DAG from the Airflow node."""
    dag = await get_dag(db, dag_id)
    if not dag:
        return None
    fileloc = dag.get("fileloc")
    if not fileloc:
        return None
    content = await _read_remote_file(db, fileloc)
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
    await _write_remote_file(db, fileloc, content)
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
            f"/api/v1/dags/{dag_id}/clearTaskInstances",
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
    """Update DAG schedule interval via Airflow PATCH API."""
    try:
        airflow = await get_airflow_client(db)
        # Use the client's _request method to PATCH the DAG with new schedule
        resp = await airflow._request("PATCH", f"/api/v1/dags/{dag_id}", json={"schedule_interval": schedule_interval})
        return resp.json()
    except RuntimeError:
        return None
    except Exception as e:
        logger.error(f"Failed to update DAG schedule: {e}")
        return None


async def deploy_dags(db: AsyncSession) -> dict:
    """Deploy DAG template files to the Airflow dags folder via SSH/SFTP.

    The SSH connection details (ssh_host/ssh_port/ssh_user/ssh_password/dags_path)
    are stored in the Airflow component config.
    """
    import paramiko

    from app.services.component_service import _load_config

    config = await _load_config(db, "airflow")
    if not config:
        raise RuntimeError("Airflow component not configured")

    ssh_host = config.get("ssh_host") or "192.168.1.4"
    ssh_port = int(config.get("ssh_port") or 22)
    ssh_user = config.get("ssh_user") or "root"
    ssh_password = config.get("ssh_password") or ""
    dags_path = config.get("dags_path") or "/opt/software/airflow/dags"

    if not ssh_password:
        raise ValueError("请先在 Airflow 组件配置中填写 SSH 密码")

    dags_dir = Path(
        os.environ.get("AIRFLOW_DAGS_DIR")
        or (Path(__file__).resolve().parents[3] / "airflow-dags")
    )
    files = ["datax_sync_dag.py", "spark_job_dag.py"]

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        ssh_host, port=ssh_port, username=ssh_user,
        password=ssh_password, timeout=15,
    )
    sftp = client.open_sftp()
    try:
        try:
            sftp.stat(dags_path)
        except FileNotFoundError:
            sftp.mkdir(dags_path)

        uploaded = []
        for f in files:
            src = dags_dir / f
            if not src.exists():
                continue
            remote = f"{dags_path.rstrip('/')}/{f}"
            sftp.put(str(src), remote)
            uploaded.append(remote)
    finally:
        sftp.close()
        client.close()

    logger.info(f"[airflow] DAG templates deployed to {dags_path}: {uploaded}")
    return {
        "uploaded": uploaded,
        "dags_path": dags_path,
        "ssh_host": ssh_host,
    }


async def create_dag_task(
    db: AsyncSession,
    dag_name: str,
    task_type: str,
    task_id: str,
    schedule: str,
    description: Optional[str] = None,
) -> dict:
    """Create a scheduled DAG that triggers a DataX/Spark task.

    Generates a DAG definition file (using TriggerDagRunOperator to fire the
    matching datax_sync / spark_job template with the task id) and uploads it
    to the Airflow dags folder via SFTP.
    """
    import uuid
    import paramiko

    from app.models import DataXTask, SparkTask
    from app.services.component_service import _load_config

    # Load the target task to validate and get its code
    task = None
    if task_type == "datax":
        result = await db.execute(
            select(DataXTask).where(DataXTask.id == uuid.UUID(task_id))
        )
        task = result.scalar_one_or_none()
        trigger_dag_id = "datax_sync"
        task_label = "DataX"
    elif task_type == "spark":
        result = await db.execute(
            select(SparkTask).where(SparkTask.id == uuid.UUID(task_id))
        )
        task = result.scalar_one_or_none()
        trigger_dag_id = "spark_job"
        task_label = "Spark"
    else:
        raise ValueError("task_type 必须是 datax 或 spark")

    if not task:
        raise ValueError("任务不存在")

    task_code = getattr(task, "task_code", "") or str(uuid.UUID(task_id))
    dag_id = f"datamind_{task_type}_{task_code}"

    # Build the DAG definition file content
    content = (
        f'"""DataMind scheduled DAG: {dag_name}"""\n'
        "from airflow import DAG\n"
        "from airflow.operators.trigger_dagrun import TriggerDagRunOperator\n"
        "from airflow.utils.dates import days_ago\n"
        "\n"
        "default_args = {\n"
        '    "owner": "datamind",\n'
        '    "retries": 0,\n'
        "}\n"
        "\n"
        f"dag = DAG(\n"
        f'    dag_id="{dag_id}",\n'
        f'    description="{dag_name}",\n'
        f'    schedule="{schedule}",\n'
        "    start_date=days_ago(1),\n"
        "    catchup=False,\n"
        '    tags=["datamind", "scheduled"],\n'
        "    default_args=default_args,\n"
        ")\n"
        "\n"
        f'trigger_task = TriggerDagRunOperator(\n'
        f'    task_id="run_{trigger_dag_id}",\n'
        f'    trigger_dag_id="{trigger_dag_id}",\n'
        f'    conf={{"task_id": "{task_id}"}},\n'
        f'    dag=dag,\n'
        ")\n"
    )

    # Upload via SFTP
    config = await _load_config(db, "airflow")
    if not config:
        raise RuntimeError("Airflow component not configured")
    ssh_host = config.get("ssh_host") or "192.168.1.4"
    ssh_port = int(config.get("ssh_port") or 22)
    ssh_user = config.get("ssh_user") or "root"
    ssh_password = config.get("ssh_password") or ""
    dags_path = config.get("dags_path") or "/home/airflow/dags"
    if not ssh_password:
        raise ValueError("请先在 Airflow 组件配置中填写 SSH 密码")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        ssh_host, port=ssh_port, username=ssh_user,
        password=ssh_password, timeout=15,
    )
    sftp = client.open_sftp()
    try:
        remote = f"{dags_path.rstrip('/')}/{dag_id}.py"
        with sftp.open(remote, "w") as f:
            f.write(content.encode("utf-8"))
    finally:
        sftp.close()
        client.close()

    logger.info(f"[airflow] Created DAG task {dag_id} -> {remote}")
    return {
        "dag_id": dag_id,
        "dag_name": dag_name,
        "task_type": task_type,
        "task_code": task_code,
        "schedule": schedule,
        "trigger_dag_id": trigger_dag_id,
        "file": remote,
    }


async def sync_dag_runs(db: AsyncSession) -> dict:
    """Sync all Airflow DAG runs into airflow_dag_runs for unified monitoring."""
    from datetime import datetime, timezone

    from app.models import AirflowDagRun
    from app.services.component_service import get_airflow_client

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
                row.execution_date = _parse(run.get("execution_date"))
            else:
                db.add(AirflowDagRun(
                    dag_id=dag_id,
                    dag_run_id=run_id,
                    run_type=run.get("run_type"),
                    state=run.get("state"),
                    execution_date=_parse(run.get("execution_date")),
                    start_date=start,
                    end_date=end,
                    duration_seconds=duration,
                ))
            total += 1
    await db.commit()
    logger.info(f"[airflow] synced {total} dag runs from {len(dags)} dags")
    return {"synced": total, "dags": len(dags)}


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
        })
    return items, total
