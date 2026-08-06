"""Authentication service: login, refresh, logout, current user info."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from loguru import logger

from app.core.security import verify_password, create_access_token, create_refresh_token, decode_token
from app.core.config import settings
from app.core.redis import redis_client
from app.models import User, Role, Menu

ACCESS_TTL = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
REFRESH_TTL = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400


async def login(db: AsyncSession, username: str, password: str) -> dict:
    """Validate credentials and return tokens."""
    result = await db.execute(
        select(User).options(selectinload(User.roles)).where(User.username == username)
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.hashed_password):
        raise ValueError("Invalid username or password")
    if not user.is_active:
        raise ValueError("User is disabled")

    # update last login
    await db.execute(
        update(User).where(User.id == user.id).values(last_login_at=datetime.now(timezone.utc))
    )
    await db.commit()

    access = create_access_token(str(user.id), extra={"username": user.username})
    refresh = create_refresh_token(str(user.id))

    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
        "expires_in": ACCESS_TTL,
    }


async def refresh(db: AsyncSession, refresh_token: str) -> dict:
    """Exchange refresh token for new access token."""
    try:
        payload = decode_token(refresh_token)
    except Exception:
        raise ValueError("Invalid or expired refresh token")

    if payload.get("type") != "refresh":
        raise ValueError("Invalid token type")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise ValueError("User not found or disabled")

    access = create_access_token(str(user.id), extra={"username": user.username})
    new_refresh = create_refresh_token(str(user.id))

    return {
        "access_token": access,
        "refresh_token": new_refresh,
        "token_type": "bearer",
        "expires_in": ACCESS_TTL,
    }


async def get_current_user_info(db: AsyncSession, user: User) -> dict:
    """Return user info with roles, permissions, and menu tree."""
    # permissions from roles -> permissions
    perms: list[str] = []
    for role in user.roles:
        # load permissions for each role
        result = await db.execute(
            select(Role)
            .where(Role.id == role.id)
        )
        loaded_role = result.scalar_one()
        # permissions are loaded via selectin on Role
        perms.extend([p.permission_code for p in loaded_role.permissions])

    # unique
    perms = list(set(perms))
    role_codes = [r.role_code for r in user.roles]

    # build menu tree for user's roles
    menu_tree = await _build_menu_tree_for_user(db, user)

    return {
        "id": str(user.id),
        "username": user.username,
        "full_name": user.full_name,
        "email": user.email,
        "avatar": user.avatar,
        "department": user.department,
        "roles": role_codes,
        "permissions": perms,
        "menus": menu_tree,
    }


async def logout(access_token: str):
    """Add token to Redis blacklist until expiry."""
    try:
        payload = decode_token(access_token)
        jti = payload.get("jti", "")
        exp = payload.get("exp", 0)
        import time
        ttl = max(int(exp - time.time()), 1)
        await redis_client.setex(f"blacklist:{jti}", ttl, "1")
    except Exception:
        pass  # token invalid anyway


async def _build_menu_tree_for_user(db: AsyncSession, user: User) -> list[dict]:
    """Build menu tree from user's roles."""
    if not user.roles:
        return []

    role_ids = [r.id for r in user.roles]

    # get menu IDs assigned to user's roles
    from app.models import RoleMenu
    result = await db.execute(
        select(RoleMenu.menu_id).where(RoleMenu.role_id.in_(role_ids))
    )
    menu_ids = list(set(row[0] for row in result.all()))
    if not menu_ids:
        return []

    # load menus
    result = await db.execute(
        select(Menu)
        .where(Menu.id.in_(menu_ids))
        .where(Menu.status == "active")
        .order_by(Menu.sort_order)
    )
    menus = result.scalars().all()

    # build tree
    menu_map = {m.id: _menu_to_dict(m) for m in menus}
    root: list[dict] = []
    for m in menus:
        node = menu_map[m.id]
        if m.parent_id and m.parent_id in menu_map:
            menu_map[m.parent_id].setdefault("children", []).append(node)
        else:
            root.append(node)
    return root


def _menu_to_dict(m: Menu) -> dict:
    return {
        "id": str(m.id),
        "parent_id": str(m.parent_id) if m.parent_id else None,
        "menu_name": m.menu_name,
        "menu_type": m.menu_type,
        "route_path": m.route_path,
        "component": m.component,
        "icon": m.icon,
        "sort_order": m.sort_order,
        "visible": m.visible,
        "children": [],
    }
