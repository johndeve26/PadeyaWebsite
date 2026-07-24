"""advanced ticketing phase 17

Revision ID: 20260716_0016
Revises: 20260716_0015
Create Date: 2026-07-16

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260716_0016"
down_revision: Union[str, Sequence[str], None] = "20260716_0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ticket_types",
        sa.Column("seats_per_unit", sa.Integer(), server_default="1", nullable=False),
    )

    op.add_column(
        "tickets",
        sa.Column("qr_mode", sa.String(length=32), server_default="static", nullable=False),
    )
    op.add_column("tickets", sa.Column("device_binding_hash", sa.String(length=64), nullable=True))
    op.add_column("tickets", sa.Column("device_bound_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("tickets", sa.Column("seat_label", sa.String(length=80), nullable=True))
    op.add_column("tickets", sa.Column("table_label", sa.String(length=80), nullable=True))
    op.add_column("tickets", sa.Column("attendee_index", sa.Integer(), nullable=True))

    op.add_column(
        "ticket_qr_tokens",
        sa.Column("rotation_version", sa.Integer(), server_default="1", nullable=False),
    )
    op.add_column(
        "ticket_qr_tokens",
        sa.Column("is_rotating", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column(
        "ticket_qr_tokens",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )

    op.create_table(
        "ticket_transfers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ticket_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("from_user_id", sa.Uuid(), nullable=False),
        sa.Column("to_user_id", sa.Uuid(), nullable=False),
        sa.Column("from_email", sa.String(length=320), nullable=False),
        sa.Column("to_email", sa.String(length=320), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["from_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["to_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ticket_transfers_ticket_id", "ticket_transfers", ["ticket_id"])
    op.create_index("ix_ticket_transfers_event_id", "ticket_transfers", ["event_id"])
    op.create_index("ix_ticket_transfers_from_user_id", "ticket_transfers", ["from_user_id"])
    op.create_index("ix_ticket_transfers_to_user_id", "ticket_transfers", ["to_user_id"])

    op.create_table(
        "ticket_groups",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("order_item_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("ticket_type_id", sa.Uuid(), nullable=False),
        sa.Column("buyer_user_id", sa.Uuid(), nullable=False),
        sa.Column("group_kind", sa.String(length=32), nullable=False),
        sa.Column("expected_size", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=160), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
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
    )
    op.create_index("ix_ticket_groups_order_id", "ticket_groups", ["order_id"])
    op.create_index("ix_ticket_groups_event_id", "ticket_groups", ["event_id"])

    op.create_table(
        "ticket_group_members",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("group_id", sa.Uuid(), nullable=False),
        sa.Column("ticket_id", sa.Uuid(), nullable=False),
        sa.Column("attendee_index", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["group_id"], ["ticket_groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticket_id", name="uq_ticket_group_members_ticket_id"),
    )
    op.create_index("ix_ticket_group_members_group_id", "ticket_group_members", ["group_id"])

    op.create_table(
        "table_reservations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("ticket_type_id", sa.Uuid(), nullable=True),
        sa.Column("group_id", sa.Uuid(), nullable=True),
        sa.Column("primary_ticket_id", sa.Uuid(), nullable=True),
        sa.Column("table_label", sa.String(length=80), nullable=False),
        sa.Column("seat_label", sa.String(length=80), nullable=True),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("assignment_note", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["group_id"], ["ticket_groups.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["primary_ticket_id"], ["tickets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["ticket_type_id"], ["ticket_types.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_table_reservations_event_id", "table_reservations", ["event_id"])
    op.create_index("ix_table_reservations_status", "table_reservations", ["status"])

    op.create_table(
        "offline_scan_batches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("uploaded_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("client_batch_id", sa.String(length=80), nullable=False),
        sa.Column("device_label", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("accepted_count", sa.Integer(), nullable=False),
        sa.Column("conflict_count", sa.Integer(), nullable=False),
        sa.Column("invalid_count", sa.Integer(), nullable=False),
        sa.Column("payload_meta", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "event_id", "client_batch_id", name="uq_offline_scan_batches_event_client"
        ),
    )
    op.create_index("ix_offline_scan_batches_event_id", "offline_scan_batches", ["event_id"])

    op.create_table(
        "offline_scan_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("client_scan_id", sa.String(length=80), nullable=False),
        sa.Column("ticket_id", sa.Uuid(), nullable=True),
        sa.Column("public_code", sa.String(length=40), nullable=True),
        sa.Column("scanned_at_client", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sync_status", sa.String(length=32), nullable=False),
        sa.Column("conflict_reason", sa.Text(), nullable=True),
        sa.Column("check_in_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["batch_id"], ["offline_scan_batches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "batch_id", "client_scan_id", name="uq_offline_scan_items_batch_client"
        ),
    )
    op.create_index("ix_offline_scan_items_batch_id", "offline_scan_items", ["batch_id"])
    op.create_index("ix_offline_scan_items_sync_status", "offline_scan_items", ["sync_status"])


def downgrade() -> None:
    op.drop_table("offline_scan_items")
    op.drop_table("offline_scan_batches")
    op.drop_table("table_reservations")
    op.drop_table("ticket_group_members")
    op.drop_table("ticket_groups")
    op.drop_table("ticket_transfers")
    op.drop_column("ticket_qr_tokens", "updated_at")
    op.drop_column("ticket_qr_tokens", "is_rotating")
    op.drop_column("ticket_qr_tokens", "rotation_version")
    op.drop_column("tickets", "attendee_index")
    op.drop_column("tickets", "table_label")
    op.drop_column("tickets", "seat_label")
    op.drop_column("tickets", "device_bound_at")
    op.drop_column("tickets", "device_binding_hash")
    op.drop_column("tickets", "qr_mode")
    op.drop_column("ticket_types", "seats_per_unit")
