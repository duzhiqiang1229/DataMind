"""Restricted executor API boundary tests."""
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.executor_main import app


@pytest.mark.asyncio
async def test_executor_health_is_available():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://executor"
    ) as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "datamind-executor"


@pytest.mark.asyncio
async def test_executor_rejects_invalid_token_before_docker_access(monkeypatch):
    monkeypatch.setattr(settings, "EXECUTOR_TOKEN", "valid-executor-token-123456789")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://executor"
    ) as client:
        response = await client.post(
            "/v1/cube/restart",
            headers={"X-Executor-Token": "invalid-token"},
        )
    assert response.status_code == 401
