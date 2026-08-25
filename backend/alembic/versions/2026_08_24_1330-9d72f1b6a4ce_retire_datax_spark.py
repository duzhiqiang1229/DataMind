"""Retire the former DataX and Spark integration modules.

Revision ID: 9d72f1b6a4ce
Revises: c4a17e52b901
"""
from typing import Union

from alembic import op


revision: str = "9d72f1b6a4ce"
down_revision: Union[str, None] = "c4a17e52b901"
branch_labels: Union[str, tuple[str, ...], None] = None
depends_on: Union[str, tuple[str, ...], None] = None


def upgrade() -> None:
    # Remove records whose source entities are being retired.
    op.execute("""
        DELETE FROM publish_records
        WHERE publish_task_id IN (
            SELECT id FROM publish_tasks
            WHERE publish_type IN ('datax_task', 'spark_task')
        )
    """)
    op.execute("DELETE FROM publish_tasks WHERE publish_type IN ('datax_task', 'spark_task')")
    op.execute("DELETE FROM etl_scripts WHERE language IN ('sparksql', 'pyspark', 'python')")

    # Remove obsolete RBAC and menu entries.
    op.execute("""
        DELETE FROM role_permissions
        WHERE permission_id IN (
            SELECT id FROM permissions WHERE permission_code LIKE 'datax:task:%'
        )
    """)
    op.execute("DELETE FROM permissions WHERE permission_code LIKE 'datax:task:%'")
    op.execute("""
        DELETE FROM role_menus
        WHERE menu_id IN (SELECT id FROM menus WHERE route_path = '/datax')
    """)
    op.execute("DELETE FROM menus WHERE route_path = '/datax'")
    op.execute("DELETE FROM component_configs WHERE component_code IN ('datax', 'spark')")

    # These tables contain only the retired integration runtime state.
    op.execute("DROP TABLE IF EXISTS dag_nodes CASCADE")
    op.execute("DROP TABLE IF EXISTS dag_definitions CASCADE")
    op.execute("DROP TABLE IF EXISTS datax_field_mappings CASCADE")
    op.execute("DROP TABLE IF EXISTS datax_tasks CASCADE")
    op.execute("DROP TABLE IF EXISTS spark_tasks CASCADE")
    op.execute("DROP TABLE IF EXISTS task_instances CASCADE")


def downgrade() -> None:
    # Removed task definitions, credentials and execution history cannot be
    # reconstructed safely.
    pass
