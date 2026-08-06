"""Menu service: tree CRUD."""
import uuid
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Menu


async def get_menu_tree(db: AsyncSession) -> list[dict]:
    """Get full menu tree."""
    result = await db.execute(
        select(Menu).where(Menu.status == "active").order_by(Menu.sort_order)
    )
    menus = result.scalars().all()

    menu_map = {m.id: _menu_to_dict(m) for m in menus}
    root: list[dict] = []
    for m in menus:
        node = menu_map[m.id]
        if m.parent_id and m.parent_id in menu_map:
            menu_map[m.parent_id].setdefault("children", []).append(node)
        else:
            root.append(node)
    return root


async def create_menu(
    db: AsyncSession,
    parent_id: Optional[str], menu_name: str, menu_type: str,
    route_path: Optional[str] = None, component: Optional[str] = None,
    icon: Optional[str] = None, sort_order: int = 0, visible: bool = True,
) -> dict:
    menu = Menu(
        parent_id=uuid.UUID(parent_id) if parent_id else None,
        menu_name=menu_name,
        menu_type=menu_type,
        route_path=route_path,
        component=component,
        icon=icon,
        sort_order=sort_order,
        visible=visible,
    )
    db.add(menu)
    await db.commit()
    await db.refresh(menu)
    return _menu_to_dict(menu)


async def update_menu(db: AsyncSession, menu_id: uuid.UUID, **kwargs) -> dict | None:
    allowed = {"menu_name", "menu_type", "route_path", "component", "icon", "sort_order", "visible", "status", "parent_id"}
    updates = {}
    for k, v in kwargs.items():
        if k in allowed and v is not None:
            if k == "parent_id" and isinstance(v, str):
                v = uuid.UUID(v) if v else None
            updates[k] = v
    if updates:
        from sqlalchemy import update
        await db.execute(update(Menu).where(Menu.id == menu_id).values(**updates))
        await db.commit()
    result = await db.execute(select(Menu).where(Menu.id == menu_id))
    m = result.scalar_one_or_none()
    if not m:
        return None
    return _menu_to_dict(m)


async def delete_menu(db: AsyncSession, menu_id: uuid.UUID) -> bool:
    result = await db.execute(select(Menu).where(Menu.id == menu_id))
    menu = result.scalar_one_or_none()
    if not menu:
        return False
    await db.delete(menu)
    await db.commit()
    return True


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
        "status": m.status,
        "children": [],
    }
