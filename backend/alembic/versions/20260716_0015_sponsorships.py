"""sponsorship marketplace

Revision ID: 20260716_0015
Revises: 20260716_0014
Create Date: 2026-07-16

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260716_0015"
down_revision: Union[str, Sequence[str], None] = "20260716_0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sponsors",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("company_name", sa.String(length=200), nullable=False),
        sa.Column("contact_name", sa.String(length=160), nullable=False),
        sa.Column("contact_email", sa.String(length=320), nullable=False),
        sa.Column("website", sa.String(length=255), nullable=True),
        sa.Column("logo_url", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sponsors_user_id", "sponsors", ["user_id"])
    op.create_index("ix_sponsors_contact_email", "sponsors", ["contact_email"])
    op.create_index("ix_sponsors_status", "sponsors", ["status"])

    op.create_table(
        "host_sponsorship_settings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=False),
        sa.Column("accepting_sponsors", sa.Boolean(), nullable=False),
        sa.Column("contact_email", sa.String(length=320), nullable=True),
        sa.Column("pitch", sa.Text(), nullable=True),
        sa.Column("audience_notes", sa.Text(), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("host_id", name="uq_host_sponsorship_settings_host_id"),
    )
    op.create_index(
        "ix_host_sponsorship_settings_host_id",
        "host_sponsorship_settings",
        ["host_id"],
    )

    op.create_table(
        "sponsorship_slots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("host_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=True),
        sa.Column("slot_type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("moderation_status", sa.String(length=32), nullable=False),
        sa.Column("moderation_note", sa.Text(), nullable=True),
        sa.Column("moderated_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("moderated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["moderated_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sponsorship_slots_host_id", "sponsorship_slots", ["host_id"])
    op.create_index("ix_sponsorship_slots_event_id", "sponsorship_slots", ["event_id"])
    op.create_index("ix_sponsorship_slots_slot_type", "sponsorship_slots", ["slot_type"])
    op.create_index("ix_sponsorship_slots_status", "sponsorship_slots", ["status"])
    op.create_index(
        "ix_sponsorship_slots_moderation_status",
        "sponsorship_slots",
        ["moderation_status"],
    )
    op.create_index(
        "ix_sponsorship_slots_created_at", "sponsorship_slots", ["created_at"]
    )

    op.create_table(
        "sponsorship_inquiries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slot_id", sa.Uuid(), nullable=False),
        sa.Column("sponsor_id", sa.Uuid(), nullable=True),
        sa.Column("company_name", sa.String(length=200), nullable=False),
        sa.Column("contact_name", sa.String(length=160), nullable=False),
        sa.Column("contact_email", sa.String(length=320), nullable=False),
        sa.Column("website", sa.String(length=255), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("proposed_budget", sa.Numeric(12, 2), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("host_note", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["slot_id"], ["sponsorship_slots.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["sponsor_id"], ["sponsors.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_sponsorship_inquiries_slot_id", "sponsorship_inquiries", ["slot_id"]
    )
    op.create_index(
        "ix_sponsorship_inquiries_sponsor_id", "sponsorship_inquiries", ["sponsor_id"]
    )
    op.create_index(
        "ix_sponsorship_inquiries_contact_email",
        "sponsorship_inquiries",
        ["contact_email"],
    )
    op.create_index(
        "ix_sponsorship_inquiries_status", "sponsorship_inquiries", ["status"]
    )
    op.create_index(
        "ix_sponsorship_inquiries_created_at",
        "sponsorship_inquiries",
        ["created_at"],
    )

    op.create_table(
        "sponsorship_placements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slot_id", sa.Uuid(), nullable=False),
        sa.Column("sponsor_id", sa.Uuid(), nullable=False),
        sa.Column("inquiry_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("asset_url", sa.String(length=500), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["slot_id"], ["sponsorship_slots.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["sponsor_id"], ["sponsors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["inquiry_id"], ["sponsorship_inquiries.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_sponsorship_placements_slot_id", "sponsorship_placements", ["slot_id"]
    )
    op.create_index(
        "ix_sponsorship_placements_sponsor_id",
        "sponsorship_placements",
        ["sponsor_id"],
    )
    op.create_index(
        "ix_sponsorship_placements_status", "sponsorship_placements", ["status"]
    )

    op.create_table(
        "sponsorship_analytics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("placement_id", sa.Uuid(), nullable=False),
        sa.Column("impressions", sa.Integer(), nullable=False),
        sa.Column("clicks", sa.Integer(), nullable=False),
        sa.Column("inquiries_attributed", sa.Integer(), nullable=False),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["placement_id"], ["sponsorship_placements.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "placement_id", name="uq_sponsorship_analytics_placement_id"
        ),
    )
    op.create_index(
        "ix_sponsorship_analytics_placement_id",
        "sponsorship_analytics",
        ["placement_id"],
    )


def downgrade() -> None:
    op.drop_table("sponsorship_analytics")
    op.drop_table("sponsorship_placements")
    op.drop_table("sponsorship_inquiries")
    op.drop_table("sponsorship_slots")
    op.drop_table("host_sponsorship_settings")
    op.drop_table("sponsors")
