"""
OpenMetadata REST API client.
Provides data catalog, lineage, and data quality.

Key operations:
- List data assets (tables, databases, dashboards, pipelines)
- Get table details (columns, schema, tags)
- Get lineage / data pipeline relationships
- Health check
"""
from typing import Any, Optional

from loguru import logger

from app.integrations.base import ComponentAdapter


class OpenMetadataClient(ComponentAdapter):
    """Async client for OpenMetadata REST API."""

    def __init__(self, config: dict):
        super().__init__("openmetadata", config)
        # JWT token for auth (if configured)
        self._jwt_token: str = self._credentials.get("jwt_token", "")

    async def health_check(self) -> bool:
        try:
            resp = await self._request("GET", "/api/v1/system/config/health")
            data = resp.json()
            return data.get("status") in ("healthy", "HEALTHY")
        except Exception:
            try:
                resp = await self._request("GET", "/api/v1/system/version")
                return resp.status_code == 200
            except Exception:
                return False

    def _get_headers(self) -> dict:
        """Add JWT token to headers if configured."""
        headers = super()._get_headers()
        if self._jwt_token:
            headers["Authorization"] = f"Bearer {self._jwt_token}"
        return headers

    # --- Data Catalog ---

    async def list_databases(self, limit: int = 100) -> list[dict]:
        """List all registered databases."""
        resp = await self._request(
            "GET", "/api/v1/databases",
            params={"limit": limit, "fields": "tables"},
        )
        return resp.json().get("data", [])

    async def list_tables(self, database_fqn: str | None = None, limit: int = 100) -> list[dict]:
        """List tables, optionally filtered by database."""
        params: dict[str, Any] = {"limit": limit, "fields": "columns,tags"}
        if database_fqn:
            params["database"] = database_fqn
        resp = await self._request("GET", "/api/v1/tables", params=params)
        return resp.json().get("data", [])

    async def get_table(self, table_fqn: str) -> dict:
        """Get table details including columns, schema, tags."""
        resp = await self._request(
            "GET", f"/api/v1/tables/{table_fqn}",
            params={"fields": "columns,tags,profile"},
        )
        return resp.json()

    # --- Lineage ---

    async def get_lineage(self, entity_fqn: str, entity_type: str = "table") -> dict:
        """
        Get upstream/downstream lineage for an entity.

        Args:
            entity_fqn: Fully qualified name (e.g. "doris.ods.ods_user")
            entity_type: "table" | "database" | "pipeline"
        """
        resp = await self._request(
            "GET", "/api/v1/lineage",
            params={"fqn": entity_fqn, "entityType": entity_type, "upstreamDepth": 5, "downstreamDepth": 5},
        )
        return resp.json()

    # --- Search ---

    async def search(self, query: str, limit: int = 20) -> list[dict]:
        """Search across all data assets."""
        resp = await self._request(
            "GET", "/api/v1/search/query",
            params={"q": query, "index": "table_search_index", "from": 0, "size": limit},
        )
        hits = resp.json().get("hits", {}).get("hits", [])
        return [h.get("_source", {}) for h in hits]

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
