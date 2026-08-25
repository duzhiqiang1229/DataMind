"""Add MCP clients, credentials, audit and modeling change sets.

Revision ID: d4e8b7c219a0
Revises: b72a41d9c5e8
"""
from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d4e8b7c219a0"
down_revision: Union[str, None] = "b72a41d9c5e8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mcp_clients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_name", sa.String(100), nullable=False),
        sa.Column("client_code", sa.String(100), nullable=False, unique=True),
        sa.Column("service_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("scopes", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("last_connected_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_mcp_clients_service_user_id", "mcp_clients", ["service_user_id"])
    op.create_index("ix_mcp_clients_status", "mcp_clients", ["status"])

    op.create_table(
        "mcp_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("mcp_clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_name", sa.String(100), nullable=False),
        sa.Column("token_prefix", sa.String(20), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_mcp_tokens_client_id", "mcp_tokens", ["client_id"])
    op.create_index("ix_mcp_tokens_token_prefix", "mcp_tokens", ["token_prefix"])
    op.create_index("ix_mcp_tokens_status", "mcp_tokens", ["status"])

    op.create_table(
        "mcp_change_sets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("change_set_code", sa.String(100), nullable=False, unique=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("mcp_clients.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("validation_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("validation_result", postgresql.JSONB(), nullable=False),
        sa.Column("committed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_mcp_change_sets_client_id", "mcp_change_sets", ["client_id"])
    op.create_index("ix_mcp_change_sets_created_by", "mcp_change_sets", ["created_by"])
    op.create_index("ix_mcp_change_sets_status", "mcp_change_sets", ["status"])

    op.create_table(
        "mcp_change_set_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("change_set_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("mcp_change_sets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("object_type", sa.String(50), nullable=False),
        sa.Column("action", sa.String(30), nullable=False, server_default="create"),
        sa.Column("object_id", postgresql.UUID(as_uuid=True)),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("validation_result", postgresql.JSONB(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_mcp_change_set_items_change_set_id", "mcp_change_set_items", ["change_set_id"])
    op.create_index("ix_mcp_change_set_items_object_type", "mcp_change_set_items", ["object_type"])

    op.create_table(
        "mcp_tool_calls",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("mcp_clients.id", ondelete="SET NULL")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("change_set_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("mcp_change_sets.id", ondelete="SET NULL")),
        sa.Column("tool_name", sa.String(100), nullable=False),
        sa.Column("arguments_json", postgresql.JSONB(), nullable=False),
        sa.Column("result_summary", sa.Text()),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("elapsed_ms", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    for column in ("client_id", "user_id", "change_set_id", "tool_name", "status"):
        op.create_index(f"ix_mcp_tool_calls_{column}", "mcp_tool_calls", [column])

    op.execute("""
        INSERT INTO menus (id, parent_id, menu_name, menu_type, route_path, component, icon, sort_order, visible, status)
        SELECT gen_random_uuid(), parent.id, 'MCP管理', 'menu', '/system/mcp', 'system/mcp/index', '', 5, true, 'active'
        FROM menus parent
        WHERE parent.route_path = '/system'
          AND NOT EXISTS (SELECT 1 FROM menus WHERE route_path = '/system/mcp')
    """)
    op.execute("""
        INSERT INTO role_menus (role_id, menu_id)
        SELECT r.id, m.id FROM roles r CROSS JOIN menus m
        WHERE m.route_path = '/system/mcp'
          AND NOT EXISTS (SELECT 1 FROM role_menus rm WHERE rm.role_id = r.id AND rm.menu_id = m.id)
    """)


def downgrade() -> None:
    op.execute("DELETE FROM role_menus WHERE menu_id IN (SELECT id FROM menus WHERE route_path = '/system/mcp')")
    op.execute("DELETE FROM menus WHERE route_path = '/system/mcp'")
    op.drop_table("mcp_tool_calls")
    op.drop_table("mcp_change_set_items")
    op.drop_table("mcp_change_sets")
    op.drop_table("mcp_tokens")
    op.drop_table("mcp_clients")
