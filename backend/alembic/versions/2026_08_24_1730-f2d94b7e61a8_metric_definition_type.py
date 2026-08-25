"""Add metric type to metric definitions.

Revision ID: f2d94b7e61a8
Revises: e71c4d8a30f2
"""
from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "f2d94b7e61a8"
down_revision: Union[str, None] = "e71c4d8a30f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "metric_definitions",
        sa.Column("metric_type", sa.String(20), nullable=False, server_default="atomic"),
    )
    op.create_index("ix_metric_definitions_metric_type", "metric_definitions", ["metric_type"])


def downgrade() -> None:
    op.drop_index("ix_metric_definitions_metric_type", table_name="metric_definitions")
    op.drop_column("metric_definitions", "metric_type")
