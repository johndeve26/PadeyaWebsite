"""Schemas for host team API surface (`/host/team`, `/me`, `/admin/teams`)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ActiveWorkspaceSet(BaseModel):
    host_id: UUID


class ActiveWorkspacePublic(BaseModel):
    host_id: UUID
    display_name: str
    slug: str
    kind: str
    role: str
    role_label: str
    is_owner: bool = False


class TeamRoleCatalogItem(BaseModel):
    role: str
    label: str
    default_scope: str
    default_permissions: dict[str, bool]


class TeamPermissionGroupCatalog(BaseModel):
    group: str
    keys: list[str]


class TeamPermissionsCatalog(BaseModel):
    groups: list[TeamPermissionGroupCatalog]
    keys: list[str]
    owner_only_keys: list[str]


class AdminTeamSummary(BaseModel):
    host_id: UUID
    display_name: str
    slug: str
    status: str
    owner_user_id: UUID
    owner_email: str | None = None
    member_count: int = 0
    pending_invite_count: int = 0
    created_at: datetime | None = None


class AdminTeamAuditItem(BaseModel):
    id: UUID
    host_id: UUID
    host_display_name: str | None = None
    action: str
    actor_user_id: UUID | None = None
    target_user_id: UUID | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    details: dict[str, Any] | None = None
    created_at: datetime


class TeamWorkspacePublic(BaseModel):
    host_id: UUID
    display_name: str
    slug: str
    kind: str
    role: str
    role_label: str
    permissions: dict[str, Any]
    scope: str = "host_wide"
    scoped_event_ids: list[str] = Field(default_factory=list)
    membership_id: UUID | None = None
    is_owner: bool = False
    is_active: bool = False
