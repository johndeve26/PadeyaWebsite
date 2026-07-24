"""AI Control Center: provider profiles, feature routes, health checks.

Revision ID: 20260722_0127
Revises: 20260722_0126
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260722_0127"
down_revision = "20260722_0126"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_provider_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider_type", sa.String(length=32), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("base_url", sa.String(length=500), nullable=True),
        sa.Column("api_key_encrypted", sa.Text(), nullable=True),
        sa.Column("api_key_last_four", sa.String(length=4), nullable=True),
        sa.Column("use_env_api_key", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("default_model", sa.String(length=120), nullable=True),
        sa.Column("available_models", sa.JSON(), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("health_status", sa.String(length=32), nullable=False, server_default="unknown"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("max_tokens_default", sa.Integer(), nullable=False, server_default="800"),
        sa.Column("rate_limit_per_minute", sa.Integer(), nullable=True),
        sa.Column("monthly_spend_limit_micros", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
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
            ["created_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ai_provider_profiles_enabled_priority",
        "ai_provider_profiles",
        ["is_enabled", "priority"],
    )

    op.create_table(
        "ai_feature_routes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("feature_key", sa.String(length=80), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("primary_provider_id", sa.Uuid(), nullable=True),
        sa.Column("primary_model", sa.String(length=120), nullable=True),
        sa.Column("fallback_provider_id", sa.Uuid(), nullable=True),
        sa.Column("fallback_model", sa.String(length=120), nullable=True),
        sa.Column(
            "template_fallback_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("daily_request_limit", sa.Integer(), nullable=True),
        sa.Column("monthly_request_limit", sa.Integer(), nullable=True),
        sa.Column("max_tokens", sa.Integer(), nullable=True),
        sa.Column("monthly_spend_cap_micros", sa.Integer(), nullable=True),
        sa.Column(
            "requires_human_review",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("allowed_permissions", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
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
            ["primary_provider_id"],
            ["ai_provider_profiles.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["fallback_provider_id"],
            ["ai_provider_profiles.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("feature_key", name="uq_ai_feature_routes_feature_key"),
    )
    op.create_index(
        "ix_ai_feature_routes_feature_key", "ai_feature_routes", ["feature_key"]
    )

    op.create_table(
        "ai_provider_health_checks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("error_message_safe", sa.Text(), nullable=True),
        sa.Column("checked_by_user_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["provider_id"], ["ai_provider_profiles.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["checked_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ai_provider_health_checks_provider_id",
        "ai_provider_health_checks",
        ["provider_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ai_provider_health_checks_provider_id",
        table_name="ai_provider_health_checks",
    )
    op.drop_table("ai_provider_health_checks")
    op.drop_index("ix_ai_feature_routes_feature_key", table_name="ai_feature_routes")
    op.drop_table("ai_feature_routes")
    op.drop_index(
        "ix_ai_provider_profiles_enabled_priority", table_name="ai_provider_profiles"
    )
    op.drop_table("ai_provider_profiles")
