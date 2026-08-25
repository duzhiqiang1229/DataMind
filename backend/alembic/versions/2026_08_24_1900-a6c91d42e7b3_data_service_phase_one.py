"""Data service phase one.

Revision ID: a6c91d42e7b3
Revises: f2d94b7e61a8
"""
from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "a6c91d42e7b3"
down_revision: Union[str, None] = "f2d94b7e61a8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("data_service_apis", sa.Column("service_code", sa.String(100), nullable=True))
    op.add_column("data_service_apis", sa.Column("service_type", sa.String(30), nullable=False, server_default="custom_sql"))
    op.add_column("data_service_apis", sa.Column("datasource_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("data_service_apis", sa.Column("table_name", sa.String(200), nullable=True))
    op.add_column("data_service_apis", sa.Column("selected_fields", postgresql.JSONB(), nullable=False, server_default="[]"))
    op.add_column("data_service_apis", sa.Column("filter_fields", postgresql.JSONB(), nullable=False, server_default="[]"))
    op.add_column("data_service_apis", sa.Column("max_rows", sa.Integer(), nullable=False, server_default="1000"))
    op.execute("UPDATE data_service_apis SET service_code = 'legacy_' || replace(id::text, '-', '_') WHERE service_code IS NULL")
    op.execute("UPDATE data_service_apis SET status = CASE WHEN status = 'active' THEN 'published' ELSE 'offline' END")
    op.alter_column("data_service_apis", "service_code", nullable=False)
    op.create_index("ix_data_service_apis_service_code", "data_service_apis", ["service_code"], unique=True)
    op.create_index("ix_data_service_apis_service_type", "data_service_apis", ["service_type"])
    op.create_index("ix_data_service_apis_datasource_id", "data_service_apis", ["datasource_id"])
    op.create_foreign_key("fk_data_service_datasource", "data_service_apis", "data_sources", ["datasource_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    op.drop_constraint("fk_data_service_datasource", "data_service_apis", type_="foreignkey")
    op.drop_index("ix_data_service_apis_datasource_id", table_name="data_service_apis")
    op.drop_index("ix_data_service_apis_service_type", table_name="data_service_apis")
    op.drop_index("ix_data_service_apis_service_code", table_name="data_service_apis")
    for column in ["max_rows", "filter_fields", "selected_fields", "table_name", "datasource_id", "service_type", "service_code"]:
        op.drop_column("data_service_apis", column)
