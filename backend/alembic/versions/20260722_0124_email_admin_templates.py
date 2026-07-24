"""Admin editable email template storage.

Revision ID: 20260722_0124
Revises: 20260722_0123
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260722_0124"
down_revision = "20260722_0123"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "email_admin_templates",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("key", sa.String(80), nullable=False),
        sa.Column("category", sa.String(40), nullable=False),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("subject", sa.String(255), nullable=True),
        sa.Column("preview_text", sa.String(500), nullable=True),
        sa.Column("html_body", sa.Text(), nullable=True),
        sa.Column("text_body", sa.Text(), nullable=True),
        sa.Column(
            "variables_schema",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_enabled", sa.Boolean(), nullable=True),
        sa.Column("default_recipient_group", sa.String(32), nullable=False),
        sa.Column("recipient_group", sa.String(32), nullable=True),
        sa.Column(
            "custom_recipient_emails",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("delivery_mode", sa.String(16), nullable=False, server_default="instant"),
        sa.Column("threshold_amount", sa.Float(), nullable=True),
        sa.Column("updated_by_admin_id", sa.Uuid(as_uuid=True), nullable=True),
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
            ["updated_by_admin_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.UniqueConstraint("key", name="uq_email_admin_templates_key"),
    )
    op.create_index("ix_email_admin_templates_key", "email_admin_templates", ["key"])
    op.create_index(
        "ix_email_admin_templates_category", "email_admin_templates", ["category"]
    )

    op.create_table(
        "email_admin_notification_settings",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("master_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("digest_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("digest_hour_utc", sa.Integer(), nullable=False, server_default="8"),
        sa.Column("updated_by_admin_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_admin_id"], ["users.id"], ondelete="SET NULL"
        ),
    )


def downgrade() -> None:
    op.drop_table("email_admin_notification_settings")
    op.drop_table("email_admin_templates")
