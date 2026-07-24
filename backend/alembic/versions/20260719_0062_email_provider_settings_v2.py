"""Reshape email_provider_settings for Fernet secrets + multi-row activate.

Revision ID: 20260719_0062
Revises: 20260719_0061
Create Date: 2026-07-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260719_0062"
down_revision = "20260719_0061"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rebuild table — v1 was a short-lived singleton; migrate best-effort.
    op.rename_table("email_provider_settings", "email_provider_settings_legacy_v1")

    op.create_table(
        "email_provider_settings",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("provider", sa.String(32), nullable=False, server_default="log"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "email_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column("dev_mode", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("smtp_host", sa.String(255), nullable=True),
        sa.Column("smtp_port", sa.Integer(), nullable=True),
        sa.Column(
            "smtp_use_tls", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "smtp_use_ssl", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("smtp_username_encrypted", sa.Text(), nullable=True),
        sa.Column("smtp_password_encrypted", sa.Text(), nullable=True),
        sa.Column("smtp_from_email", sa.String(320), nullable=True),
        sa.Column("smtp_from_name", sa.String(120), nullable=True),
        sa.Column("smtp_reply_to", sa.String(320), nullable=True),
        sa.Column("smtp_username_last4", sa.String(8), nullable=True),
        sa.Column("smtp_password_last4", sa.String(8), nullable=True),
        sa.Column("last_test_status", sa.String(32), nullable=True),
        sa.Column("last_test_error", sa.Text(), nullable=True),
        sa.Column("last_test_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_successful_send_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(as_uuid=True), nullable=True),
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
            ["created_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
    )
    op.create_index(
        "ix_email_provider_settings_is_active",
        "email_provider_settings",
        ["is_active"],
    )

    # Best-effort copy of non-secret fields from legacy singleton.
    # Passwords are NOT copied — re-enter via Admin (encryption scheme changed).
    conn = op.get_bind()
    rows = conn.execute(
        sa.text(
            """
            SELECT id, provider, enabled, dev_mode, from_email, from_name, reply_to,
                   smtp_host, smtp_port, smtp_use_tls, last_tested_at, last_test_ok,
                   last_test_error, updated_by_user_id, created_at, updated_at, managed
            FROM email_provider_settings_legacy_v1
            """
        )
    ).mappings().all()
    for row in rows:
        status = None
        if row["last_test_ok"] is True:
            status = "success"
        elif row["last_test_ok"] is False:
            status = "failed"
        conn.execute(
            sa.text(
                """
                INSERT INTO email_provider_settings (
                    id, provider, is_active, email_enabled, dev_mode,
                    smtp_host, smtp_port, smtp_use_tls, smtp_use_ssl,
                    smtp_from_email, smtp_from_name, smtp_reply_to,
                    last_test_status, last_test_error, last_test_at,
                    updated_by_user_id, created_at, updated_at
                ) VALUES (
                    :id, :provider, :is_active, :email_enabled, :dev_mode,
                    :smtp_host, :smtp_port, :smtp_use_tls, false,
                    :smtp_from_email, :smtp_from_name, :smtp_reply_to,
                    :last_test_status, :last_test_error, :last_test_at,
                    :updated_by_user_id, :created_at, :updated_at
                )
                """
            ),
            {
                "id": row["id"],
                "provider": row["provider"] or "log",
                "is_active": bool(row["managed"]),
                "email_enabled": bool(row["enabled"]),
                "dev_mode": bool(row["dev_mode"]),
                "smtp_host": row["smtp_host"],
                "smtp_port": row["smtp_port"],
                "smtp_use_tls": bool(row["smtp_use_tls"]),
                "smtp_from_email": row["from_email"],
                "smtp_from_name": row["from_name"],
                "smtp_reply_to": row["reply_to"],
                "last_test_status": status,
                "last_test_error": row["last_test_error"],
                "last_test_at": row["last_tested_at"],
                "updated_by_user_id": row["updated_by_user_id"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            },
        )

    op.drop_table("email_provider_settings_legacy_v1")


def downgrade() -> None:
    op.drop_index("ix_email_provider_settings_is_active", table_name="email_provider_settings")
    op.drop_table("email_provider_settings")
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
