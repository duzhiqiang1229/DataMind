"""FastAPI dependencies: auth, pagination, etc."""
from typing import Optional
import uuid

from fastapi import Depends, Header, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import decode_token
from app.core.redis import redis_client
from app.models import User, Role


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None),
) -> User:
    """Extract and validate JWT from Authorization header, return current User."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
        )

    token = authorization.split(" ", 1)[1]
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = payload.get("sub")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    jti = payload.get("jti")
    if jti and await redis_client.exists(f"blacklist:{jti}"):
        raise HTTPException(status_code=401, detail="Token has been revoked")

    try:
        parsed_user_id = uuid.UUID(user_id)
    except (TypeError, ValueError, AttributeError):
        raise HTTPException(status_code=401, detail="Invalid token subject")

    result = await db.execute(
        select(User)
        .options(selectinload(User.roles).selectinload(Role.permissions))
        .where(User.id == parsed_user_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is disabled")
    return user


async def get_optional_current_user(
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None),
) -> User | None:
    """Return the JWT user when supplied, otherwise allow AppKey authentication."""
    if not authorization:
        return None
    return await get_current_user(db=db, authorization=authorization)


def require_role(*allowed_roles: str):
    """Require at least one active role; administrators always pass."""
    async def dependency(user: User = Depends(get_current_user)) -> User:
        role_codes = {
            role.role_code for role in user.roles if role.status == "active"
        }
        if "admin" not in role_codes and role_codes.isdisjoint(allowed_roles):
            raise HTTPException(status_code=403, detail="Insufficient role")
        return user
    return dependency


def require_permission(*required_permissions: str):
    """Require all named permissions; administrators always pass."""
    async def dependency(user: User = Depends(get_current_user)) -> User:
        active_roles = [role for role in user.roles if role.status == "active"]
        if any(role.role_code == "admin" for role in active_roles):
            return user
        granted = {
            permission.permission_code
            for role in active_roles
            for permission in role.permissions
        }
        if not set(required_permissions).issubset(granted):
            raise HTTPException(status_code=403, detail="Insufficient permission")
        return user
    return dependency


class PaginationParams:
    """Common pagination query params."""
    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number"),
        page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    ):
        self.page = page
        self.page_size = page_size

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size
