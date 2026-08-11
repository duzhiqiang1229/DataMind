"""Authorization and production-safety unit tests."""
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.core import dependencies
from app.core.config import settings, validate_production_settings


def _role(code: str, permissions: tuple[str, ...] = ()):  # tiny model stand-in
    return SimpleNamespace(
        role_code=code,
        status="active",
        permissions=[SimpleNamespace(permission_code=item) for item in permissions],
    )


@pytest.mark.asyncio
async def test_require_role_rejects_non_admin():
    dependency = dependencies.require_role("admin")
    user = SimpleNamespace(roles=[_role("viewer")])
    with pytest.raises(HTTPException) as exc:
        await dependency(user)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_admin_bypasses_permission_check():
    dependency = dependencies.require_permission("system:manage")
    user = SimpleNamespace(roles=[_role("admin")])
    assert await dependency(user) is user


@pytest.mark.asyncio
async def test_permission_check_accepts_granted_permission():
    dependency = dependencies.require_permission("datasource:view")
    user = SimpleNamespace(roles=[_role("viewer", ("datasource:view",))])
    assert await dependency(user) is user


@pytest.mark.asyncio
async def test_revoked_token_is_rejected_before_database_lookup(monkeypatch):
    monkeypatch.setattr(
        dependencies,
        "decode_token",
        lambda _token: {"type": "access", "sub": "00000000-0000-0000-0000-000000000001", "jti": "revoked"},
    )

    async def token_exists(_key: str):
        return 1

    monkeypatch.setattr(dependencies.redis_client, "exists", token_exists)
    db = SimpleNamespace()
    with pytest.raises(HTTPException) as exc:
        await dependencies.get_current_user(db=db, authorization="Bearer token")
    assert exc.value.status_code == 401


def test_production_rejects_default_jwt_secret(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "JWT_SECRET_KEY", "change-in-production")
    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        validate_production_settings()


def test_production_requires_cube_api_secret(monkeypatch):
    from cryptography.fernet import Fernet

    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "JWT_SECRET_KEY", "valid-jwt-secret-for-production-tests")
    monkeypatch.setattr(settings, "ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setattr(settings, "BOOTSTRAP_ADMIN", False)
    monkeypatch.setattr(settings, "EXECUTOR_URL", "")
    monkeypatch.setattr(settings, "CUBE_API_SECRET", "")

    with pytest.raises(RuntimeError, match="CUBE_API_SECRET"):
        validate_production_settings()
