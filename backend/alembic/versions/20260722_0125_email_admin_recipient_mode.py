"""Add recipient_mode to email_admin_templates.

Revision ID: 20260722_0125
Revises: 20260722_0124
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260722_0125"
down_revision = "20260722_0124"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "email_admin_templates",
        sa.Column(
            "recipient_mode",
            sa.String(24),
            nullable=False,
            server_default="group",
        ),
    )


def downgrade() -> None:
    op.drop_column("email_admin_templates", "recipient_mode")
