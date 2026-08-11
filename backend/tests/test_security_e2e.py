"""End-to-end authentication and authorization checks with PostgreSQL + Redis."""
import uuid

import pytest

from app.core.security import hash_password
from app.models import Role, User, UserRole


pytestmark = pytest.mark.integration


async def _create_principal(db, username: str, role_code: str) -> None:
    user = User(
        username=username,
        hashed_password=hash_password("strong-password-123"),
        status="active",
    )
    role = Role(
        role_code=f"{role_code}-{uuid.uuid4().hex[:8]}",
        role_name=role_code,
        status="active",
    )
    # Authorization deliberately keys the privileged role by its stable code.
    if role_code == "admin":
        role.role_code = "admin"
    db.add_all([user, role])
    await db.flush()
    db.add(UserRole(user_id=user.id, role_id=role.id))
    await db.commit()


async def _login(client, username: str) -> dict:
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "strong-password-123"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 200
    return payload["data"]


@pytest.mark.asyncio
async def test_non_admin_cannot_access_user_administration(test_client, test_db_session):
    await _create_principal(test_db_session, "trial-viewer", "viewer")
    tokens = await _login(test_client, "trial-viewer")
    response = await test_client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_access_user_administration(test_client, test_db_session):
    await _create_principal(test_db_session, "trial-admin", "admin")
    tokens = await _login(test_client, "trial-admin")
    response = await test_client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert response.status_code == 200
    assert response.json()["code"] == 200


@pytest.mark.asyncio
async def test_logout_revokes_access_token(test_client, test_db_session):
    await _create_principal(test_db_session, "logout-admin", "admin")
    tokens = await _login(test_client, "logout-admin")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    assert (await test_client.get("/api/v1/auth/me", headers=headers)).status_code == 200
    assert (await test_client.post("/api/v1/auth/logout", headers=headers)).status_code == 200
    assert (await test_client.get("/api/v1/auth/me", headers=headers)).status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_is_single_use(test_client, test_db_session):
    await _create_principal(test_db_session, "refresh-admin", "admin")
    tokens = await _login(test_client, "refresh-admin")
    body = {"refresh_token": tokens["refresh_token"]}
    first = await test_client.post("/api/v1/auth/refresh", json=body)
    second = await test_client.post("/api/v1/auth/refresh", json=body)
    assert first.json()["code"] == 200
    assert second.json()["code"] == 401
