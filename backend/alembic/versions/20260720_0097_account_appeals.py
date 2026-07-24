"""Account suspensions (public metadata) + appeals.

Revision ID: 20260720_0097
Revises: 20260720_0096
Create Date: 2026-07-20
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260720_0097"
down_revision = "20260720_0096"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "account_suspensions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("reason_category", sa.String(length=64), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_admin_id", sa.Uuid(), nullable=False),
        sa.Column("lifted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lifted_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_admin_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lifted_by_admin_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_account_suspensions_user_id", "account_suspensions", ["user_id"])
    op.create_index("ix_account_suspensions_status", "account_suspensions", ["status"])

    op.create_table(
        "account_appeals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("suspension_id", sa.Uuid(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("admin_reply", sa.String(length=1000), nullable=True),
        sa.Column("reviewed_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["reviewed_by_admin_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["suspension_id"], ["account_suspensions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_account_appeals_user_id", "account_appeals", ["user_id"])
    op.create_index("ix_account_appeals_status", "account_appeals", ["status"])
    op.create_index("ix_account_appeals_suspension_id", "account_appeals", ["suspension_id"])


def downgrade() -> None:
    op.drop_index("ix_account_appeals_suspension_id", table_name="account_appeals")
    op.drop_index("ix_account_appeals_status", table_name="account_appeals")
    op.drop_index("ix_account_appeals_user_id", table_name="account_appeals")
    op.drop_table("account_appeals")
    op.drop_index("ix_account_suspensions_status", table_name="account_suspensions")
    op.drop_index("ix_account_suspensions_user_id", table_name="account_suspensions")
    op.drop_table("account_suspensions")
