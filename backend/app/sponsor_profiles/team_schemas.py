"""Sponsor team API schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.sponsor_profiles.constants import SPONSOR_TEAM_INVITE_ROLES


class SponsorTeamInviteCreate(BaseModel):
    email: EmailStr
    role: str = Field(default="viewer")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in SPONSOR_TEAM_INVITE_ROLES:
            raise ValueError("Invalid team role for invite")
        return v


class SponsorTeamMemberUpdate(BaseModel):
    role: str

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in SPONSOR_TEAM_INVITE_ROLES:
            raise ValueError("Invalid team role")
        return v


class SponsorTeamMemberPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID | None
    sponsor_id: UUID
    user_id: UUID | None
    email: str | None
    display_name: str | None
    role: str
    status: str
    is_owner: bool = False
    permissions: dict[str, bool]
    invited_at: datetime | None = None
    joined_at: datetime | None = None
    created_at: datetime | None = None


class SponsorTeamInvitePublic(BaseModel):
    id: UUID
    sponsor_id: UUID
    email: str
    role: str
    status: str
    invite_expires_at: datetime | None
    invited_at: datetime
    display_name: str | None = None


class SponsorTeamListPublic(BaseModel):
    members: list[SponsorTeamMemberPublic]
    invites: list[SponsorTeamInvitePublic]


class SponsorTeamInviteCreateResponse(BaseModel):
    invite: SponsorTeamInvitePublic
    accept_path: str


class SponsorTeamInvitePreview(BaseModel):
    sponsor_display_name: str
    role: str
    status: str
    expires_at: datetime | None


class SponsorTeamAuditItem(BaseModel):
    id: UUID
    action: str
    actor_user_id: UUID | None
    target_user_id: UUID | None
    entity_type: str | None
    entity_id: str | None
    metadata: dict | None
    created_at: datetime
