"""Add first_four columns for admin secret fingerprints."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260721_0121"
down_revision = "20260721_0120"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "runtime_settings",
        sa.Column("first_four", sa.String(length=8), nullable=True),
    )
    op.add_column(
        "email_provider_settings",
        sa.Column("smtp_username_first4", sa.String(length=8), nullable=True),
    )
    op.add_column(
        "email_provider_settings",
        sa.Column("smtp_password_first4", sa.String(length=8), nullable=True),
    )
    op.add_column(
        "push_provider_settings",
        sa.Column("vapid_private_first4", sa.String(length=8), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("push_provider_settings", "vapid_private_first4")
    op.drop_column("email_provider_settings", "smtp_password_first4")
    op.drop_column("email_provider_settings", "smtp_username_first4")
    op.drop_column("runtime_settings", "first_four")
