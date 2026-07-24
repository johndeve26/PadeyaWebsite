"""Issued ticket and QR token models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.database import Base

# Re-export advanced models so metadata / imports stay cohesive.
from app.tickets.advanced_models import (  # noqa: E402,F401
    OfflineScanBatch,
    OfflineScanItem,
    TableReservation,
    TicketGroup,
    TicketGroupMember,
    TicketTransfer,
)

if TYPE_CHECKING:
    from app.payments.models import Order


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (UniqueConstraint("public_code", name="uq_tickets_public_code"),)

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    public_code: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("order_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ticket_type_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("ticket_types.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    buyer_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False, index=True)
    ticket_type_name: Mapped[str] = mapped_column(String(160), nullable=False)
    holder_name: Mapped[str] = mapped_column(String(200), nullable=False)
    holder_email: Mapped[str] = mapped_column(String(320), nullable=False)
    holder_phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    is_gift: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Never set from email alone — only explicit verified linking rules
    recipient_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    claimed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    checked_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Phase 17 — advanced ticketing (nullable / defaults keep legacy tickets working)
    qr_mode: Mapped[str] = mapped_column(String(32), default="static", nullable=False)
    device_binding_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    device_bound_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    seat_label: Mapped[str | None] = mapped_column(String(80), nullable=True)
    table_label: Mapped[str | None] = mapped_column(String(80), nullable=True)
    attendee_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    order: Mapped[Order] = relationship(back_populates="tickets")
    qr_token: Mapped[TicketQrToken | None] = relationship(
        back_populates="ticket",
        uselist=False,
        cascade="all, delete-orphan",
    )


class TicketQrToken(Base):
    __tablename__ = "ticket_qr_tokens"
    __table_args__ = (UniqueConstraint("ticket_id", name="uq_ticket_qr_tokens_ticket_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    jti_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    signed_payload: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rotation_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_rotating: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    ticket: Mapped[Ticket] = relationship(back_populates="qr_token")
