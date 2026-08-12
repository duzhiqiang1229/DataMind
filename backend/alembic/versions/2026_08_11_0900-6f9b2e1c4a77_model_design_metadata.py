"""add model design metadata and external-table safety flag

Revision ID: 6f9b2e1c4a77
Revises: e86ab4667156
Create Date: 2026-08-11 09:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "6f9b2e1c4a77"
down_revision: Union[str, None] = "e86ab4667156"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("data_models", sa.Column("model_grain", sa.String(length=300), nullable=True))
    op.add_column("data_models", sa.Column("update_strategy", sa.String(length=30), nullable=True))
    op.add_column(
        "data_models",
        sa.Column(
            "source_tables",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column("data_models", sa.Column("source_fqn", sa.String(length=500), nullable=True))
    op.add_column(
        "data_models",
        sa.Column("is_external", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.create_index(op.f("ix_data_models_source_fqn"), "data_models", ["source_fqn"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_data_models_source_fqn"), table_name="data_models")
    op.drop_column("data_models", "is_external")
    op.drop_column("data_models", "source_fqn")
    op.drop_column("data_models", "source_tables")
    op.drop_column("data_models", "update_strategy")
    op.drop_column("data_models", "model_grain")
