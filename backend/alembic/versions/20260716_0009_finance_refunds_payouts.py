"""finance refunds balances ledger payouts

Revision ID: 20260716_0009
Revises: 20260716_0008
Create Date: 2026-07-16

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260716_0009"
down_revision: Union[str, Sequence[str], None] = "20260716_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "host_balances",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("available_balance", sa.Numeric(14, 2), nullable=False),
        sa.Column("pending_payout_balance", sa.Numeric(14, 2), nullable=False),
        sa.Column("lifetime_earned", sa.Numeric(14, 2), nullable=False),
        sa.Column("lifetime_refunded", sa.Numeric(14, 2), nullable=False),
        sa.Column("lifetime_paid_out", sa.Numeric(14, 2), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("host_id", name="uq_host_balances_host_id"),
    )
    op.create_index("ix_host_balances_host_id", "host_balances", ["host_id"])

    op.create_table(
        "ledger_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=False),
        sa.Column("entry_type", sa.String(length=64), nullable=False),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("available_balance_after", sa.Numeric(14, 2), nullable=False),
        sa.Column("pending_payout_balance_after", sa.Numeric(14, 2), nullable=False),
        sa.Column("reference_type", sa.String(length=64), nullable=True),
        sa.Column("reference_id", sa.String(length=64), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ledger_entries_host_id", "ledger_entries", ["host_id"])
    op.create_index("ix_ledger_entries_entry_type", "ledger_entries", ["entry_type"])
    op.create_index("ix_ledger_entries_reference_type", "ledger_entries", ["reference_type"])
    op.create_index("ix_ledger_entries_reference_id", "ledger_entries", ["reference_id"])
    op.create_index("ix_ledger_entries_created_at", "ledger_entries", ["created_at"])

    op.create_table(
        "refund_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("payment_id", sa.Uuid(), nullable=True),
        sa.Column("buyer_user_id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("refund_type", sa.String(length=32), nullable=False),
        sa.Column("requested_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("policy_snapshot", sa.String(length=64), nullable=False),
        sa.Column("ticket_ids", sa.JSON(), nullable=True),
        sa.Column("escalation_note", sa.Text(), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("reviewed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_refund_requests_order_id", "refund_requests", ["order_id"])
    op.create_index("ix_refund_requests_payment_id", "refund_requests", ["payment_id"])
    op.create_index("ix_refund_requests_buyer_user_id", "refund_requests", ["buyer_user_id"])
    op.create_index("ix_refund_requests_host_id", "refund_requests", ["host_id"])
    op.create_index("ix_refund_requests_event_id", "refund_requests", ["event_id"])
    op.create_index("ix_refund_requests_status", "refund_requests", ["status"])
    op.create_index("ix_refund_requests_created_at", "refund_requests", ["created_at"])

    op.create_table(
        "refunds",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("refund_request_id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("processed_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("ledger_entry_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ledger_entry_id"], ["ledger_entries.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["processed_by_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["refund_request_id"], ["refund_requests.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("refund_request_id"),
    )
    op.create_index("ix_refunds_refund_request_id", "refunds", ["refund_request_id"])
    op.create_index("ix_refunds_order_id", "refunds", ["order_id"])
    op.create_index("ix_refunds_host_id", "refunds", ["host_id"])
    op.create_index("ix_refunds_created_at", "refunds", ["created_at"])

    op.create_table(
        "payout_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("recipient_bank_snapshot", sa.JSON(), nullable=False),
        sa.Column("host_note", sa.Text(), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("requested_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("reviewed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["requested_by_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_payout_requests_host_id", "payout_requests", ["host_id"])
    op.create_index("ix_payout_requests_status", "payout_requests", ["status"])
    op.create_index("ix_payout_requests_created_at", "payout_requests", ["created_at"])

    op.create_table(
        "payout_evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("payout_request_id", sa.Uuid(), nullable=False),
        sa.Column("bank_transfer_reference", sa.String(length=128), nullable=False),
        sa.Column("evidence_file_url", sa.String(length=500), nullable=False),
        sa.Column("admin_note", sa.Text(), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("paid_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("recipient_bank_snapshot", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["paid_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["payout_request_id"], ["payout_requests.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("payout_request_id", name="uq_payout_evidence_request"),
    )
    op.create_index(
        "ix_payout_evidence_payout_request_id", "payout_evidence", ["payout_request_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_payout_evidence_payout_request_id", table_name="payout_evidence")
    op.drop_table("payout_evidence")
    op.drop_index("ix_payout_requests_created_at", table_name="payout_requests")
    op.drop_index("ix_payout_requests_status", table_name="payout_requests")
    op.drop_index("ix_payout_requests_host_id", table_name="payout_requests")
    op.drop_table("payout_requests")
    op.drop_index("ix_refunds_created_at", table_name="refunds")
    op.drop_index("ix_refunds_host_id", table_name="refunds")
    op.drop_index("ix_refunds_order_id", table_name="refunds")
    op.drop_index("ix_refunds_refund_request_id", table_name="refunds")
    op.drop_table("refunds")
    op.drop_index("ix_refund_requests_created_at", table_name="refund_requests")
    op.drop_index("ix_refund_requests_status", table_name="refund_requests")
    op.drop_index("ix_refund_requests_event_id", table_name="refund_requests")
    op.drop_index("ix_refund_requests_host_id", table_name="refund_requests")
    op.drop_index("ix_refund_requests_buyer_user_id", table_name="refund_requests")
    op.drop_index("ix_refund_requests_payment_id", table_name="refund_requests")
    op.drop_index("ix_refund_requests_order_id", table_name="refund_requests")
    op.drop_table("refund_requests")
    op.drop_index("ix_ledger_entries_created_at", table_name="ledger_entries")
    op.drop_index("ix_ledger_entries_reference_id", table_name="ledger_entries")
    op.drop_index("ix_ledger_entries_reference_type", table_name="ledger_entries")
    op.drop_index("ix_ledger_entries_entry_type", table_name="ledger_entries")
    op.drop_index("ix_ledger_entries_host_id", table_name="ledger_entries")
    op.drop_table("ledger_entries")
    op.drop_index("ix_host_balances_host_id", table_name="host_balances")
    op.drop_table("host_balances")
