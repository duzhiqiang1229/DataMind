"""Add OpenLineage identifiers to Airflow task runs.

Revision ID: c7f4a9d213e6
Revises: d4e8b7c219a0
Create Date: 2026-08-26 16:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c7f4a9d213e6"
down_revision: Union[str, None] = "d4e8b7c219a0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "airflow_task_runs",
        sa.Column(
            "openlineage_inputs",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "airflow_task_runs",
        sa.Column(
            "openlineage_outputs",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column("airflow_task_runs", sa.Column("openlineage_run_id", sa.String(100), nullable=True))
    op.add_column("airflow_task_runs", sa.Column("openlineage_job_namespace", sa.String(500), nullable=True))
    op.add_column("airflow_task_runs", sa.Column("openlineage_job_name", sa.String(500), nullable=True))
    op.create_index(
        "ix_airflow_task_runs_openlineage_run_id",
        "airflow_task_runs",
        ["openlineage_run_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_airflow_task_runs_openlineage_run_id", table_name="airflow_task_runs")
    op.drop_column("airflow_task_runs", "openlineage_job_name")
    op.drop_column("airflow_task_runs", "openlineage_job_namespace")
    op.drop_column("airflow_task_runs", "openlineage_run_id")
    op.drop_column("airflow_task_runs", "openlineage_outputs")
    op.drop_column("airflow_task_runs", "openlineage_inputs")
