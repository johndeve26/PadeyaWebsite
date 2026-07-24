"""Check-in and scanner schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StartSessionRequest(BaseModel):
    event_id: UUID
    device_label: str | None = Field(default=None, max_length=120)


class ScannerSessionPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: UUID
    user_id: UUID
    status: str
    device_label: str | None
    started_at: datetime
    ended_at: datetime | None
    scanner_name: str | None = None


class ValidateQrRequest(BaseModel):
    event_id: UUID
    qr_payload: str = Field(min_length=10)
    session_id: UUID | None = None


class CheckInRequest(BaseModel):
    event_id: UUID
    qr_payload: str | None = None
    public_code: str | None = None
    session_id: UUID | None = None


class ManualOverrideRequest(BaseModel):
    event_id: UUID
    ticket_id: UUID
    reason: str = Field(min_length=3, max_length=2000)
    session_id: UUID | None = None


class StaffAssignRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)


class StaffAssignmentPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: UUID
    user_id: UUID
    role_label: str
    created_at: datetime
    user_email: str | None = None
    user_name: str | None = None


class TicketScanInfo(BaseModel):
    ticket_id: UUID | None = None
    public_code: str | None = None
    status: str | None = None
    holder_name: str | None = None
    # Always null for desk scanners (kept for schema BC).
    holder_email: str | None = None
    ticket_type_name: str | None = None
    checked_in_at: datetime | None = None


class DeskAttendeePublic(BaseModel):
    """Minimal attendee search result for scanner staff."""

    id: UUID
    public_code: str
    ticket_type_name: str
    status: str
    holder_name: str
    checked_in_at: datetime | None = None


class ScanResultResponse(BaseModel):
    outcome: str
    message: str
    ticket: TicketScanInfo | None = None
    check_in_id: UUID | None = None
    checked_in_at: datetime | None = None
    scanner_name: str | None = None


class CheckInPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: UUID
    ticket_id: UUID | None
    ticket_public_code: str | None
    scanned_by_user_id: UUID
    outcome: str
    method: str
    detail: str | None
    override_reason: str | None
    holder_name: str | None
    ticket_type_name: str | None
    created_at: datetime
    scanner_name: str | None = None


class CheckInStats(BaseModel):
    event_id: UUID
    total_tickets: int
    checked_in: int
    remaining: int
    successful_scans: int
    duplicate_scans: int
    invalid_scans: int
    override_scans: int


class OfflineScanEntry(BaseModel):
    client_scan_id: str = Field(min_length=1, max_length=80)
    qr_payload: str | None = None
    public_code: str | None = None
    scanned_at: datetime | None = None


class OfflineSyncRequest(BaseModel):
    event_id: UUID
    client_batch_id: str = Field(min_length=1, max_length=80)
    device_label: str | None = Field(default=None, max_length=120)
    scans: list[OfflineScanEntry] = Field(min_length=1, max_length=500)


class OfflineScanResultItem(BaseModel):
    client_scan_id: str
    sync_status: str
    conflict_reason: str | None = None
    ticket: TicketScanInfo | None = None
    check_in_id: UUID | None = None


class OfflineSyncResponse(BaseModel):
    batch_id: UUID
    client_batch_id: str
    status: str
    accepted_count: int
    conflict_count: int
    invalid_count: int
    results: list[OfflineScanResultItem]
