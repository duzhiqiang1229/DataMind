"""Trigger etl_dim_to_ads and verify OpenMetadata receives lineage edges."""

import asyncio
import os
import time
from collections import Counter
from datetime import datetime, timezone

from app.core.database import async_session
from app.services.component_service import get_airflow_client, get_openmetadata_client


DAG_ID = "etl_dim_to_ads"
PIPELINE_FQN = "datamind_airflow.etl_dim_to_ads"


def counts(lineage: dict) -> tuple[int, int, int, int]:
    return (
        len(lineage.get("upstream", {}).get("nodes", [])),
        len(lineage.get("upstream", {}).get("edges", [])),
        len(lineage.get("downstream", {}).get("nodes", [])),
        len(lineage.get("downstream", {}).get("edges", [])),
    )


async def main() -> None:
    async with async_session() as db:
        airflow = await get_airflow_client(db)
        metadata = await get_openmetadata_client(db)
        print(f"airflow_healthy={await airflow.health_check()}", flush=True)
        print(f"openmetadata_healthy={await metadata.health_check()}", flush=True)
        try:
            before = counts(await metadata.get_lineage(PIPELINE_FQN, "pipeline"))
        except Exception:
            before = (0, 0, 0, 0)
        print(f"lineage_before={before}", flush=True)

        run_id = os.environ.get("OPENLINEAGE_RUN_ID")
        if not run_id:
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            run_id = f"manual__openlineage_validation_{stamp}"
            run = await airflow.trigger_dag_run(DAG_ID, run_id=run_id)
            run_id = run.get("dag_run_id", run_id)
        print(f"dag_run_id={run_id}", flush=True)

        deadline = time.monotonic() + 3600
        last_summary = None
        state = "queued"
        while time.monotonic() < deadline:
            try:
                state = await airflow.get_dag_run_state(DAG_ID, run_id)
                tasks = await airflow.get_task_instances(DAG_ID, run_id)
            except Exception as exc:
                print(f"poll_retry={type(exc).__name__}", flush=True)
                await asyncio.sleep(10)
                continue
            summary = dict(Counter(task.get("state") or "none" for task in tasks))
            current = (state, summary)
            if current != last_summary:
                print(f"state={state} tasks={summary}", flush=True)
                last_summary = current
            if state in {"success", "failed"}:
                break
            await asyncio.sleep(10)

        if state != "success":
            print(f"terminal_state={state}", flush=True)
            for task in await airflow.get_task_instances(DAG_ID, run_id):
                if task.get("state") == "failed":
                    task_id = task.get("task_id")
                    print(f"failed_task={task_id}", flush=True)
                    try:
                        log = await airflow.get_task_log(DAG_ID, run_id, task_id)
                        print(log[-4000:], flush=True)
                    except Exception as exc:
                        print(f"failed_log_error={exc}", flush=True)
            raise RuntimeError(f"DAG validation did not succeed: {state}")

        await asyncio.sleep(15)
        after = counts(await metadata.get_lineage(PIPELINE_FQN, "pipeline"))
        print(f"lineage_after={after}", flush=True)
        print(f"lineage_changed={after != before}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
