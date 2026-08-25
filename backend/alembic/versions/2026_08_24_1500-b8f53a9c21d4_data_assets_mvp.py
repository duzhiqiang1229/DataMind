"""Add self-hosted data catalog, lineage and quality tables.

Revision ID: b8f53a9c21d4
Revises: 9d72f1b6a4ce
"""
from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "b8f53a9c21d4"
down_revision: Union[str, None] = "9d72f1b6a4ce"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "asset_objects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("datasource_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("data_sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("asset_type", sa.String(30), nullable=False, server_default="table"),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("fqn", sa.String(600), nullable=False),
        sa.Column("database_name", sa.String(150)),
        sa.Column("schema_name", sa.String(150)),
        sa.Column("description", sa.Text()),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("properties", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("fqn", name="uq_asset_objects_fqn"),
    )
    for column in ("datasource_id", "asset_type", "name", "fqn", "database_name", "schema_name", "status"):
        op.create_index(f"ix_asset_objects_{column}", "asset_objects", [column])

    op.create_table(
        "asset_columns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("asset_objects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("data_type", sa.String(150), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("nullable", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("primary_key", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("default_value", sa.Text()),
        sa.Column("ordinal_position", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("asset_id", "name", name="uq_asset_columns_asset_name"),
    )
    op.create_index("ix_asset_columns_asset_id", "asset_columns", ["asset_id"])

    op.create_table(
        "asset_lineage_edges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_asset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("asset_objects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_asset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("asset_objects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lineage_type", sa.String(20), nullable=False, server_default="table"),
        sa.Column("source_type", sa.String(30), nullable=False, server_default="model"),
        sa.Column("expression", sa.Text()),
        sa.Column("confidence", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("source_asset_id", "target_asset_id", "source_type", name="uq_asset_lineage_edge"),
    )
    op.create_index("ix_asset_lineage_edges_source_asset_id", "asset_lineage_edges", ["source_asset_id"])
    op.create_index("ix_asset_lineage_edges_target_asset_id", "asset_lineage_edges", ["target_asset_id"])

    op.create_table(
        "quality_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("asset_objects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rule_name", sa.String(200), nullable=False),
        sa.Column("rule_type", sa.String(30), nullable=False),
        sa.Column("column_name", sa.String(200)),
        sa.Column("config", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_quality_rules_asset_id", "quality_rules", ["asset_id"])
    op.create_index("ix_quality_rules_rule_type", "quality_rules", ["rule_type"])

    op.create_table(
        "quality_rule_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("quality_rules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("total_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pass_rate", sa.Numeric(7, 4), nullable=False, server_default="0"),
        sa.Column("message", sa.Text()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_quality_rule_runs_rule_id", "quality_rule_runs", ["rule_id"])
    op.create_index("ix_quality_rule_runs_status", "quality_rule_runs", ["status"])

    op.execute("DELETE FROM role_menus WHERE menu_id IN (SELECT id FROM menus WHERE route_path = '/assets/steward')")
    op.execute("DELETE FROM menus WHERE route_path = '/assets/steward'")
    op.execute("""
        INSERT INTO menus (id, parent_id, menu_name, menu_type, route_path, component, icon, sort_order, visible, status)
        SELECT gen_random_uuid(), parent.id, '数据质量', 'menu', '/assets/quality', 'assets/quality/index', '', 2, true, 'active'
        FROM menus parent
        WHERE parent.route_path = '/assets'
          AND NOT EXISTS (SELECT 1 FROM menus WHERE route_path = '/assets/quality')
    """)
    op.execute("""
        INSERT INTO role_menus (role_id, menu_id)
        SELECT r.id, m.id FROM roles r CROSS JOIN menus m
        WHERE m.route_path = '/assets/quality'
          AND NOT EXISTS (SELECT 1 FROM role_menus rm WHERE rm.role_id = r.id AND rm.menu_id = m.id)
    """)


def downgrade() -> None:
    op.execute("DELETE FROM role_menus WHERE menu_id IN (SELECT id FROM menus WHERE route_path = '/assets/quality')")
    op.execute("DELETE FROM menus WHERE route_path = '/assets/quality'")
    op.drop_table("quality_rule_runs")
    op.drop_table("quality_rules")
    op.drop_table("asset_lineage_edges")
    op.drop_table("asset_columns")
    op.drop_table("asset_objects")
