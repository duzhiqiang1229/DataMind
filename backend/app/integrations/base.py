"""Base adapter: common interface for all external component clients."""
from abc import ABC, abstractmethod
from typing import Any, Optional

import httpx
from loguru import logger


class ComponentAdapter(ABC):
    """
    Abstract base for all external component integrations.
    Each adapter wraps a specific component (Airflow, Doris, Cube, OpenMetadata).

    Connection config (base_url, auth) is loaded from component_configs table
    and passed in at initialization time — no hardcoded URLs.
    """

    def __init__(self, component_name: str, config: dict):
        self.component_name = component_name
        self.base_url: str = config.get("base_url", "").rstrip("/")
        self.auth_type: str = config.get("auth_type", "none")
        self._credentials: dict = config.get("credentials", {})
        self._client: Optional[httpx.AsyncClient] = None

    @abstractmethod
    async def health_check(self) -> bool:
        """Test connectivity to the component. Returns True if reachable."""
        ...

    @abstractmethod
    async def close(self):
        """Clean up connections."""
        ...

    def _get_headers(self) -> dict:
        """Build auth headers based on auth_type."""
        headers = {"Content-Type": "application/json"}
        if self.auth_type == "token":
            token = self._credentials.get("token", "")
            headers["Authorization"] = f"Bearer {token}"
        elif self.auth_type == "basic":
            import base64
            user = self._credentials.get("username", "")
            pwd = self._credentials.get("password", "")
            cred = base64.b64encode(f"{user}:{pwd}".encode()).decode()
            headers["Authorization"] = f"Basic {cred}"
        return headers

    def _get_client(self) -> httpx.AsyncClient:
        """Lazy-init HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=self._get_headers(),
                timeout=httpx.Timeout(30.0, connect=10.0),
            )
        return self._client

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        """Execute HTTP request with error logging."""
        client = self._get_client()
        try:
            resp = await client.request(method, path, **kwargs)
            resp.raise_for_status()
            return resp
        except httpx.HTTPStatusError as e:
            logger.error(
                f"[{self.component_name}] HTTP {e.response.status_code} "
                f"on {method} {path}: {e.response.text[:500]}"
            )
            raise
        except httpx.RequestError as e:
            logger.error(f"[{self.component_name}] Request error on {method} {path}: {e}")
            raise
