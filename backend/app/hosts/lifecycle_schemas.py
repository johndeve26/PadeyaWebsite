"""Schemas for host team, bank accounts, and verification review."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class HostTeamMemberInvite(BaseModel):
    """Create pending host-team invite.

    Canonical body uses ``invite_identifier`` + ``permissions_json`` / ``scope_json`` /
    ``selected_event_ids``. Legacy ``email`` / ``permissions`` / ``scope`` /
    ``scoped_event_ids`` remain accepted.
    """

    invite_identifier: str | None = Field(default=None, min_length=2, max_length=320)
    # Legacy alias for invite_identifier
    email: str | None = Field(default=None, min_length=2, max_length=320)
    role: str = Field(default="scanner", max_length=32)
    role_label: str | None = Field(default=None, min_length=2, max_length=64)
    permissions_json: dict[str, bool] | None = None
    permissions: dict[str, bool] | None = None
    # ``{"type":"host_wide"|"selected_events","event_ids":[...]}`` or legacy scope string
    scope_json: dict[str, Any] | str | None = None
    scope: str | None = Field(default=None, max_length=32)
    selected_event_ids: list[UUID] | None = None
    scoped_event_ids: list[UUID] | None = None

    @model_validator(mode="after")
    def coalesce_invite_fields(self) -> HostTeamMemberInvite:
        from app.hosts.team_invite_resolve import normalize_invitee_input
        from app.hosts.team_permissions import unpack_scope_json

        raw = (self.invite_identifier or self.email or "").strip()
        if not raw:
            raise ValueError("invite_identifier is required")
        normalized = normalize_invitee_input(raw)
        self.invite_identifier = normalized
        self.email = normalized

        if self.permissions_json is None and self.permissions is not None:
            self.permissions_json = self.permissions
        if self.permissions is None and self.permissions_json is not None:
            self.permissions = self.permissions_json

        if self.scope_json is not None:
            scope, ids = unpack_scope_json(self.scope_json, role=self.role)
            self.scope = scope
            if self.selected_event_ids is None and self.scoped_event_ids is None:
                self.selected_event_ids = ids
                self.scoped_event_ids = ids
        else:
            ids = self.selected_event_ids or self.scoped_event_ids
            self.selected_event_ids = ids
            self.scoped_event_ids = ids

        return self

    @field_validator("role")
    @classmethod
    def normalize_role(cls, value: str) -> str:
        return (value or "scanner").strip().lower()


class HostTeamInviteCreateResponse(BaseModel):
    """Safe create-invite response — never returns private email for username invites."""

    invite_id: UUID
    invite_method: str
    status: str
    # Email invites only (masked)
    masked_email: str | None = None
    # Username invites only
    display_name: str | None = None
    username: str | None = None
    avatar_url: str | None = None


class HostTeamInviteLookupResponse(BaseModel):
    """Live invite-field preview — never includes private account email."""

    invite_method: str | None = None
    valid: bool = False
    found: bool = False
    display_name: str | None = None
    username: str | None = None
    avatar_url: str | None = None
    masked_email: str | None = None
    message: str | None = None


class HostTeamMemberCreate(BaseModel):
    """Legacy create — routes to invite when email/username or user_id provided."""

    user_id: UUID | None = None
    invited_email: str | None = Field(default=None, max_length=320)
    role_label: str = Field(default="scanner", min_length=2, max_length=64)
    role: str | None = Field(default=None, max_length=32)
    permissions: dict[str, bool] | None = None
    scope: str | None = Field(default=None, max_length=32)
    scoped_event_ids: list[UUID] | None = None

    @field_validator("invited_email")
    @classmethod
    def normalize_invitee(cls, value: str | None) -> str | None:
        if not value:
            return value
        from app.hosts.team_invite_resolve import normalize_invitee_input

        return normalize_invitee_input(value)


class HostTeamMemberUpdate(BaseModel):
    role: str | None = Field(default=None, max_length=32)
    role_label: str | None = Field(default=None, min_length=2, max_length=64)
    status: str | None = Field(default=None, max_length=32)
    permissions: dict[str, bool] | None = None
    scope: str | None = Field(default=None, max_length=32)
    scoped_event_ids: list[UUID] | None = None


class HostTeamPermissionsUpdate(BaseModel):
    role: str | None = Field(default=None, max_length=32)
    role_label: str | None = Field(default=None, min_length=2, max_length=64)
    permissions: dict[str, bool]
    scope: str | None = Field(default=None, max_length=32)
    scoped_event_ids: list[UUID] | None = None


class HostTeamMemberPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    host_id: UUID
    user_id: UUID | None
    role: str
    role_label: str
    status: str
    # Null for username invites — never expose private account email to the host.
    invited_email: str | None
    invite_method: str = "email"
    invited_username: str | None = None
    avatar_url: str | None = None
    permissions: dict[str, Any]
    scope: str = "host_wide"
    scoped_event_ids: list[UUID] = Field(default_factory=list)
    display_name: str | None = None
    invite_expires_at: datetime | None = None
    invited_at: datetime | None = None
    accepted_at: datetime | None = None
    suspended_at: datetime | None = None
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class HostTeamInvitePreview(BaseModel):
    host_display_name: str
    role: str
    role_label: str
    invite_method: str = "email"
    # Email hint for email invites; @username for username invites (no private email).
    invited_email_hint: str
    expires_at: datetime | None
    status: str
    already_accepted: bool = False


class HostTeamAuditItem(BaseModel):
    id: UUID
    action: str
    action_label: str | None = None
    actor_user_id: UUID | None = None
    actor_label: str | None = None
    target_user_id: UUID | None = None
    target_label: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    details: dict[str, Any] | None = None
    created_at: datetime
    source: str | None = None


class HostWorkspacePublic(BaseModel):
    host_id: UUID
    display_name: str
    slug: str
    kind: str  # owner | team_member | event_staff
    role: str
    role_label: str
    permissions: dict[str, Any]
    scope: str = "host_wide"
    scoped_event_ids: list[str] = Field(default_factory=list)
    membership_id: UUID | None = None
    is_owner: bool = False


class HostDeskEventPublic(BaseModel):
    id: UUID
    title: str
    slug: str
    status: str
    start_datetime: datetime
    # Safe public label; secret venue_name withheld for non-owners on hidden events.
    location_label: str | None = None
    venue_name: str | None = None
    staff_check_in_path: str
    host_check_in_path: str


class HostBankAccountCreate(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    bank_name: str = Field(min_length=2, max_length=160)
    account_name: str = Field(min_length=2, max_length=160)
    account_number: str = Field(min_length=4, max_length=32)
    currency: str = Field(default="NGN", min_length=3, max_length=8)
    is_default: bool = False


class HostBankAccountUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=120)
    bank_name: str | None = Field(default=None, min_length=2, max_length=160)
    account_name: str | None = Field(default=None, min_length=2, max_length=160)
    account_number: str | None = Field(default=None, min_length=4, max_length=32)
    currency: str | None = Field(default=None, min_length=3, max_length=8)
    is_default: bool | None = None


class HostBankAccountPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    host_id: UUID
    label: str
    bank_name: str
    account_name: str
    account_number_last4: str
    currency: str
    status: str
    is_default: bool
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class HostVerificationPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    host_id: UUID
    status: str
    notes: str | None
    reviewed_by: UUID | None
    reviewed_at: datetime | None
    created_at: datetime
    # Joined host/owner surface for admin Hosts directory (safe fields only).
    host_display_name: str | None = None
    host_slug: str | None = None
    host_status: str | None = None
    owner_user_id: UUID | None = None
    owner_full_name: str | None = None
    owner_email: str | None = None
    events_count: int = 0


class HostVerificationReject(BaseModel):
    notes: str = Field(min_length=3, max_length=2000)
