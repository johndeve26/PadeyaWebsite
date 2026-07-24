"""orders payments tickets qr

Revision ID: 20260716_0003
Revises: 20260716_0002
Create Date: 2026-07-16

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260716_0003"
down_revision: Union[str, Sequence[str], None] = "20260716_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ticket_types",
        sa.Column("quantity_sold", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "ticket_types",
        sa.Column("quantity_reserved", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "orders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reference", sa.String(length=64), nullable=False),
        sa.Column("buyer_user_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("subtotal_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("buyer_email", sa.String(length=320), nullable=False),
        sa.Column("buyer_name", sa.String(length=200), nullable=False),
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
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["buyer_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_orders_reference", "orders", ["reference"], unique=True)
    op.create_index("ix_orders_buyer_user_id", "orders", ["buyer_user_id"], unique=False)
    op.create_index("ix_orders_event_id", "orders", ["event_id"], unique=False)
    op.create_index("ix_orders_status", "orders", ["status"], unique=False)

    op.create_table(
        "order_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("ticket_type_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("ticket_type_name", sa.String(length=160), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ticket_type_id"], ["ticket_types.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_order_items_order_id", "order_items", ["order_id"], unique=False)
    op.create_index(
        "ix_order_items_ticket_type_id", "order_items", ["ticket_type_id"], unique=False
    )

    op.create_table(
        "payments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("reference", sa.String(length=64), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("provider_payment_id", sa.String(length=128), nullable=True),
        sa.Column("authorization_url", sa.String(length=500), nullable=True),
        sa.Column("access_code", sa.String(length=128), nullable=True),
        sa.Column("raw_response", sa.JSON(), nullable=True),
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
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_payments_order_id", "payments", ["order_id"], unique=False)
    op.create_index("ix_payments_reference", "payments", ["reference"], unique=True)
    op.create_index("ix_payments_status", "payments", ["status"], unique=False)

    op.create_table(
        "payment_webhook_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("event_key", sa.String(length=191), nullable=False),
        sa.Column("reference", sa.String(length=64), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("processing_status", sa.String(length=32), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "event_key", name="uq_payment_webhook_events_key"),
    )
    op.create_index(
        "ix_payment_webhook_events_event_key",
        "payment_webhook_events",
        ["event_key"],
        unique=False,
    )
    op.create_index(
        "ix_payment_webhook_events_reference",
        "payment_webhook_events",
        ["reference"],
        unique=False,
    )

    op.create_table(
        "tickets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("public_code", sa.String(length=40), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("order_item_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("ticket_type_id", sa.Uuid(), nullable=False),
        sa.Column("buyer_user_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("ticket_type_name", sa.String(length=160), nullable=False),
        sa.Column("holder_name", sa.String(length=200), nullable=False),
        sa.Column("holder_email", sa.String(length=320), nullable=False),
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
        sa.ForeignKeyConstraint(["buyer_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["order_item_id"], ["order_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ticket_type_id"], ["ticket_types.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_code", name="uq_tickets_public_code"),
    )
    op.create_index("ix_tickets_public_code", "tickets", ["public_code"], unique=False)
    op.create_index("ix_tickets_order_id", "tickets", ["order_id"], unique=False)
    op.create_index("ix_tickets_buyer_user_id", "tickets", ["buyer_user_id"], unique=False)
    op.create_index("ix_tickets_event_id", "tickets", ["event_id"], unique=False)
    op.create_index("ix_tickets_status", "tickets", ["status"], unique=False)

    op.create_table(
        "ticket_qr_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ticket_id", sa.Uuid(), nullable=False),
        sa.Column("jti_hash", sa.String(length=64), nullable=False),
        sa.Column("signed_payload", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticket_id", name="uq_ticket_qr_tokens_ticket_id"),
    )
    op.create_index("ix_ticket_qr_tokens_ticket_id", "ticket_qr_tokens", ["ticket_id"], unique=False)
    op.create_index("ix_ticket_qr_tokens_jti_hash", "ticket_qr_tokens", ["jti_hash"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_ticket_qr_tokens_jti_hash", table_name="ticket_qr_tokens")
    op.drop_index("ix_ticket_qr_tokens_ticket_id", table_name="ticket_qr_tokens")
    op.drop_table("ticket_qr_tokens")
    op.drop_index("ix_tickets_status", table_name="tickets")
    op.drop_index("ix_tickets_event_id", table_name="tickets")
    op.drop_index("ix_tickets_buyer_user_id", table_name="tickets")
    op.drop_index("ix_tickets_order_id", table_name="tickets")
    op.drop_index("ix_tickets_public_code", table_name="tickets")
    op.drop_table("tickets")
    op.drop_index("ix_payment_webhook_events_reference", table_name="payment_webhook_events")
    op.drop_index("ix_payment_webhook_events_event_key", table_name="payment_webhook_events")
    op.drop_table("payment_webhook_events")
    op.drop_index("ix_payments_status", table_name="payments")
    op.drop_index("ix_payments_reference", table_name="payments")
    op.drop_index("ix_payments_order_id", table_name="payments")
    op.drop_table("payments")
    op.drop_index("ix_order_items_ticket_type_id", table_name="order_items")
    op.drop_index("ix_order_items_order_id", table_name="order_items")
    op.drop_table("order_items")
    op.drop_index("ix_orders_status", table_name="orders")
    op.drop_index("ix_orders_event_id", table_name="orders")
    op.drop_index("ix_orders_buyer_user_id", table_name="orders")
    op.drop_index("ix_orders_reference", table_name="orders")
    op.drop_table("orders")
    op.drop_column("ticket_types", "quantity_reserved")
    op.drop_column("ticket_types", "quantity_sold")
