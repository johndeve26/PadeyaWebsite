"""fan passport badges loyalty

Revision ID: 20260716_0011
Revises: 20260716_0010
Create Date: 2026-07-16

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260716_0011"
down_revision: Union[str, Sequence[str], None] = "20260716_0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "fan_passports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("tickets_bought", sa.Integer(), nullable=False),
        sa.Column("events_attended", sa.Integer(), nullable=False),
        sa.Column("hosts_followed", sa.Integer(), nullable=False),
        sa.Column("vip_purchases", sa.Integer(), nullable=False),
        sa.Column("vault_unlocks", sa.Integer(), nullable=False),
        sa.Column("is_superfan", sa.Boolean(), nullable=False),
        sa.Column("favorite_categories", sa.JSON(), nullable=True),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_fan_passports_user_id"),
    )
    op.create_index("ix_fan_passports_user_id", "fan_passports", ["user_id"])

    op.create_table(
        "fan_badges",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("criteria_key", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_fan_badges_slug", "fan_badges", ["slug"])
    op.create_index("ix_fan_badges_criteria_key", "fan_badges", ["criteria_key"])

    op.create_table(
        "user_badges",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("badge_id", sa.Uuid(), nullable=False),
        sa.Column(
            "awarded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["badge_id"], ["fan_badges.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "badge_id", name="uq_user_badges_user_badge"),
    )
    op.create_index("ix_user_badges_user_id", "user_badges", ["user_id"])
    op.create_index("ix_user_badges_badge_id", "user_badges", ["badge_id"])
    op.create_index("ix_user_badges_awarded_at", "user_badges", ["awarded_at"])

    op.create_table(
        "loyalty_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=False),
        sa.Column("tickets_bought", sa.Integer(), nullable=False),
        sa.Column("check_ins", sa.Integer(), nullable=False),
        sa.Column("vip_purchases", sa.Integer(), nullable=False),
        sa.Column("is_superfan", sa.Boolean(), nullable=False),
        sa.Column("follows_host", sa.Boolean(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "host_id", name="uq_loyalty_records_user_host"),
    )
    op.create_index("ix_loyalty_records_user_id", "loyalty_records", ["user_id"])
    op.create_index("ix_loyalty_records_host_id", "loyalty_records", ["host_id"])


def downgrade() -> None:
    op.drop_index("ix_loyalty_records_host_id", table_name="loyalty_records")
    op.drop_index("ix_loyalty_records_user_id", table_name="loyalty_records")
    op.drop_table("loyalty_records")
    op.drop_index("ix_user_badges_awarded_at", table_name="user_badges")
    op.drop_index("ix_user_badges_badge_id", table_name="user_badges")
    op.drop_index("ix_user_badges_user_id", table_name="user_badges")
    op.drop_table("user_badges")
    op.drop_index("ix_fan_badges_criteria_key", table_name="fan_badges")
    op.drop_index("ix_fan_badges_slug", table_name="fan_badges")
    op.drop_table("fan_badges")
    op.drop_index("ix_fan_passports_user_id", table_name="fan_passports")
    op.drop_table("fan_passports")
