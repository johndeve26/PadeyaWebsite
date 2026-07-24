"""Desk scan audit logs for ticket and merch scanners.

Revision ID: 20260719_0072
Revises: 20260719_0071
Create Date: 2026-07-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260719_0072"
down_revision = "20260719_0071"
branch_labels = None
depends_on = None

JSON_VARIANT = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    op.create_table(
        "desk_scan_audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("host_id", sa.Uuid(), nullable=True),
        sa.Column("event_id", sa.Uuid(), nullable=True),
        sa.Column("ticket_id", sa.Uuid(), nullable=True),
        sa.Column("merch_order_item_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("result", sa.String(length=32), nullable=False),
        sa.Column("denial_reason", sa.Text(), nullable=True),
        sa.Column("metadata_json", JSON_VARIANT, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_desk_scan_audit_logs_actor_user_id", "desk_scan_audit_logs", ["actor_user_id"])
    op.create_index("ix_desk_scan_audit_logs_host_id", "desk_scan_audit_logs", ["host_id"])
    op.create_index("ix_desk_scan_audit_logs_event_id", "desk_scan_audit_logs", ["event_id"])
    op.create_index("ix_desk_scan_audit_logs_ticket_id", "desk_scan_audit_logs", ["ticket_id"])
    op.create_index(
        "ix_desk_scan_audit_logs_merch_order_item_id",
        "desk_scan_audit_logs",
        ["merch_order_item_id"],
    )
    op.create_index("ix_desk_scan_audit_logs_action", "desk_scan_audit_logs", ["action"])
    op.create_index("ix_desk_scan_audit_logs_result", "desk_scan_audit_logs", ["result"])
    op.create_index("ix_desk_scan_audit_logs_created_at", "desk_scan_audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("desk_scan_audit_logs")
