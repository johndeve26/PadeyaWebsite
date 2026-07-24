"""Admin impersonation session + request audit tables.

Revision ID: 20260720_0089
Revises: 20260720_0088
Create Date: 2026-07-20
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260720_0089"
down_revision = "20260720_0088"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "admin_impersonation_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_admin_id", sa.Uuid(), nullable=False),
        sa.Column("target_user_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("support_ticket_id", sa.String(length=128), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["actor_admin_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["ended_by_admin_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["target_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_admin_impersonation_sessions_actor_admin_id",
        "admin_impersonation_sessions",
        ["actor_admin_id"],
    )
    op.create_index(
        "ix_admin_impersonation_sessions_target_user_id",
        "admin_impersonation_sessions",
        ["target_user_id"],
    )
    op.create_index(
        "ix_admin_impersonation_sessions_started_at",
        "admin_impersonation_sessions",
        ["started_at"],
    )
    op.create_index(
        "ix_admin_impersonation_sessions_expires_at",
        "admin_impersonation_sessions",
        ["expires_at"],
    )
    op.create_index(
        "ix_admin_impersonation_sessions_ended_by_admin_id",
        "admin_impersonation_sessions",
        ["ended_by_admin_id"],
    )
    op.create_index(
        "ix_admin_impersonation_sessions_status",
        "admin_impersonation_sessions",
        ["status"],
    )
    op.create_index(
        "ix_admin_impersonation_sessions_created_at",
        "admin_impersonation_sessions",
        ["created_at"],
    )

    op.create_table(
        "admin_impersonation_audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("impersonation_id", sa.Uuid(), nullable=False),
        sa.Column("actor_admin_id", sa.Uuid(), nullable=False),
        sa.Column("target_user_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("method", sa.String(length=16), nullable=True),
        sa.Column("path", sa.String(length=512), nullable=True),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["actor_admin_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["impersonation_id"],
            ["admin_impersonation_sessions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["target_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_admin_impersonation_audit_logs_impersonation_id",
        "admin_impersonation_audit_logs",
        ["impersonation_id"],
    )
    op.create_index(
        "ix_admin_impersonation_audit_logs_actor_admin_id",
        "admin_impersonation_audit_logs",
        ["actor_admin_id"],
    )
    op.create_index(
        "ix_admin_impersonation_audit_logs_target_user_id",
        "admin_impersonation_audit_logs",
        ["target_user_id"],
    )
    op.create_index(
        "ix_admin_impersonation_audit_logs_action",
        "admin_impersonation_audit_logs",
        ["action"],
    )
    op.create_index(
        "ix_admin_impersonation_audit_logs_created_at",
        "admin_impersonation_audit_logs",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_table("admin_impersonation_audit_logs")
    op.drop_table("admin_impersonation_sessions")
