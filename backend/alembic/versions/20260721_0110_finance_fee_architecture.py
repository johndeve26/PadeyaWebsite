"""Alembic: platform fee settings, host overrides, order fee snapshots.

Revision ID: 20260721_0110
Revises: 20260721_0109
Create Date: 2026-07-21

Configurable Pàdéyá fee architecture foundation. Money amounts for fixed
fees and snapshots use integer minor units. Does not alter checkout or
payout flows yet.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260721_0110"
down_revision = "20260721_0109"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "platform_fee_settings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("fee_key", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=200), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("fee_type", sa.String(length=16), nullable=False),
        sa.Column("percentage_value", sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column("fixed_value", sa.BigInteger(), nullable=True),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("payer", sa.String(length=16), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("applies_to", sa.String(length=128), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("updated_by_admin_id", sa.Uuid(), nullable=True),
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
        sa.ForeignKeyConstraint(["created_by_admin_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_admin_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_platform_fee_settings_fee_key", "platform_fee_settings", ["fee_key"])
    op.create_index("ix_platform_fee_settings_category", "platform_fee_settings", ["category"])
    op.create_index(
        "ix_platform_fee_settings_effective_from",
        "platform_fee_settings",
        ["effective_from"],
    )
    op.create_index(
        "ix_platform_fee_settings_effective_to",
        "platform_fee_settings",
        ["effective_to"],
    )
    op.create_index(
        "ix_platform_fee_settings_created_at",
        "platform_fee_settings",
        ["created_at"],
    )

    op.create_table(
        "host_fee_overrides",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=False),
        sa.Column("fee_key", sa.String(length=64), nullable=False),
        sa.Column("percentage_value", sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column("fixed_value", sa.BigInteger(), nullable=True),
        sa.Column("payer", sa.String(length=16), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("updated_by_admin_id", sa.Uuid(), nullable=True),
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
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_admin_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_admin_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_host_fee_overrides_host_id", "host_fee_overrides", ["host_id"])
    op.create_index("ix_host_fee_overrides_fee_key", "host_fee_overrides", ["fee_key"])
    op.create_index(
        "ix_host_fee_overrides_effective_from",
        "host_fee_overrides",
        ["effective_from"],
    )
    op.create_index(
        "ix_host_fee_overrides_effective_to",
        "host_fee_overrides",
        ["effective_to"],
    )
    op.create_index(
        "ix_host_fee_overrides_created_at",
        "host_fee_overrides",
        ["created_at"],
    )

    op.create_table(
        "order_fee_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=True),
        sa.Column("fee_key", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=200), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("fee_type", sa.String(length=16), nullable=False),
        sa.Column("percentage_value", sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column("fixed_value", sa.BigInteger(), nullable=True),
        sa.Column("payer", sa.String(length=16), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_order_fee_snapshots_order_id", "order_fee_snapshots", ["order_id"])
    op.create_index("ix_order_fee_snapshots_host_id", "order_fee_snapshots", ["host_id"])
    op.create_index("ix_order_fee_snapshots_fee_key", "order_fee_snapshots", ["fee_key"])
    op.create_index(
        "ix_order_fee_snapshots_created_at",
        "order_fee_snapshots",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_order_fee_snapshots_created_at", table_name="order_fee_snapshots")
    op.drop_index("ix_order_fee_snapshots_fee_key", table_name="order_fee_snapshots")
    op.drop_index("ix_order_fee_snapshots_host_id", table_name="order_fee_snapshots")
    op.drop_index("ix_order_fee_snapshots_order_id", table_name="order_fee_snapshots")
    op.drop_table("order_fee_snapshots")

    op.drop_index("ix_host_fee_overrides_created_at", table_name="host_fee_overrides")
    op.drop_index("ix_host_fee_overrides_effective_to", table_name="host_fee_overrides")
    op.drop_index("ix_host_fee_overrides_effective_from", table_name="host_fee_overrides")
    op.drop_index("ix_host_fee_overrides_fee_key", table_name="host_fee_overrides")
    op.drop_index("ix_host_fee_overrides_host_id", table_name="host_fee_overrides")
    op.drop_table("host_fee_overrides")

    op.drop_index("ix_platform_fee_settings_created_at", table_name="platform_fee_settings")
    op.drop_index("ix_platform_fee_settings_effective_to", table_name="platform_fee_settings")
    op.drop_index("ix_platform_fee_settings_effective_from", table_name="platform_fee_settings")
    op.drop_index("ix_platform_fee_settings_category", table_name="platform_fee_settings")
    op.drop_index("ix_platform_fee_settings_fee_key", table_name="platform_fee_settings")
    op.drop_table("platform_fee_settings")
