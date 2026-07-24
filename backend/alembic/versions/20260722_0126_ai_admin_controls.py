"""AI admin controls: platform spend settings + per-feature configs.

Revision ID: 20260722_0126
Revises: 20260722_0125
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260722_0126"
down_revision = "20260722_0125"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_platform_settings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("monthly_spend_cap_micros", sa.Integer(), nullable=True),
        sa.Column(
            "warning_threshold_pct",
            sa.Integer(),
            nullable=False,
            server_default="80",
        ),
        sa.Column(
            "hard_stop_threshold_pct",
            sa.Integer(),
            nullable=False,
            server_default="100",
        ),
        sa.Column(
            "hard_stop_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "allow_template_fallback_when_capped",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "ai_feature_configs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("feature_key", sa.String(length=80), nullable=False),
        sa.Column(
            "enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column("allowed_permissions", sa.JSON(), nullable=True),
        sa.Column("daily_request_limit", sa.Integer(), nullable=True),
        sa.Column("monthly_request_limit", sa.Integer(), nullable=True),
        sa.Column("token_limit_per_request", sa.Integer(), nullable=True),
        sa.Column(
            "requires_human_review",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "status", sa.String(length=32), nullable=False, server_default="active"
        ),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("feature_key", name="uq_ai_feature_configs_feature_key"),
    )
    op.create_index(
        "ix_ai_feature_configs_feature_key", "ai_feature_configs", ["feature_key"]
    )


def downgrade() -> None:
    op.drop_index("ix_ai_feature_configs_feature_key", table_name="ai_feature_configs")
    op.drop_table("ai_feature_configs")
    op.drop_table("ai_platform_settings")
