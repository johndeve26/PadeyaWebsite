"""Sponsor saved items schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.sponsor_profiles.constants import SAVED_ITEM_TYPES


class SponsorSavedItemCreate(BaseModel):
    item_type: str
    item_id: UUID
    note: str | None = Field(default=None, max_length=2000)

    @field_validator("item_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in SAVED_ITEM_TYPES:
            raise ValueError("Invalid item_type")
        return v


class SponsorSavedItemNoteUpdate(BaseModel):
    note: str | None = Field(default=None, max_length=2000)


class SponsorSavedItemPublic(BaseModel):
    id: UUID
    sponsor_id: UUID
    item_type: str
    item_id: UUID
    note: str | None
    created_at: datetime
    updated_at: datetime
    available: bool
    title: str | None = None
    subtitle: str | None = None
    href: str | None = None
    sort_host_name: str | None = None
    sort_event_date: datetime | None = None


class SponsorSavedListPublic(BaseModel):
    items: list[SponsorSavedItemPublic]
    total: int
    saved_count: int
