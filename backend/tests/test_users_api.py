"""
Integration tests for the User API endpoints.

These tests require a running PostgreSQL and Redis instance.
Run: pytest -m integration tests/test_users_api.py
"""
import pytest

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
class TestUsersAPI:
    async def test_list_users_without_auth(self, test_client):
        """Listing users without auth should return 401."""
        resp = await test_client.get("/api/v1/users")
        assert resp.status_code == 401

    async def test_create_user_without_auth(self, test_client):
        """Creating a user without auth should return 401."""
        resp = await test_client.post(
            "/api/v1/users",
            json={
                "username": "newuser",
                "password": "password123",
            },
        )
        assert resp.status_code == 401

    async def test_get_nonexistent_user_without_auth(self, test_client):
        """Accessing a user endpoint without auth should return 401."""
        resp = await test_client.get("/api/v1/users/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 401


@pytest.mark.asyncio
class TestPaginationParams:
    async def test_invalid_page_number(self, test_client):
        """Page number < 1 should return 422."""
        resp = await test_client.get("/api/v1/users?page=0")
        assert resp.status_code == 422

    async def test_invalid_page_size_too_large(self, test_client):
        """Page size > 100 should return 422."""
        resp = await test_client.get("/api/v1/users?page_size=200")
        assert resp.status_code == 422
