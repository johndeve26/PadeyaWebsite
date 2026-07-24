"""Alembic: guest checkout + claim tokens.

Revision ID: 20260721_0109
Revises: 20260721_0108
Create Date: 2026-07-21

Makes buyer_user_id nullable on orders/tickets for guest checkout.
Adds guest buyer fields and hashed claim tokens. Tickets/QR still issue
only after verified payment finalize.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260721_0109"
down_revision = "20260721_0108"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "orders",
        "buyer_user_id",
        existing_type=sa.Uuid(),
        nullable=True,
    )
    op.add_column(
        "orders",
        sa.Column("guest_buyer_name", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("guest_buyer_email", sa.String(length=320), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("guest_buyer_phone", sa.String(length=40), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("is_guest_checkout", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "orders",
        sa.Column("claim_token_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("claim_token_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("claimed_by_user_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_orders_guest_buyer_email", "orders", ["guest_buyer_email"], unique=False
    )
    op.create_index(
        "ix_orders_claim_token_hash", "orders", ["claim_token_hash"], unique=False
    )
    op.create_index(
        "ix_orders_claimed_by_user_id", "orders", ["claimed_by_user_id"], unique=False
    )
    op.create_foreign_key(
        "fk_orders_claimed_by_user_id_users",
        "orders",
        "users",
        ["claimed_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.alter_column(
        "tickets",
        "buyer_user_id",
        existing_type=sa.Uuid(),
        nullable=True,
    )
    op.add_column(
        "tickets",
        sa.Column("claimed_by_user_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "tickets",
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_tickets_claimed_by_user_id", "tickets", ["claimed_by_user_id"], unique=False
    )
    op.create_foreign_key(
        "fk_tickets_claimed_by_user_id_users",
        "tickets",
        "users",
        ["claimed_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Guest promo redemptions have no user until claim
    op.alter_column(
        "promo_redemptions",
        "user_id",
        existing_type=sa.Uuid(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "promo_redemptions",
        "user_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )

    op.drop_constraint(
        "fk_tickets_claimed_by_user_id_users", "tickets", type_="foreignkey"
    )
    op.drop_index("ix_tickets_claimed_by_user_id", table_name="tickets")
    op.drop_column("tickets", "claimed_at")
    op.drop_column("tickets", "claimed_by_user_id")
    op.alter_column(
        "tickets",
        "buyer_user_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )

    op.drop_constraint("fk_orders_claimed_by_user_id_users", "orders", type_="foreignkey")
    op.drop_index("ix_orders_claimed_by_user_id", table_name="orders")
    op.drop_index("ix_orders_claim_token_hash", table_name="orders")
    op.drop_index("ix_orders_guest_buyer_email", table_name="orders")
    op.drop_column("orders", "claimed_at")
    op.drop_column("orders", "claimed_by_user_id")
    op.drop_column("orders", "claim_token_expires_at")
    op.drop_column("orders", "claim_token_hash")
    op.drop_column("orders", "is_guest_checkout")
    op.drop_column("orders", "guest_buyer_phone")
    op.drop_column("orders", "guest_buyer_email")
    op.drop_column("orders", "guest_buyer_name")
    op.alter_column(
        "orders",
        "buyer_user_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )
