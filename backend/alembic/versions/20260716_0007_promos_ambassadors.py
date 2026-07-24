"""promo codes and ambassador tracking

Revision ID: 20260716_0007
Revises: 20260716_0006
Create Date: 2026-07-16

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260716_0007"
down_revision: Union[str, Sequence[str], None] = "20260716_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "promo_codes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("discount_type", sa.String(length=32), nullable=False),
        sa.Column("discount_value", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("usage_limit", sa.Integer(), nullable=True),
        sa.Column("usage_count", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("event_id", sa.Uuid(), nullable=True),
        sa.Column("ticket_type_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("max_per_user", sa.Integer(), nullable=False),
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
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ticket_type_id"], ["ticket_types.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("host_id", "code", name="uq_promo_codes_host_code"),
    )
    op.create_index("ix_promo_codes_host_id", "promo_codes", ["host_id"], unique=False)
    op.create_index("ix_promo_codes_code", "promo_codes", ["code"], unique=False)
    op.create_index("ix_promo_codes_event_id", "promo_codes", ["event_id"], unique=False)
    op.create_index("ix_promo_codes_ticket_type_id", "promo_codes", ["ticket_type_id"], unique=False)
    op.create_index("ix_promo_codes_status", "promo_codes", ["status"], unique=False)

    op.create_table(
        "ambassadors",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("referral_code", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("commission_rate_percent", sa.Numeric(precision=5, scale=2), nullable=False),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("host_id", "referral_code", name="uq_ambassadors_host_referral"),
    )
    op.create_index("ix_ambassadors_host_id", "ambassadors", ["host_id"], unique=False)
    op.create_index("ix_ambassadors_user_id", "ambassadors", ["user_id"], unique=False)
    op.create_index("ix_ambassadors_referral_code", "ambassadors", ["referral_code"], unique=False)
    op.create_index("ix_ambassadors_status", "ambassadors", ["status"], unique=False)

    op.add_column(
        "orders",
        sa.Column("discount_amount", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0"),
    )
    op.add_column("orders", sa.Column("promo_code_id", sa.Uuid(), nullable=True))
    op.add_column("orders", sa.Column("promo_code_snapshot", sa.String(length=64), nullable=True))
    op.add_column("orders", sa.Column("ambassador_id", sa.Uuid(), nullable=True))
    op.add_column("orders", sa.Column("referral_code", sa.String(length=64), nullable=True))
    op.create_foreign_key(
        "fk_orders_promo_code_id",
        "orders",
        "promo_codes",
        ["promo_code_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_orders_ambassador_id",
        "orders",
        "ambassadors",
        ["ambassador_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_orders_promo_code_id", "orders", ["promo_code_id"], unique=False)
    op.create_index("ix_orders_ambassador_id", "orders", ["ambassador_id"], unique=False)

    op.create_table(
        "promo_redemptions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("promo_code_id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("discount_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("redeemed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["promo_code_id"], ["promo_codes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id", name="uq_promo_redemptions_order_id"),
    )
    op.create_index("ix_promo_redemptions_promo_code_id", "promo_redemptions", ["promo_code_id"])
    op.create_index("ix_promo_redemptions_order_id", "promo_redemptions", ["order_id"])
    op.create_index("ix_promo_redemptions_user_id", "promo_redemptions", ["user_id"])
    op.create_index("ix_promo_redemptions_status", "promo_redemptions", ["status"])

    op.create_table(
        "promo_clicks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ambassador_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=True),
        sa.Column("landing_path", sa.String(length=500), nullable=True),
        sa.Column("ip_hash", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["ambassador_id"], ["ambassadors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_promo_clicks_ambassador_id", "promo_clicks", ["ambassador_id"])
    op.create_index("ix_promo_clicks_event_id", "promo_clicks", ["event_id"])
    op.create_index("ix_promo_clicks_ip_hash", "promo_clicks", ["ip_hash"])
    op.create_index("ix_promo_clicks_created_at", "promo_clicks", ["created_at"])

    op.create_table(
        "ambassador_sales",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ambassador_id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("tickets_sold", sa.Integer(), nullable=False),
        sa.Column("revenue_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("commission_owed", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["ambassador_id"], ["ambassadors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id", name="uq_ambassador_sales_order_id"),
    )
    op.create_index("ix_ambassador_sales_ambassador_id", "ambassador_sales", ["ambassador_id"])
    op.create_index("ix_ambassador_sales_order_id", "ambassador_sales", ["order_id"])
    op.create_index("ix_ambassador_sales_event_id", "ambassador_sales", ["event_id"])
    op.create_index("ix_ambassador_sales_created_at", "ambassador_sales", ["created_at"])


def downgrade() -> None:
    op.drop_table("ambassador_sales")
    op.drop_table("promo_clicks")
    op.drop_table("promo_redemptions")
    op.drop_constraint("fk_orders_ambassador_id", "orders", type_="foreignkey")
    op.drop_constraint("fk_orders_promo_code_id", "orders", type_="foreignkey")
    op.drop_index("ix_orders_ambassador_id", table_name="orders")
    op.drop_index("ix_orders_promo_code_id", table_name="orders")
    op.drop_column("orders", "referral_code")
    op.drop_column("orders", "ambassador_id")
    op.drop_column("orders", "promo_code_snapshot")
    op.drop_column("orders", "promo_code_id")
    op.drop_column("orders", "discount_amount")
    op.drop_table("ambassadors")
    op.drop_table("promo_codes")
