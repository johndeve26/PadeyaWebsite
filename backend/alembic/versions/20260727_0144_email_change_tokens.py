"""Alembic: pending email change confirmation tokens.

Revision ID: 20260727_0144
Revises: 20260726_0143
Create Date: 2026-07-27

Stores hashed codes + target email until the user confirms a change.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260727_0144"
down_revision = "20260726_0143"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "email_change_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("new_email", sa.String(length=320), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_email_change_tokens_user_id",
        "email_change_tokens",
        ["user_id"],
    )
    op.create_index(
        "ix_email_change_tokens_new_email",
        "email_change_tokens",
        ["new_email"],
    )
    op.create_index(
        "ix_email_change_tokens_code_hash",
        "email_change_tokens",
        ["code_hash"],
    )


def downgrade() -> None:
    op.drop_index("ix_email_change_tokens_code_hash", table_name="email_change_tokens")
    op.drop_index("ix_email_change_tokens_new_email", table_name="email_change_tokens")
    op.drop_index("ix_email_change_tokens_user_id", table_name="email_change_tokens")
    op.drop_table("email_change_tokens")
