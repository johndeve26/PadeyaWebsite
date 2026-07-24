"""Add push_reviews and push_security preference columns.

Revision ID: 20260719_0067
Revises: 20260719_0066
Create Date: 2026-07-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260719_0067"
down_revision = "20260719_0066"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_email_preferences",
        sa.Column(
            "push_reviews",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.add_column(
        "user_email_preferences",
        sa.Column(
            "push_security",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.alter_column("user_email_preferences", "push_reviews", server_default=None)
    op.alter_column("user_email_preferences", "push_security", server_default=None)


def downgrade() -> None:
    op.drop_column("user_email_preferences", "push_security")
    op.drop_column("user_email_preferences", "push_reviews")
