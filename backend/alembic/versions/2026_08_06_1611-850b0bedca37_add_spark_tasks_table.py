"""Compatibility marker for the former Spark migration.

Revision ID: 850b0bedca37
Revises: a13aae84b769
"""
from typing import Sequence, Union


revision: str = "850b0bedca37"
down_revision: Union[str, None] = "a13aae84b769"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Current schema reconciliation is handled by the next revision."""


def downgrade() -> None:
    """Compatibility markers do not own database objects."""
