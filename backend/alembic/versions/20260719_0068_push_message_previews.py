"""Add push_message_previews opt-in preference.

Revision ID: 20260719_0068
Revises: 20260719_0067
Create Date: 2026-07-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260719_0068"
down_revision = "20260719_0067"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_email_preferences",
        sa.Column(
            "push_message_previews",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.alter_column(
        "user_email_preferences", "push_message_previews", server_default=None
    )


def downgrade() -> None:
    op.drop_column("user_email_preferences", "push_message_previews")
