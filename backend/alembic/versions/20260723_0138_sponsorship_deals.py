"""Sponsorship deals, invoices, and payment events

Revision ID: 20260723_0138
Revises: 20260723_0137
Create Date: 2026-07-23

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260723_0138"
down_revision: Union[str, Sequence[str], None] = "20260723_0137"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sponsorship_deals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sponsor_id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=True),
        sa.Column("campaign_id", sa.Uuid(), nullable=True),
        sa.Column("inquiry_id", sa.Uuid(), nullable=True),
        sa.Column("slot_id", sa.Uuid(), nullable=True),
        sa.Column("placement_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("package_type", sa.String(length=64), nullable=False),
        sa.Column("deliverables", sa.JSON(), nullable=True),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=8), server_default="NGN", nullable=False),
        sa.Column("platform_fee_snapshot", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="draft", nullable=False),
        sa.Column("proposed_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("accepted_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["sponsor_id"], ["sponsors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["campaign_id"], ["sponsor_campaigns.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["inquiry_id"], ["sponsorship_inquiries.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["slot_id"], ["sponsorship_slots.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["placement_id"], ["sponsorship_placements.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["proposed_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["accepted_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sponsorship_deals_sponsor_id", "sponsorship_deals", ["sponsor_id"])
    op.create_index("ix_sponsorship_deals_host_id", "sponsorship_deals", ["host_id"])
    op.create_index("ix_sponsorship_deals_status", "sponsorship_deals", ["status"])

    op.create_table(
        "sponsorship_invoices",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("deal_id", sa.Uuid(), nullable=False),
        sa.Column("sponsor_id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=False),
        sa.Column("invoice_number", sa.String(length=40), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=8), server_default="NGN", nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="draft", nullable=False),
        sa.Column("paystack_reference", sa.String(length=120), nullable=True),
        sa.Column("payment_url", sa.String(length=500), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["deal_id"], ["sponsorship_deals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sponsor_id"], ["sponsors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invoice_number", name="uq_sponsorship_invoices_number"),
        sa.UniqueConstraint("paystack_reference", name="uq_sponsorship_invoices_paystack_ref"),
    )
    op.create_index("ix_sponsorship_invoices_deal_id", "sponsorship_invoices", ["deal_id"])

    op.create_table(
        "sponsorship_payment_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("invoice_id", sa.Uuid(), nullable=False),
        sa.Column("deal_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("provider_reference", sa.String(length=120), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("raw_payload_redacted", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["invoice_id"], ["sponsorship_invoices.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["deal_id"], ["sponsorship_deals.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider",
            "provider_reference",
            "event_type",
            name="uq_sponsorship_payment_events_provider_ref_type",
        ),
    )


def downgrade() -> None:
    op.drop_table("sponsorship_payment_events")
    op.drop_table("sponsorship_invoices")
    op.drop_table("sponsorship_deals")
