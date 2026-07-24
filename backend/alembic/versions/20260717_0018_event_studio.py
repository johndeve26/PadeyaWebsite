"""event studio fields and related tables

Revision ID: 20260717_0018
Revises: 20260716_0017
Create Date: 2026-07-17

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260717_0018"
down_revision: Union[str, Sequence[str], None] = "20260716_0017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    op.add_column("events", sa.Column("short_tagline", sa.String(length=240), nullable=True))
    op.add_column("events", sa.Column("vibe", sa.String(length=120), nullable=True))
    op.add_column(
        "events",
        sa.Column("event_type", sa.String(length=32), server_default="public", nullable=False),
    )
    op.add_column(
        "events",
        sa.Column("visibility", sa.String(length=32), server_default="listed", nullable=False),
    )
    op.add_column("events", sa.Column("doors_open_datetime", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "events",
        sa.Column("timezone", sa.String(length=64), server_default="Africa/Lagos", nullable=False),
    )
    op.add_column("events", sa.Column("public_location_label", sa.String(length=255), nullable=True))
    op.add_column(
        "events",
        sa.Column(
            "location_visibility",
            sa.String(length=48),
            server_default="full_public",
            nullable=False,
        ),
    )
    op.add_column(
        "events",
        sa.Column(
            "reveal_timing",
            sa.String(length=48),
            server_default="immediately",
            nullable=False,
        ),
    )
    op.add_column("events", sa.Column("reveal_note", sa.Text(), nullable=True))
    op.add_column("events", sa.Column("online_event_url", sa.String(length=500), nullable=True))
    op.add_column(
        "events",
        sa.Column(
            "online_url_reveal_rule",
            sa.String(length=48),
            server_default="after_payment",
            nullable=False,
        ),
    )
    op.add_column("events", sa.Column("mobile_banner_url", sa.String(length=500), nullable=True))
    op.add_column("events", sa.Column("teaser_video_url", sa.String(length=500), nullable=True))
    op.add_column("events", sa.Column("social_share_image_url", sa.String(length=500), nullable=True))
    op.add_column("events", sa.Column("brand_accent_override", sa.String(length=32), nullable=True))
    op.add_column("events", sa.Column("sponsor_logo_urls", JSON_TYPE, nullable=True))
    op.add_column("events", sa.Column("refund_policy_type", sa.String(length=64), nullable=True))
    op.add_column("events", sa.Column("refund_policy_text", sa.Text(), nullable=True))
    op.add_column("events", sa.Column("cancellation_policy", sa.Text(), nullable=True))
    op.add_column(
        "events",
        sa.Column("id_required", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column("events", sa.Column("safety_notice", sa.Text(), nullable=True))
    op.add_column("events", sa.Column("terms_acknowledgement", sa.Text(), nullable=True))
    op.add_column(
        "events",
        sa.Column("door_sales_allowed", sa.Boolean(), server_default=sa.text("true"), nullable=False),
    )
    op.add_column(
        "events",
        sa.Column("re_entry_allowed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column("events", sa.Column("check_in_start_time", sa.DateTime(timezone=True), nullable=True))
    op.add_column("events", sa.Column("check_in_end_time", sa.DateTime(timezone=True), nullable=True))
    op.add_column("events", sa.Column("dress_code", sa.String(length=255), nullable=True))
    op.add_column("events", sa.Column("accessibility_notes", sa.Text(), nullable=True))
    op.add_column("events", sa.Column("parking_info", sa.Text(), nullable=True))
    op.add_column("events", sa.Column("what_to_expect", sa.Text(), nullable=True))
    op.add_column("events", sa.Column("what_to_bring", sa.Text(), nullable=True))
    op.add_column("events", sa.Column("prohibited_items", sa.Text(), nullable=True))
    op.add_column("events", sa.Column("entry_requirements", sa.Text(), nullable=True))
    op.add_column("events", sa.Column("social_share_title", sa.String(length=200), nullable=True))
    op.add_column("events", sa.Column("social_share_description", sa.String(length=320), nullable=True))
    op.add_column("events", sa.Column("hashtags", JSON_TYPE, nullable=True))
    op.add_column("events", sa.Column("discoverable_keywords", JSON_TYPE, nullable=True))

    op.add_column(
        "ticket_types",
        sa.Column("transfer_allowed", sa.Boolean(), server_default=sa.text("true"), nullable=False),
    )
    op.add_column(
        "ticket_types",
        sa.Column("refund_allowed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column("ticket_types", sa.Column("access_code", sa.String(length=64), nullable=True))
    op.add_column(
        "ticket_types",
        sa.Column("waitlist_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column("ticket_types", sa.Column("table_perks", sa.Text(), nullable=True))
    op.add_column("ticket_types", sa.Column("reservation_hold_minutes", sa.Integer(), nullable=True))

    op.create_table(
        "event_agenda_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_event_agenda_items_event_id", "event_agenda_items", ["event_id"])

    op.create_table(
        "event_people",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("role", sa.String(length=120), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("image_url", sa.String(length=500), nullable=True),
        sa.Column("social_url", sa.String(length=500), nullable=True),
        sa.Column("performance_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_event_people_event_id", "event_people", ["event_id"])

    op.create_table(
        "event_checkout_questions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.Column("options", JSON_TYPE, nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_event_checkout_questions_event_id", "event_checkout_questions", ["event_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_event_checkout_questions_event_id", table_name="event_checkout_questions")
    op.drop_table("event_checkout_questions")
    op.drop_index("ix_event_people_event_id", table_name="event_people")
    op.drop_table("event_people")
    op.drop_index("ix_event_agenda_items_event_id", table_name="event_agenda_items")
    op.drop_table("event_agenda_items")

    for col in (
        "reservation_hold_minutes",
        "table_perks",
        "waitlist_enabled",
        "access_code",
        "refund_allowed",
        "transfer_allowed",
    ):
        op.drop_column("ticket_types", col)

    for col in (
        "discoverable_keywords",
        "hashtags",
        "social_share_description",
        "social_share_title",
        "entry_requirements",
        "prohibited_items",
        "what_to_bring",
        "what_to_expect",
        "parking_info",
        "accessibility_notes",
        "dress_code",
        "check_in_end_time",
        "check_in_start_time",
        "re_entry_allowed",
        "door_sales_allowed",
        "terms_acknowledgement",
        "safety_notice",
        "id_required",
        "cancellation_policy",
        "refund_policy_text",
        "refund_policy_type",
        "sponsor_logo_urls",
        "brand_accent_override",
        "social_share_image_url",
        "teaser_video_url",
        "mobile_banner_url",
        "online_url_reveal_rule",
        "online_event_url",
        "reveal_note",
        "reveal_timing",
        "location_visibility",
        "public_location_label",
        "timezone",
        "doors_open_datetime",
        "visibility",
        "event_type",
        "vibe",
        "short_tagline",
    ):
        op.drop_column("events", col)
