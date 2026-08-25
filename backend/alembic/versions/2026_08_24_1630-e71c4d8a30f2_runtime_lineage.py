"""Add task run callbacks and runtime-only lineage.

Revision ID: e71c4d8a30f2
Revises: b8f53a9c21d4
"""
from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "e71c4d8a30f2"
down_revision: Union[str, None] = "b8f53a9c21d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for name in ("task_count", "success_task_count", "failed_task_count", "input_asset_count", "output_asset_count"):
        op.add_column("airflow_dag_runs", sa.Column(name, sa.Integer(), nullable=False, server_default="0"))
    op.add_column("airflow_dag_runs", sa.Column("lineage_status", sa.String(20), nullable=False, server_default="pending"))
    op.add_column("airflow_dag_runs", sa.Column("lineage_collected_at", sa.DateTime(timezone=True)))
    op.create_index("ix_airflow_dag_runs_lineage_status", "airflow_dag_runs", ["lineage_status"])

    op.create_table(
        "airflow_task_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("dag_run_record_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("airflow_dag_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("dag_id", sa.String(200), nullable=False),
        sa.Column("dag_run_id", sa.String(250), nullable=False),
        sa.Column("task_id", sa.String(250), nullable=False),
        sa.Column("try_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("operator_type", sa.String(100)),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("executed_sql", sa.Text()),
        sa.Column("sql_hash", sa.String(64)),
        sa.Column("affected_rows", sa.Integer()),
        sa.Column("input_tables", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("output_tables", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("error_message", sa.Text()),
        sa.Column("start_date", sa.DateTime(timezone=True)),
        sa.Column("end_date", sa.DateTime(timezone=True)),
        sa.Column("duration_seconds", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("dag_id", "dag_run_id", "task_id", "try_number", name="uq_airflow_task_runs_identity"),
    )
    for column in ("dag_run_record_id", "dag_id", "dag_run_id", "state", "sql_hash"):
        op.create_index(f"ix_airflow_task_runs_{column}", "airflow_task_runs", [column])

    op.add_column("asset_lineage_edges", sa.Column("first_seen_at", sa.DateTime(timezone=True)))
    op.add_column("asset_lineage_edges", sa.Column("last_seen_at", sa.DateTime(timezone=True)))
    op.add_column("asset_lineage_edges", sa.Column("success_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("asset_lineage_edges", sa.Column("last_dag_run_id", sa.String(250)))
    op.add_column("asset_lineage_edges", sa.Column("last_task_id", sa.String(250)))

    op.create_table(
        "lineage_run_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("task_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("airflow_task_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_asset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("asset_objects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_asset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("asset_objects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("dag_id", sa.String(200), nullable=False),
        sa.Column("dag_run_id", sa.String(250), nullable=False),
        sa.Column("task_id", sa.String(250), nullable=False),
        sa.Column("sql_hash", sa.String(64)),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("task_run_id", "source_asset_id", "target_asset_id", name="uq_lineage_run_event_pair"),
    )
    for column in ("task_run_id", "source_asset_id", "target_asset_id", "dag_id", "dag_run_id"):
        op.create_index(f"ix_lineage_run_events_{column}", "lineage_run_events", [column])

    # The product now exposes successful runtime lineage only.
    op.execute("DELETE FROM asset_lineage_edges")


def downgrade() -> None:
    op.drop_table("lineage_run_events")
    for name in ("last_task_id", "last_dag_run_id", "success_count", "last_seen_at", "first_seen_at"):
        op.drop_column("asset_lineage_edges", name)
    op.drop_table("airflow_task_runs")
    op.drop_index("ix_airflow_dag_runs_lineage_status", table_name="airflow_dag_runs")
    for name in ("lineage_collected_at", "lineage_status", "output_asset_count", "input_asset_count", "failed_task_count", "success_task_count", "task_count"):
        op.drop_column("airflow_dag_runs", name)
