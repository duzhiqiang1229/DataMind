"""Airflow 3 public REST API client using JWT authentication."""
import asyncio
from typing import Any, Optional

import httpx
from loguru import logger

from app.integrations.base import ComponentAdapter


class AirflowClient(ComponentAdapter):
    """Async client for the Airflow 3 ``/api/v2`` public API."""

    def __init__(self, config: dict):
        super().__init__("airflow", config)
        credentials = config.get("credentials") or {}
        self._username = credentials.get("username", "")
        self._password = credentials.get("password", "")
        self._access_token: str | None = None
        self._auth_lock = asyncio.Lock()

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={"Content-Type": "application/json"},
                timeout=httpx.Timeout(30.0, connect=10.0),
            )
        return self._client

    async def _authenticate(self, force: bool = False) -> str:
        if self._access_token and not force:
            return self._access_token
        if not self._username or not self._password:
            raise RuntimeError("Airflow 3 JWT authentication requires username and password")
        async with self._auth_lock:
            if self._access_token and not force:
                return self._access_token
            response = await self._get_client().post(
                "/auth/token", json={"username": self._username, "password": self._password}
            )
            response.raise_for_status()
            token = response.json().get("access_token")
            if not token:
                raise RuntimeError("Airflow authentication response contains no access_token")
            self._access_token = token
            return token

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        """Call Airflow, refreshing its short-lived JWT once on HTTP 401."""
        headers = dict(kwargs.pop("headers", {}) or {})
        is_public_health = path == "/api/v2/monitor/health"
        if not is_public_health:
            headers["Authorization"] = f"Bearer {await self._authenticate()}"
        try:
            response = await self._get_client().request(method, path, headers=headers, **kwargs)
            if response.status_code == 401 and not is_public_health:
                headers["Authorization"] = f"Bearer {await self._authenticate(force=True)}"
                response = await self._get_client().request(method, path, headers=headers, **kwargs)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as exc:
            logger.error(
                f"[airflow] HTTP {exc.response.status_code} on {method} {path}: "
                f"{exc.response.text[:500]}"
            )
            raise
        except httpx.RequestError as exc:
            logger.error(f"[airflow] Request error on {method} {path}: {exc}")
            raise

    async def health_check(self) -> bool:
        try:
            response = await self._request("GET", "/api/v2/monitor/health")
            return response.json().get("metadatabase", {}).get("status") == "healthy"
        except Exception:
            return False

    async def list_dags(self, limit: int = 100, offset: int = 0) -> list[dict]:
        response = await self._request("GET", "/api/v2/dags", params={"limit": limit, "offset": offset})
        return response.json().get("dags", [])

    async def get_dag(self, dag_id: str) -> dict:
        return (await self._request("GET", f"/api/v2/dags/{dag_id}")).json()

    async def patch_dag(self, dag_id: str, is_paused: bool) -> dict:
        return (await self._request("PATCH", f"/api/v2/dags/{dag_id}", json={"is_paused": is_paused})).json()

    async def trigger_dag_run(self, dag_id: str, conf: Optional[dict] = None, run_id: Optional[str] = None) -> dict:
        payload: dict[str, Any] = {"logical_date": None, "conf": conf or {}}
        if run_id:
            payload["dag_run_id"] = run_id
        return (await self._request("POST", f"/api/v2/dags/{dag_id}/dagRuns", json=payload)).json()

    async def get_dag_run(self, dag_id: str, run_id: str) -> dict:
        return (await self._request("GET", f"/api/v2/dags/{dag_id}/dagRuns/{run_id}")).json()

    async def get_dag_run_state(self, dag_id: str, run_id: str) -> str:
        return (await self.get_dag_run(dag_id, run_id)).get("state", "unknown")

    async def list_dag_runs(self, dag_id: str, limit: int = 50, offset: int = 0, order_by: str = "-start_date") -> list[dict]:
        response = await self._request(
            "GET", f"/api/v2/dags/{dag_id}/dagRuns",
            params={"limit": limit, "offset": offset, "order_by": order_by},
        )
        return response.json().get("dag_runs", [])

    async def get_task_instances(self, dag_id: str, run_id: str) -> list[dict]:
        response = await self._request("GET", f"/api/v2/dags/{dag_id}/dagRuns/{run_id}/taskInstances")
        return response.json().get("task_instances", [])

    async def get_rendered_task_fields(self, dag_id: str, run_id: str, task_id: str) -> dict:
        response = await self._request(
            "GET", f"/api/v2/dags/{dag_id}/dagRuns/{run_id}/taskInstances/{task_id}/renderedFields"
        )
        payload = response.json()
        return payload.get("rendered_fields", payload) if isinstance(payload, dict) else {}

    async def get_task_log(self, dag_id: str, run_id: str, task_id: str, try_number: int = 1) -> str:
        response = await self._request(
            "GET", f"/api/v2/dags/{dag_id}/dagRuns/{run_id}/taskInstances/{task_id}/logs/{try_number}",
            headers={"Accept": "text/plain"},
        )
        return response.text

    async def get_xcom(self, dag_id: str, run_id: str, task_id: str, key: str) -> Any:
        response = await self._request(
            "GET", f"/api/v2/dags/{dag_id}/dagRuns/{run_id}/taskInstances/{task_id}/xcomEntries/{key}"
        )
        return response.json().get("value")

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
