"""Flatten data development into a top-level menu.

Revision ID: b72a41d9c5e8
Revises: f39d8b21a6c4
"""
from typing import Union
import uuid

from alembic import op
import sqlalchemy as sa


revision: str = "b72a41d9c5e8"
down_revision: Union[str, None] = "f39d8b21a6c4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text("""
            UPDATE menus
            SET parent_id=NULL, menu_name='数据开发', menu_type='menu',
                icon='CodeOutlined', sort_order=2, updated_at=now()
            WHERE route_path='/query'
        """)
    )
    connection.execute(
        sa.text("DELETE FROM menus WHERE route_path IN ('/dev/models', '/dev/publish')")
    )
    connection.execute(sa.text("DELETE FROM menus WHERE route_path='/dev'"))


def downgrade() -> None:
    connection = op.get_bind()
    parent_id = connection.execute(
        sa.text("SELECT id FROM menus WHERE route_path='/dev' LIMIT 1")
    ).scalar()
    if not parent_id:
        parent_id = uuid.uuid4()
        connection.execute(
            sa.text("""
                INSERT INTO menus (id, parent_id, menu_name, menu_type, route_path, component,
                    icon, sort_order, visible, status, created_at, updated_at)
                VALUES (:id, NULL, '数据开发', 'directory', '/dev', '', 'CodeOutlined',
                    2, true, 'active', now(), now())
            """),
            {"id": parent_id},
        )
    connection.execute(
        sa.text("""
            UPDATE menus
            SET parent_id=:parent_id, menu_name='ETL 开发', menu_type='menu',
                icon='', sort_order=1, updated_at=now()
            WHERE route_path='/query'
        """),
        {"parent_id": parent_id},
    )
