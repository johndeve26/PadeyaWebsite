"""Admin API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AuditLogPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    actor_user_id: UUID | None
    action: str
    resource_type: str | None
    resource_id: str | None
    details: dict[str, Any] | None
    ip_address: str | None
    user_agent: str | None
    created_at: datetime


class ImpersonationStartRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)
    support_ticket_id: str | None = Field(default=None, max_length=128)
    # Default 30; max 60. Only 15 / 30 / 60 are accepted.
    duration_minutes: Literal[15, 30, 60] = 30


class ImpersonationStartResponse(BaseModel):
    """Start an audited impersonation session.

    ``access_token`` is the separate impersonation session JWT (target perms only).
    The admin's original session is not permanently replaced.
    """

    impersonation_id: UUID
    target_user_id: UUID
    expires_at: datetime
    redirect_to: str = "/dashboard"
    access_token: str
    token_type: str = "bearer"
    scopes: list[str] = Field(default_factory=lambda: ["view"])
    pack: str = "view"


class ImpersonationEndResponse(BaseModel):
    ended: bool = True
    return_to: str


class ImpersonationStatusResponse(BaseModel):
    """Current impersonation session for the caller (GET /me/impersonation)."""

    is_impersonating: bool = False
    impersonation_id: UUID | None = None
    current_user_id: UUID | None = None
    actual_user_id: UUID | None = None
    actor_admin_id: UUID | None = None
    target_user_id: UUID | None = None
    reason: str | None = None
    support_ticket_id: str | None = None
    started_at: datetime | None = None
    expires_at: datetime | None = None
    impersonator_email: str | None = None
    impersonator_full_name: str | None = None
    target_email: str | None = None
    target_full_name: str | None = None
    scopes: list[str] = Field(default_factory=list)
    pack: str | None = None


class SessionIdentityResponse(BaseModel):
    """Per-request auth identity (effective user + optional impersonation)."""

    current_user_id: UUID
    actor_admin_id: UUID | None = None
    impersonation_id: UUID | None = None
    is_impersonating: bool = False


class ImpersonationHistoryItem(BaseModel):
    """One past or active impersonation session for a target user."""

    id: UUID
    actor_admin_id: UUID
    started_by: str
    started_by_email: str | None = None
    target_user_id: UUID
    reason: str
    support_ticket_id: str | None = None
    started_at: datetime
    ended_at: datetime | None = None
    expires_at: datetime
    status: str
    scopes: list[str] = Field(default_factory=list)
    pack: str | None = None
