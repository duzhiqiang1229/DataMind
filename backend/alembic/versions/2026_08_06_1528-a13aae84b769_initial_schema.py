"""Compatibility marker for the original SQL-initialized schema.

Revision ID: a13aae84b769
Revises:
"""
from typing import Sequence, Union


revision: str = "a13aae84b769"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """The original deployment created these objects from SQL."""


def downgrade() -> None:
    """Compatibility markers do not own database objects."""
