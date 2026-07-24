"""Event, category, venue, media, agenda, people, and ticket type models.

Event Studio nested resources live here:
- event_agenda_items, event_people, event_checkout_questions
- event_media (gallery + typed media; no separate gallery table)
- event_venues (1:1 nested; flat events.* location fields dual-written)
- event_templates (host JSON blueprints)

Checkout answers are order snapshots in payments.OrderCheckoutAnswer
(order_checkout_answers), not a per-event answers table.

Publish checklist is computed in service.build_publish_checklist — not stored.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON, Uuid

from app.core.database import Base

if TYPE_CHECKING:
    from app.hosts.models import Host
    from app.taxonomy.models import Location


class EventCategory(Base):
    __tablename__ = "event_categories"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(140), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    events: Mapped[list[Event]] = relationship(back_populates="category")


class Event(Base):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    short_tagline: Mapped[str | None] = mapped_column(String(240), nullable=True)
    vibe: Mapped[str | None] = mapped_column(String(120), nullable=True)
    event_type: Mapped[str] = mapped_column(String(32), default="public", nullable=False)
    visibility: Mapped[str] = mapped_column(String(32), default="listed", nullable=False)
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("event_categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    primary_category_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("taxonomy_categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    location_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("locations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    host_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("hosts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    start_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    doors_open_datetime: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    timezone: Mapped[str] = mapped_column(String(64), default="Africa/Lagos", nullable=False)
    venue_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    venue_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    state: Mapped[str | None] = mapped_column(String(120), nullable=True)
    country: Mapped[str | None] = mapped_column(String(120), nullable=True)
    area: Mapped[str | None] = mapped_column(String(120), nullable=True)
    postcode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    latitude: Mapped[str | None] = mapped_column(String(32), nullable=True)
    longitude: Mapped[str | None] = mapped_column(String(32), nullable=True)
    google_place_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    formatted_address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    google_maps_share_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    google_maps_place_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    public_location_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approximate_latitude: Mapped[str | None] = mapped_column(String(32), nullable=True)
    approximate_longitude: Mapped[str | None] = mapped_column(String(32), nullable=True)
    approximate_map_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location_visibility: Mapped[str] = mapped_column(
        String(48), default="full_public", nullable=False
    )
    reveal_timing: Mapped[str] = mapped_column(String(48), default="immediately", nullable=False)
    reveal_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    online_event_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    online_url_reveal_rule: Mapped[str] = mapped_column(
        String(48), default="after_payment", nullable=False
    )
    banner_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    mobile_banner_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    teaser_video_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    social_share_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    brand_accent_override: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sponsor_logo_urls: Mapped[list[Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    refund_policy: Mapped[str | None] = mapped_column(Text, nullable=True)
    refund_policy_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    refund_policy_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancellation_policy: Mapped[str | None] = mapped_column(Text, nullable=True)
    age_restriction: Mapped[str | None] = mapped_column(String(64), nullable=True)
    id_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    safety_notice: Mapped[str | None] = mapped_column(Text, nullable=True)
    terms_acknowledgement: Mapped[str | None] = mapped_column(Text, nullable=True)
    door_sales_allowed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allow_merch_only_checkout: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    open_ambassadors_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    open_ambassador_commission_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("5.00"), nullable=False
    )
    re_entry_allowed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    check_in_start_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    check_in_end_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    dress_code: Mapped[str | None] = mapped_column(String(255), nullable=True)
    accessibility_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    parking_info: Mapped[str | None] = mapped_column(Text, nullable=True)
    what_to_expect: Mapped[str | None] = mapped_column(Text, nullable=True)
    what_to_bring: Mapped[str | None] = mapped_column(Text, nullable=True)
    prohibited_items: Mapped[str | None] = mapped_column(Text, nullable=True)
    entry_requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False, index=True)
    featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    seo_title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    seo_description: Mapped[str | None] = mapped_column(String(320), nullable=True)
    social_share_title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    social_share_description: Mapped[str | None] = mapped_column(String(320), nullable=True)
    hashtags: Mapped[list[Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    discoverable_keywords: Mapped[list[Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Admin ops flag (does not hide listing; soft marker for review).
    admin_flagged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    admin_flag_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    admin_flagged_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    category: Mapped[EventCategory | None] = relationship(back_populates="events")
    host: Mapped[Host] = relationship(back_populates="events")
    location: Mapped[Location | None] = relationship(
        "Location",
        foreign_keys=[location_id],
        lazy="selectin",
    )
    venue: Mapped[EventVenue | None] = relationship(
        back_populates="event",
        uselist=False,
        cascade="all, delete-orphan",
    )
    media: Mapped[list[EventMedia]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
        order_by="EventMedia.sort_order",
    )
    ticket_types: Mapped[list[TicketType]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
    )
    agenda_items: Mapped[list[EventAgendaItem]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
        order_by="EventAgendaItem.sort_order",
    )
    people: Mapped[list[EventPerson]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
        order_by="EventPerson.sort_order",
    )
    checkout_questions: Mapped[list[EventCheckoutQuestion]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
        order_by="EventCheckoutQuestion.sort_order",
    )


class EventVenue(Base):
    __tablename__ = "event_venues"
    __table_args__ = (UniqueConstraint("event_id", name="uq_event_venues_event_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    state: Mapped[str | None] = mapped_column(String(120), nullable=True)
    country: Mapped[str | None] = mapped_column(String(120), nullable=True)
    latitude: Mapped[str | None] = mapped_column(String(32), nullable=True)
    longitude: Mapped[str | None] = mapped_column(String(32), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    event: Mapped[Event] = relationship(back_populates="venue")


class EventMedia(Base):
    __tablename__ = "event_media"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    media_type: Mapped[str] = mapped_column(String(32), default="gallery", nullable=False)
    alt_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    event: Mapped[Event] = relationship(back_populates="media")


class EventAgendaItem(Base):
    __tablename__ = "event_agenda_items"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    type: Mapped[str] = mapped_column(String(32), default="other", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    event: Mapped[Event] = relationship(back_populates="agenda_items")


class EventPerson(Base):
    __tablename__ = "event_people"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str | None] = mapped_column(String(120), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    social_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    performance_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    event: Mapped[Event] = relationship(back_populates="people")


class EventCheckoutQuestion(Base):
    __tablename__ = "event_checkout_questions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(32), default="short_text", nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    options: Mapped[list[Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    help_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default="active", nullable=False, index=True
    )
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    event: Mapped[Event] = relationship(back_populates="checkout_questions")


class TicketType(Base):
    __tablename__ = "ticket_types"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_sold: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quantity_reserved: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Phase 17 — seats/attendees represented by one inventory unit (group/table)
    seats_per_unit: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    min_per_order: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    max_per_order: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    sale_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sale_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    visibility: Mapped[str] = mapped_column(String(32), default="public", nullable=False)
    benefits: Mapped[str | None] = mapped_column(Text, nullable=True)
    transfer_allowed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    refund_allowed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    access_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    waitlist_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    table_perks: Mapped[str | None] = mapped_column(Text, nullable=True)
    reservation_hold_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    event: Mapped[Event] = relationship(back_populates="ticket_types")


class EventTemplate(Base):
    """Reusable host event draft payload (archive, never casually hard-delete)."""

    __tablename__ = "event_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    host_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("hosts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict
    )
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False, index=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
