"""Promo codes, redemptions, ambassadors, clicks, and sales attribution.

Phase 9 domain tables (profiles, participants, conversions, …) live in
`ambassador_domain.py` and are re-exported below for Alembic registration.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.core.database import Base
from app.promos.referral_clicks import ReferralClick  # noqa: F401
from app.promos.referral_programs import (  # noqa: F401
    ReferralProgram,
    ReferralProgramExclusion,
    ReferralProgramRule,
)
from app.promos.referral_ledger import (  # noqa: F401
    ReferralAttribution,
    ReferralCommissionEntry,
)
from app.promos.ambassador_domain import (  # noqa: F401
    AmbassadorAttribution,
    AmbassadorAuditLog,
    AmbassadorClick,
    AmbassadorConversion,
    AmbassadorFraudFlag,
    AmbassadorParticipant,
    AmbassadorPayout,
    AmbassadorProfile,
)


class PromoCode(Base):
    __tablename__ = "promo_codes"
    __table_args__ = (UniqueConstraint("host_id", "code", name="uq_promo_codes_host_code"),)

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    host_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("hosts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    discount_type: Mapped[str] = mapped_column(String(32), nullable=False)
    discount_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    usage_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    event_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    ticket_type_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("ticket_types.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False, index=True)
    max_per_user: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class PromoRedemption(Base):
    __tablename__ = "promo_redemptions"
    __table_args__ = (UniqueConstraint("order_id", name="uq_promo_redemptions_order_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    promo_code_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("promo_codes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    redeemed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AmbassadorPlatformSettings(Base):
    """Singleton row (id=1): global Ambassadors feature switch."""

    __tablename__ = "ambassador_platform_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class AmbassadorCampaign(Base):
    """Ambassadors campaign (v1 event-scoped + phase-9 domain columns).

    Legacy v1 still uses `host_id` + required-ish event rows with statuses
    `public_open|paused|ended` and types `event_tickets|event_merch`.
    Phase 9 adds `host_profile_id`, nullable scopes, `visibility`, and
    `cookie_window_days` toward types `event|merch|host|platform` and
    statuses `draft|active|paused|ended|archived`.
    """

    __tablename__ = "ambassador_campaigns"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Legacy host account FK (v1). Prefer host_profile_id for new writes.
    host_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("hosts.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    host_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("host_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    merch_product_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("event_merch_products.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # v1: public_open | paused | ended
    # domain: draft | active | paused | ended | archived
    status: Mapped[str] = mapped_column(
        String(32), default="public_open", nullable=False, index=True
    )
    # public_open | invite_only | private
    visibility: Mapped[str] = mapped_column(
        String(32), default="public_open", nullable=False, index=True
    )
    # host | platform — platform = admin-created (v1)
    source: Mapped[str] = mapped_column(
        String(32), default="host", nullable=False, index=True
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    # v1: event_tickets | event_merch
    # domain: event | merch | host | platform
    campaign_type: Mapped[str] = mapped_column(
        String(32), default="event_tickets", nullable=False, index=True
    )
    commission_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("5.00"), nullable=False
    )
    # percentage | flat | reward_only
    commission_type: Mapped[str] = mapped_column(
        String(32), default="percentage", nullable=False
    )
    # Percent (0–100) or flat NGN amount depending on commission_type
    commission_value: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("5.00"), nullable=False
    )
    # tickets | merch | tickets_and_merch
    applies_to: Mapped[str] = mapped_column(
        String(32), default="tickets", nullable=False
    )
    hold_period_days: Mapped[int] = mapped_column(Integer, default=7, nullable=False)
    cookie_window_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    payout_minimum: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    max_commission_per_order: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    free_ticket_after_sales: Mapped[int | None] = mapped_column(Integer, nullable=True)
    leaderboard_reward_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    leaderboard_reward_description: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    # When False (default), campaign host owner cannot earn commission as ambassador.
    allow_host_owner_commission: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    # Derived from campaign_type for display/legacy: merch campaigns → True
    merch_included: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    starts_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Parent ReferralProgram (event-scoped backfill or platform-wide umbrella)
    program_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("referral_programs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
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


class Ambassador(Base):
    __tablename__ = "ambassadors"
    __table_args__ = (
        Index(
            "uq_ambassadors_host_referral_curated",
            "host_id",
            "referral_code",
            unique=True,
            sqlite_where=text("event_id IS NULL"),
            postgresql_where=text("event_id IS NULL"),
        ),
        Index(
            "uq_ambassadors_campaign_referral",
            "campaign_id",
            "referral_code",
            unique=True,
            sqlite_where=text("campaign_id IS NOT NULL"),
            postgresql_where=text("campaign_id IS NOT NULL"),
        ),
        Index(
            "uq_ambassadors_event_referral_legacy",
            "event_id",
            "referral_code",
            unique=True,
            sqlite_where=text("event_id IS NOT NULL AND campaign_id IS NULL"),
            postgresql_where=text("event_id IS NOT NULL AND campaign_id IS NULL"),
        ),
        Index(
            "uq_ambassadors_campaign_user",
            "campaign_id",
            "user_id",
            unique=True,
            sqlite_where=text("campaign_id IS NOT NULL AND user_id IS NOT NULL"),
            postgresql_where=text("campaign_id IS NOT NULL AND user_id IS NOT NULL"),
        ),
        Index(
            "uq_ambassadors_event_user_legacy",
            "event_id",
            "user_id",
            unique=True,
            sqlite_where=text(
                "event_id IS NOT NULL AND user_id IS NOT NULL AND campaign_id IS NULL"
            ),
            postgresql_where=text(
                "event_id IS NOT NULL AND user_id IS NOT NULL AND campaign_id IS NULL"
            ),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Nullable for platform-wide enrollments (Pàdéyá-funded).
    host_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("hosts.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    event_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("ambassador_campaigns.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    program_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("referral_programs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # host_curated | open_event | platform_wide
    program_kind: Mapped[str] = mapped_column(
        String(32), default="host_curated", nullable=False, index=True
    )
    referral_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False, index=True)
    commission_rate_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("0"), nullable=False
    )
    terms_accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    terms_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    free_ticket_earned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
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


class PromoClick(Base):
    """Referral link click tracking (ambassador attribution funnel)."""

    __tablename__ = "promo_clicks"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    ambassador_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("ambassadors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("events.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    landing_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    # Legacy raw UA — no longer written (phase 14). Prefer user_agent_hash.
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    user_agent_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class AmbassadorSale(Base):
    __tablename__ = "ambassador_sales"
    __table_args__ = (
        Index(
            "uq_ambassador_sales_order_slice_amb",
            "order_id",
            "product_slice",
            "ambassador_id",
            unique=True,
        ),
        Index(
            "uq_ambassador_sales_idempotency",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
            sqlite_where=text("idempotency_key IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    ambassador_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("ambassadors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # host | platform — platform commissions must not reduce host settlement
    payer_type: Mapped[str] = mapped_column(
        String(32), default="host", nullable=False, index=True
    )
    # tickets | merch | all (legacy single-row sales)
    product_slice: Mapped[str] = mapped_column(
        String(32), default="all", nullable=False
    )
    program_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("referral_programs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    idempotency_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    tickets_sold: Mapped[int] = mapped_column(Integer, nullable=False)
    merch_units_sold: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    revenue_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    commission_owed: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), nullable=False
    )
    commission_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    hold_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    # attributed → estimated; approved → payable; paid; reversed (fraud/refund)
    status: Mapped[str] = mapped_column(String(32), default="attributed", nullable=False)
    reversed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reversed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reversal_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reward_status_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reward_status_updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    rejection_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    payout_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    payout_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
