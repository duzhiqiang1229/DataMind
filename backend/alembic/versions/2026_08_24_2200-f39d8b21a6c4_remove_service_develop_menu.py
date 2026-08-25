"""Remove standalone service development menu.

Revision ID: f39d8b21a6c4
Revises: e84c7a19d5b2
"""
from typing import Union
import uuid

from alembic import op
import sqlalchemy as sa


revision: str = "f39d8b21a6c4"
down_revision: Union[str, None] = "e84c7a19d5b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    connection.execute(sa.text("DELETE FROM menus WHERE route_path='/data-service/develop'"))
    connection.execute(sa.text("UPDATE menus SET sort_order=1 WHERE route_path='/data-service/stats'"))


def downgrade() -> None:
    connection = op.get_bind()
    parent_id = connection.execute(
        sa.text("SELECT id FROM menus WHERE route_path='/data-service' LIMIT 1")
    ).scalar()
    if not parent_id:
        return
    menu_id = connection.execute(
        sa.text("SELECT id FROM menus WHERE route_path='/data-service/develop' LIMIT 1")
    ).scalar()
    if not menu_id:
        menu_id = uuid.uuid4()
        connection.execute(
            sa.text("""
                INSERT INTO menus (id, parent_id, menu_name, menu_type, route_path, component,
                    icon, sort_order, visible, status, created_at, updated_at)
                VALUES (:id, :parent_id, '服务开发', 'menu', '/data-service/develop',
                    'data-service/develop/index', '', 1, true, 'active', now(), now())
            """),
            {"id": menu_id, "parent_id": parent_id},
        )
    connection.execute(sa.text("UPDATE menus SET sort_order=2 WHERE route_path='/data-service/stats'"))
    connection.execute(
        sa.text("""
            INSERT INTO role_menus (role_id, menu_id, created_at)
            SELECT id, :menu_id, now() FROM roles WHERE role_code='admin'
            ON CONFLICT DO NOTHING
        """),
        {"menu_id": menu_id},
    )
