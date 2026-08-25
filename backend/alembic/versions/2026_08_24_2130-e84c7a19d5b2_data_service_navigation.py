"""Add data service navigation menus.

Revision ID: e84c7a19d5b2
Revises: d18bf63a4c02
"""
from typing import Union
import uuid

from alembic import op
import sqlalchemy as sa


revision: str = "e84c7a19d5b2"
down_revision: Union[str, None] = "d18bf63a4c02"
branch_labels = None
depends_on = None


def _upsert_menu(connection, *, path: str, name: str, menu_type: str, parent_id=None,
                 component: str = "", icon: str = "", sort_order: int = 0):
    existing = connection.execute(
        sa.text("SELECT id FROM menus WHERE route_path = :path LIMIT 1"), {"path": path}
    ).scalar()
    if existing:
        connection.execute(
            sa.text("""
                UPDATE menus SET menu_name=:name, menu_type=:menu_type, parent_id=:parent_id,
                    component=:component, icon=:icon, sort_order=:sort_order,
                    visible=true, status='active', updated_at=now()
                WHERE id=:id
            """),
            {"id": existing, "name": name, "menu_type": menu_type, "parent_id": parent_id,
             "component": component, "icon": icon, "sort_order": sort_order},
        )
        return existing

    menu_id = uuid.uuid4()
    connection.execute(
        sa.text("""
            INSERT INTO menus (id, parent_id, menu_name, menu_type, route_path, component,
                icon, sort_order, visible, status, created_at, updated_at)
            VALUES (:id, :parent_id, :name, :menu_type, :path, :component,
                :icon, :sort_order, true, 'active', now(), now())
        """),
        {"id": menu_id, "parent_id": parent_id, "name": name, "menu_type": menu_type,
         "path": path, "component": component, "icon": icon, "sort_order": sort_order},
    )
    return menu_id


def upgrade() -> None:
    connection = op.get_bind()
    parent_id = _upsert_menu(
        connection, path="/data-service", name="数据服务", menu_type="directory",
        icon="ShareAltOutlined", sort_order=7,
    )
    menu_ids = [parent_id]
    menu_ids.append(_upsert_menu(
        connection, path="/data-service/catalog", name="服务目录", menu_type="menu",
        parent_id=parent_id, component="data-service/index", sort_order=0,
    ))
    menu_ids.append(_upsert_menu(
        connection, path="/data-service/develop", name="服务开发", menu_type="menu",
        parent_id=parent_id, component="data-service/develop/index", sort_order=1,
    ))
    menu_ids.append(_upsert_menu(
        connection, path="/data-service/stats", name="调用监控", menu_type="menu",
        parent_id=parent_id, component="data-service/stats/index", sort_order=2,
    ))
    connection.execute(sa.text("UPDATE menus SET sort_order=8 WHERE route_path='/system'"))

    admin_role_ids = connection.execute(sa.text("SELECT id FROM roles WHERE role_code='admin'")).scalars().all()
    for role_id in admin_role_ids:
        for menu_id in menu_ids:
            connection.execute(
                sa.text("""
                    INSERT INTO role_menus (role_id, menu_id, created_at)
                    VALUES (:role_id, :menu_id, now()) ON CONFLICT DO NOTHING
                """),
                {"role_id": role_id, "menu_id": menu_id},
            )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(sa.text("UPDATE menus SET sort_order=7 WHERE route_path='/system'"))
    connection.execute(sa.text("""
        DELETE FROM menus WHERE route_path IN (
            '/data-service/catalog', '/data-service/develop', '/data-service/stats', '/data-service'
        )
    """))
