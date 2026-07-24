"""Admin-managed email provider / SMTP settings singleton.

Revision ID: 20260719_0061
Revises: 20260719_0060
Create Date: 2026-07-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260719_0061"
down_revision = "20260719_0060"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "email_provider_settings",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("singleton_key", sa.String(32), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("provider", sa.String(32), nullable=False, server_default="log"),
        sa.Column("dev_mode", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "from_email",
            sa.String(320),
            nullable=False,
            server_default="noreply@padeya.com",
        ),
        sa.Column(
            "from_name", sa.String(120), nullable=False, server_default="Pàdéyá"
        ),
        sa.Column("reply_to", sa.String(320), nullable=True),
        sa.Column("support_email", sa.String(320), nullable=True),
        sa.Column("smtp_host", sa.String(255), nullable=True),
        sa.Column("smtp_port", sa.Integer(), nullable=False, server_default="587"),
        sa.Column("smtp_username", sa.String(320), nullable=True),
        sa.Column("smtp_password_enc", sa.Text(), nullable=True),
        sa.Column(
            "smtp_use_tls", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column("managed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_test_ok", sa.Boolean(), nullable=True),
        sa.Column("last_test_error", sa.Text(), nullable=True),
        sa.Column("updated_by_user_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.UniqueConstraint(
            "singleton_key", name="uq_email_provider_settings_singleton"
        ),
    )


def downgrade() -> None:
    op.drop_table("email_provider_settings")
