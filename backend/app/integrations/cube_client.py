"""
Cube REST API client.
Provides unified semantic layer for metrics.

Key operations:
- Load metric data (query results)
- Get meta (available cubes/models/measurements)
- Health check
"""
import time

import jwt

from app.core.config import settings
from app.integrations.base import ComponentAdapter


class CubeClient(ComponentAdapter):
    """Async client for Cube REST API."""

    def __init__(self, config: dict):
        super().__init__("cube", config)
        self._api_secret = config.get("api_secret") or settings.CUBE_API_SECRET

    async def _request(self, method: str, path: str, **kwargs):
        """Attach a fresh short-lived Cube JWT to every request."""
        if self._api_secret:
            now = int(time.time())
            token = jwt.encode(
                {"sub": "datamind-backend", "iat": now, "exp": now + 300},
                self._api_secret,
                algorithm="HS256",
            )
            headers = dict(kwargs.pop("headers", {}))
            headers["Authorization"] = f"Bearer {token}"
            kwargs["headers"] = headers
        return await super()._request(method, path, **kwargs)

    async def health_check(self) -> bool:
        try:
            resp = await self._request("GET", "/cubejs-api/v1/meta")
            return resp.status_code == 200
        except Exception:
            return False

    async def get_meta(self) -> dict:
        """Get available cubes, dimensions, measures, and joins."""
        resp = await self._request("GET", "/cubejs-api/v1/meta")
        return resp.json()

    async def load(self, query: dict) -> dict:
        """
        Execute a Cube query and return results.

        Args:
            query: Cube query object with measures, dimensions, filters, etc.
                Example:
                {
                    "measures": ["Orders.count"],
                    "dimensions": ["Orders.status"],
                    "timeDimensions": [{
                        "dimension": "Orders.createdAt",
                        "dateRange": ["2026-01-01", "2026-08-06"],
                        "granularity": "day"
                    }],
                    "filters": [{"member": "Orders.status", "operator": "equals", "values": ["completed"]}],
                    "order": {"Orders.count": "desc"},
                    "limit": 10000
                }

        Returns:
            Query annotation + data (columns + rows)
        """
        resp = await self._request(
            "POST", "/cubejs-api/v1/load",
            json={"query": query},
        )
        return resp.json()

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
