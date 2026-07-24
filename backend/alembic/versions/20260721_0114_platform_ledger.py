"""Alembic: append-only platform ledger for Pàdéyá finance.

Revision ID: 20260721_0114
Revises: 20260721_0113
Create Date: 2026-07-21

Platform-wide journal for payment volume, fees, refunds, and payouts.
Corrections are new adjustment rows — never mutate prior entries.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260721_0114"
down_revision = "20260721_0113"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "platform_ledger_entries",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("entry_type", sa.String(length=64), nullable=False),
        sa.Column("order_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("ticket_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("host_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("event_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="NGN"),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "metadata_json",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=True,
        ),
        sa.Column("dedupe_key", sa.String(length=220), nullable=False),
        sa.Column("reference_type", sa.String(length=64), nullable=True),
        sa.Column("reference_id", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by", sa.Uuid(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("dedupe_key", name="uq_platform_ledger_dedupe_key"),
    )
    op.create_index(
        "ix_platform_ledger_entries_entry_type",
        "platform_ledger_entries",
        ["entry_type"],
    )
    op.create_index(
        "ix_platform_ledger_entries_order_id",
        "platform_ledger_entries",
        ["order_id"],
    )
    op.create_index(
        "ix_platform_ledger_entries_host_id",
        "platform_ledger_entries",
        ["host_id"],
    )
    op.create_index(
        "ix_platform_ledger_entries_event_id",
        "platform_ledger_entries",
        ["event_id"],
    )
    op.create_index(
        "ix_platform_ledger_entries_created_at",
        "platform_ledger_entries",
        ["created_at"],
    )
    op.create_index(
        "ix_platform_ledger_entries_reference",
        "platform_ledger_entries",
        ["reference_type", "reference_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_platform_ledger_entries_reference", table_name="platform_ledger_entries")
    op.drop_index("ix_platform_ledger_entries_created_at", table_name="platform_ledger_entries")
    op.drop_index("ix_platform_ledger_entries_event_id", table_name="platform_ledger_entries")
    op.drop_index("ix_platform_ledger_entries_host_id", table_name="platform_ledger_entries")
    op.drop_index("ix_platform_ledger_entries_order_id", table_name="platform_ledger_entries")
    op.drop_index("ix_platform_ledger_entries_entry_type", table_name="platform_ledger_entries")
    op.drop_table("platform_ledger_entries")
