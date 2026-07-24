"""Add account_status + account_restrictions for admin status MVP.

Revision ID: 20260720_0095
Revises: 20260720_0094
Create Date: 2026-07-20
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON

revision = "20260720_0095"
down_revision = "20260720_0094"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "account_status",
            sa.String(length=32),
            nullable=False,
            server_default="active",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "account_restrictions",
            JSON().with_variant(JSONB, "postgresql"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_users_account_status", "users", ["account_status"], unique=False
    )

    # Backfill from existing soft-lifecycle columns.
    op.execute(
        sa.text(
            """
            UPDATE users
            SET account_status = 'suspended'
            WHERE is_active = false OR deactivated_at IS NOT NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE users
            SET account_status = 'under_review'
            WHERE account_status = 'active'
              AND under_review_at IS NOT NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE users
            SET account_restrictions = '["cannot_promote_as_ambassador"]'
            WHERE ambassadors_blocked = true
              AND (account_restrictions IS NULL)
            """
        )
    )

    op.alter_column("users", "account_status", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_users_account_status", table_name="users")
    op.drop_column("users", "account_restrictions")
    op.drop_column("users", "account_status")
