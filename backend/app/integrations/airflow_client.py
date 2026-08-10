"""
Airflow REST API client.
Central integration: DataX and Spark execution both go through Airflow DAGs.

Key operations:
- List DAGs / get DAG info
- Trigger DAG run (with config params)
- Poll DAG run / task instance status
- Fetch task logs
"""
from typing import Any, Optional

import httpx
from loguru import logger

from app.integrations.base import ComponentAdapter


class AirflowClient(ComponentAdapter):
    """Async client for Airflow REST API v1."""

    def __init__(self, config: dict):
        super().__init__("airflow", config)

    async def health_check(self) -> bool:
        try:
            resp = await self._request("GET", "/api/v1/health")
            # Airflow health payload:
            # {"metadatabase": {"status": "healthy"}, "scheduler": {"status": "running"}, ...}
            data = resp.json()
            return data.get("metadatabase", {}).get("status") == "healthy"
        except Exception:
            return False

    # --- DAG management ---

    async def list_dags(self, limit: int = 100, offset: int = 0) -> list[dict]:
        """List all DAGs."""
        resp = await self._request(
            "GET", "/api/v1/dags",
            params={"limit": limit, "offset": offset},
        )
        return resp.json().get("dags", [])

    async def get_dag(self, dag_id: str) -> dict:
        """Get details of a specific DAG."""
        resp = await self._request("GET", f"/api/v1/dags/{dag_id}")
        return resp.json()

    async def patch_dag(self, dag_id: str, is_paused: bool) -> dict:
        """Pause/unpause a DAG."""
        resp = await self._request(
            "PATCH", f"/api/v1/dags/{dag_id}",
            json={"is_paused": is_paused},
        )
        return resp.json()

    # --- DAG run execution ---

    async def trigger_dag_run(
        self,
        dag_id: str,
        conf: Optional[dict] = None,
        run_id: Optional[str] = None,
    ) -> dict:
        """
        Trigger a DAG run with parameters.
        This is the core call for both DataX and Spark task execution.

        Args:
            dag_id: Pre-defined DAG template ID (e.g. 'datax_sync', 'spark_job')
            conf: Parameters passed to the DAG (task_id, config references, etc.)
            run_id: Optional custom run ID

        Returns:
            DAG run info including state ('queued', 'running', 'success', 'failed')
        """
        payload: dict[str, Any] = {"conf": conf or {}}
        if run_id:
            payload["dag_run_id"] = run_id
        resp = await self._request(
            "POST", f"/api/v1/dags/{dag_id}/dagRuns",
            json=payload,
        )
        return resp.json()

    async def get_dag_run(self, dag_id: str, run_id: str) -> dict:
        """Get status of a specific DAG run."""
        resp = await self._request(
            "GET", f"/api/v1/dags/{dag_id}/dagRuns/{run_id}"
        )
        return resp.json()

    async def get_dag_run_state(self, dag_id: str, run_id: str) -> str:
        """Quick state check: returns 'queued'|'running'|'success'|'failed'."""
        info = await self.get_dag_run(dag_id, run_id)
        return info.get("state", "unknown")

    async def list_dag_runs(
        self, dag_id: str, limit: int = 50, offset: int = 0,
        order_by: str = "-start_date",
    ) -> list[dict]:
        """List DAG runs for a DAG, newest first by default."""
        resp = await self._request(
            "GET", f"/api/v1/dags/{dag_id}/dagRuns",
            params={"limit": limit, "offset": offset, "order_by": order_by},
        )
        return resp.json().get("dag_runs", [])

    # --- Task instance & logs ---

    async def get_task_instances(self, dag_id: str, run_id: str) -> list[dict]:
        """Get task instances within a DAG run."""
        resp = await self._request(
            "GET", f"/api/v1/dags/{dag_id}/dagRuns/{run_id}/taskInstances"
        )
        return resp.json().get("task_instances", [])

    async def get_task_log(
        self, dag_id: str, run_id: str, task_id: str, try_number: int = 1
    ) -> str:
        """Fetch execution log for a specific task."""
        resp = await self._request(
            "GET",
            f"/api/v1/dags/{dag_id}/dagRuns/{run_id}/taskInstances/{task_id}/logs/{try_number}",
            headers={"Accept": "text/plain"},
        )
        return resp.text

    async def get_xcom(
        self, dag_id: str, run_id: str, task_id: str, key: str
    ) -> Any:
        """Fetch an XCom value pushed by a task instance."""
        resp = await self._request(
            "GET",
            f"/api/v1/dags/{dag_id}/dagRuns/{run_id}/taskInstances/{task_id}/xcomEntries/{key}",
        )
        return resp.json().get("value")

    # --- Cleanup ---

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
