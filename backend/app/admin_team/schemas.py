"""Pydantic schemas for admin team management."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class AdminTeamInviteCreate(BaseModel):
    email: EmailStr
    admin_role_id: UUID | None = None
    system_key: str | None = Field(
        default=None,
        description="Preset role key when admin_role_id is omitted",
    )


class AdminRoleCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    permission_codes: list[str] = Field(default_factory=list)


class AdminRoleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    permission_codes: list[str] | None = None


class AdminTeamMemberUpdate(BaseModel):
    admin_role_id: UUID | None = None
    system_key: str | None = None
    permission_codes: list[str] | None = None


class AdminTeamMemberDisable(BaseModel):
    reason: str | None = Field(default=None, max_length=500)
    remove: bool = False


class AdminTeamForceLogout(BaseModel):
    reason: str | None = Field(default=None, max_length=500)
