"""Alembic: checkout gift / attendee assignment fields.

Revision ID: 20260721_0108
Revises: 20260720_0107
Create Date: 2026-07-21

Adds purchase-mode + gift delivery flags on orders, per-ticket attendee
rows, and optional holder phone / gift markers on tickets. Tickets and QR
still issue only after verified payment finalize — this migration does not
change that invariant.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260721_0108"
down_revision = "20260720_0107"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column(
            "purchase_mode",
            sa.String(length=16),
            nullable=False,
            server_default="self",
        ),
    )
    op.add_column(
        "orders",
        sa.Column(
            "is_gift",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "orders",
        sa.Column(
            "purchased_for_someone_else",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "orders",
        sa.Column("gift_message", sa.Text(), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column(
            "send_ticket_to_recipient",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "orders",
        sa.Column(
            "keep_buyer_copy",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.add_column(
        "orders",
        sa.Column("recipient_name", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("recipient_email", sa.String(length=320), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("recipient_phone", sa.String(length=40), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("recipient_user_id", sa.Uuid(), nullable=True),
    )
    op.create_index(
        "ix_orders_recipient_user_id", "orders", ["recipient_user_id"], unique=False
    )
    op.create_foreign_key(
        "fk_orders_recipient_user_id_users",
        "orders",
        "users",
        ["recipient_user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "order_attendees",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("ticket_type_id", sa.Uuid(), nullable=False),
        sa.Column("unit_index", sa.Integer(), nullable=False),
        sa.Column("attendee_name", sa.String(length=200), nullable=False),
        sa.Column("attendee_email", sa.String(length=320), nullable=False),
        sa.Column("attendee_phone", sa.String(length=40), nullable=True),
        sa.Column("delivery_email", sa.String(length=320), nullable=True),
        sa.Column("delivery_phone", sa.String(length=40), nullable=True),
        sa.Column("recipient_user_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["order_id"], ["orders.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["ticket_type_id"], ["ticket_types.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["recipient_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "order_id",
            "ticket_type_id",
            "unit_index",
            name="uq_order_attendees_order_type_unit",
        ),
    )
    op.create_index(
        "ix_order_attendees_order_id", "order_attendees", ["order_id"], unique=False
    )
    op.create_index(
        "ix_order_attendees_ticket_type_id",
        "order_attendees",
        ["ticket_type_id"],
        unique=False,
    )
    op.create_index(
        "ix_order_attendees_recipient_user_id",
        "order_attendees",
        ["recipient_user_id"],
        unique=False,
    )

    op.add_column(
        "tickets",
        sa.Column("holder_phone", sa.String(length=40), nullable=True),
    )
    op.add_column(
        "tickets",
        sa.Column(
            "is_gift",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "tickets",
        sa.Column("recipient_user_id", sa.Uuid(), nullable=True),
    )
    op.create_index(
        "ix_tickets_recipient_user_id", "tickets", ["recipient_user_id"], unique=False
    )
    op.create_foreign_key(
        "fk_tickets_recipient_user_id_users",
        "tickets",
        "users",
        ["recipient_user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_tickets_recipient_user_id_users", "tickets", type_="foreignkey"
    )
    op.drop_index("ix_tickets_recipient_user_id", table_name="tickets")
    op.drop_column("tickets", "recipient_user_id")
    op.drop_column("tickets", "is_gift")
    op.drop_column("tickets", "holder_phone")

    op.drop_index("ix_order_attendees_recipient_user_id", table_name="order_attendees")
    op.drop_index("ix_order_attendees_ticket_type_id", table_name="order_attendees")
    op.drop_index("ix_order_attendees_order_id", table_name="order_attendees")
    op.drop_table("order_attendees")

    op.drop_constraint("fk_orders_recipient_user_id_users", "orders", type_="foreignkey")
    op.drop_index("ix_orders_recipient_user_id", table_name="orders")
    op.drop_column("orders", "recipient_user_id")
    op.drop_column("orders", "recipient_phone")
    op.drop_column("orders", "recipient_email")
    op.drop_column("orders", "recipient_name")
    op.drop_column("orders", "keep_buyer_copy")
    op.drop_column("orders", "send_ticket_to_recipient")
    op.drop_column("orders", "gift_message")
    op.drop_column("orders", "purchased_for_someone_else")
    op.drop_column("orders", "is_gift")
    op.drop_column("orders", "purchase_mode")
