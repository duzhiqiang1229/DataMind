"""Remove the retired external metadata component configuration.

Revision ID: c4a17e52b901
Revises: 6f9b2e1c4a77
"""
from typing import Union

from alembic import op


revision: str = "c4a17e52b901"
down_revision: Union[str, None] = "6f9b2e1c4a77"
branch_labels: Union[str, tuple[str, ...], None] = None
depends_on: Union[str, tuple[str, ...], None] = None


def upgrade() -> None:
    op.execute("DELETE FROM component_configs WHERE component_code = 'openmetadata'")


def downgrade() -> None:
    # Retired credentials cannot be reconstructed safely.
    pass
