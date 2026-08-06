"""
Integration tests for the Auth API endpoints.

These tests require a running PostgreSQL and Redis instance.
Run: pytest -m integration tests/test_auth_api.py
"""
import pytest

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
class TestAuthAPI:
    async def test_login_missing_fields(self, test_client):
        """Login with missing fields should return 422."""
        resp = await test_client.post("/api/v1/auth/login", json={})
        assert resp.status_code == 422

    async def test_login_short_username(self, test_client):
        """Username below min_length should be rejected."""
        resp = await test_client.post(
            "/api/v1/auth/login",
            json={"username": "a", "password": "admin123"},
        )
        assert resp.status_code == 422

    async def test_login_short_password(self, test_client):
        """Password below min_length should be rejected."""
        resp = await test_client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "12345"},
        )
        assert resp.status_code == 422

    async def test_me_without_token(self, test_client):
        """Accessing /me without auth header should return 401."""
        resp = await test_client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    async def test_me_with_invalid_token(self, test_client):
        """Accessing /me with invalid token should return 401."""
        resp = await test_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalidtoken"},
        )
        assert resp.status_code == 401

    async def test_refresh_with_invalid_token(self, test_client):
        """Refresh with invalid token should return code 401 in body."""
        resp = await test_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid-token"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 401
