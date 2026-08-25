"""Data service metrics, app keys and cache.

Revision ID: d18bf63a4c02
Revises: a6c91d42e7b3
"""
from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d18bf63a4c02"
down_revision: Union[str, None] = "a6c91d42e7b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("data_service_apis", sa.Column("metric_ids", postgresql.JSONB(), nullable=False, server_default="[]"))
    op.add_column("data_service_apis", sa.Column("metric_dimensions", postgresql.JSONB(), nullable=False, server_default="[]"))
    op.add_column("data_service_apis", sa.Column("time_dimension", sa.String(200), nullable=True))
    op.add_column("data_service_apis", sa.Column("default_granularity", sa.String(20), nullable=True))
    op.create_table(
        "data_service_app_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("api_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("data_service_apis.id", ondelete="CASCADE"), nullable=False),
        sa.Column("key_name", sa.String(100), nullable=False),
        sa.Column("key_prefix", sa.String(20), nullable=False),
        sa.Column("key_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_data_service_app_keys_api_id", "data_service_app_keys", ["api_id"])
    op.create_index("ix_data_service_app_keys_key_prefix", "data_service_app_keys", ["key_prefix"])


def downgrade() -> None:
    op.drop_index("ix_data_service_app_keys_key_prefix", table_name="data_service_app_keys")
    op.drop_index("ix_data_service_app_keys_api_id", table_name="data_service_app_keys")
    op.drop_table("data_service_app_keys")
    for column in ["default_granularity", "time_dimension", "metric_dimensions", "metric_ids"]:
        op.drop_column("data_service_apis", column)
