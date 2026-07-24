"""Fan Passport public profile + privacy settings.

Revision ID: 20260718_0038
Revises: 20260718_0037
Create Date: 2026-07-18
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260718_0038"
down_revision = "20260718_0037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "fan_passports",
        sa.Column("username", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "fan_passports",
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "fan_passports",
        sa.Column("tagline", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "fan_passports",
        sa.Column("bio", sa.Text(), nullable=True),
    )
    op.add_column(
        "fan_passports",
        sa.Column(
            "visibility",
            sa.String(length=16),
            nullable=False,
            server_default="private",
        ),
    )
    op.add_column(
        "fan_passports",
        sa.Column(
            "show_attended_events",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.add_column(
        "fan_passports",
        sa.Column(
            "show_badges",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.add_column(
        "fan_passports",
        sa.Column(
            "show_followed_hosts",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.add_column(
        "fan_passports",
        sa.Column(
            "show_reviews",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.add_column(
        "fan_passports",
        sa.Column(
            "show_vault_unlocks",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.add_column(
        "fan_passports",
        sa.Column(
            "show_city_category_stats",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.add_column(
        "fan_passports",
        sa.Column(
            "hide_private_events_always",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.create_index(
        "ix_fan_passports_username",
        "fan_passports",
        ["username"],
        unique=True,
    )
    op.create_index(
        "ix_fan_passports_visibility",
        "fan_passports",
        ["visibility"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_fan_passports_visibility", table_name="fan_passports")
    op.drop_index("ix_fan_passports_username", table_name="fan_passports")
    op.drop_column("fan_passports", "hide_private_events_always")
    op.drop_column("fan_passports", "show_city_category_stats")
    op.drop_column("fan_passports", "show_vault_unlocks")
    op.drop_column("fan_passports", "show_reviews")
    op.drop_column("fan_passports", "show_followed_hosts")
    op.drop_column("fan_passports", "show_badges")
    op.drop_column("fan_passports", "show_attended_events")
    op.drop_column("fan_passports", "visibility")
    op.drop_column("fan_passports", "bio")
    op.drop_column("fan_passports", "tagline")
    op.drop_column("fan_passports", "avatar_url")
    op.drop_column("fan_passports", "username")
