"""Ticket response schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TicketLinkedMerchPublic(BaseModel):
    id: UUID
    order_item_id: UUID
    product_name: str
    variant_label: str
    quantity: int
    status: str
    display_status: str | None = None
    pickup_code: str
    pickup_instructions: str | None = None


class TicketPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    public_code: str
    event_id: UUID
    order_id: UUID
    ticket_type_id: UUID
    ticket_type_name: str
    status: str
    holder_name: str
    holder_email: str
    holder_phone: str | None = None
    is_gift: bool = False
    checked_in_at: datetime | None = None
    created_at: datetime
    event_title: str | None = None
    event_slug: str | None = None
    event_cover_url: str | None = None
    event_starts_at: datetime | None = None
    event_ends_at: datetime | None = None
    event_status: str | None = None
    host_id: UUID | None = None
    host_name: str | None = None
    host_username: str | None = None
    location_label: str | None = None
    qr_payload: str | None = None
    qr_mode: str = "static"
    device_bound: bool = False
    seat_label: str | None = None
    table_label: str | None = None
    attendee_index: int | None = None
    qr_expires_at: datetime | None = None
    qr_rotation_version: int | None = None
    linked_merch: list[TicketLinkedMerchPublic] = []


class TicketTransferRequest(BaseModel):
    # Plain str so local demo emails (@*.test) can transfer; service still resolves by email.
    to_email: str = Field(min_length=3, max_length=320)
    to_name: str = Field(min_length=1, max_length=200)
    note: str | None = Field(default=None, max_length=500)


class TicketTransferClaimRequest(BaseModel):
    token: str = Field(min_length=10, max_length=200)


class TicketTransferClaimContextPublic(BaseModel):
    recipient_email: str
    recipient_name: str | None = None
    event_title: str | None = None
    status: str


class TicketTransferPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ticket_id: UUID
    event_id: UUID
    from_user_id: UUID
    to_user_id: UUID | None = None
    from_email: str
    to_email: str
    recipient_name: str | None = None
    note: str | None = None
    status: str
    created_at: datetime
    claim_path: str | None = None


class TicketTransferActivityPublic(TicketTransferPublic):
    """Buyer transfer inbox — sent/received with actions."""

    event_title: str | None = None
    ticket_public_code: str | None = None
    role: Literal["sent", "received"]
    can_revoke: bool = False
    can_decline: bool = False
    can_resend_invite: bool = False


class TicketCancelRequest(BaseModel):
    """Buyer/admin cancel requires password — irreversible; prevents accidental cancel."""

    password: str = Field(min_length=1, max_length=128)
    reason: str | None = Field(default=None, max_length=500)


class TicketQrModeRequest(BaseModel):
    qr_mode: str


class TicketDeviceBindRequest(BaseModel):
    device_fingerprint: str = Field(min_length=4, max_length=200)


class TableReservationCreate(BaseModel):
    table_label: str = Field(min_length=1, max_length=80)
    capacity: int = Field(default=1, ge=1, le=100)
    seat_label: str | None = Field(default=None, max_length=80)
    assignment_note: str | None = None


class TableReservationAssign(BaseModel):
    ticket_id: UUID | None = None
    seat_label: str | None = Field(default=None, max_length=80)


class TableReservationPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: UUID
    ticket_type_id: UUID | None = None
    group_id: UUID | None = None
    primary_ticket_id: UUID | None = None
    table_label: str
    seat_label: str | None = None
    capacity: int
    status: str
    assignment_note: str | None = None
    created_at: datetime
    updated_at: datetime


class TicketGroupPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: UUID
    order_id: UUID
    ticket_type_id: UUID
    group_kind: str
    expected_size: int
    label: str | None = None
    status: str
    created_at: datetime
    ticket_ids: list[UUID] = []
