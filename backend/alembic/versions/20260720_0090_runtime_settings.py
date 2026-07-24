"""Create runtime_settings table for Admin Runtime Settings overrides.

Revision ID: 20260720_0090
Revises: 20260720_0089
Create Date: 2026-07-20
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260720_0090"
down_revision = "20260720_0089"
branch_labels = None
depends_on = None


def upgrade() -> None:
    json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
    op.create_table(
        "runtime_settings",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("value_encrypted", sa.Text(), nullable=True),
        sa.Column("value_plain", json_type, nullable=True),
        sa.Column(
            "value_type",
            sa.String(length=32),
            nullable=False,
            server_default="string",
        ),
        sa.Column(
            "is_secret",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "is_editable",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "is_required_for_runtime",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "source", sa.String(length=16), nullable=False, server_default="db"
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("validation_schema_json", json_type, nullable=True),
        sa.Column("last_four", sa.String(length=8), nullable=True),
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
        sa.UniqueConstraint("key", name="uq_runtime_settings_key"),
    )
    op.create_index("ix_runtime_settings_category", "runtime_settings", ["category"])
    op.create_index("ix_runtime_settings_key", "runtime_settings", ["key"])


def downgrade() -> None:
    op.drop_index("ix_runtime_settings_key", table_name="runtime_settings")
    op.drop_index("ix_runtime_settings_category", table_name="runtime_settings")
    op.drop_table("runtime_settings")
