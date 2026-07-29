"""Host Pydantic schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class HostOnboardRequest(BaseModel):
    display_name: str = Field(min_length=2, max_length=160)
    bio: str | None = Field(default=None, max_length=5000)
    website: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=120)
    state: str | None = Field(default=None, max_length=120)
    country: str | None = Field(default=None, max_length=120)


class HostProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=2, max_length=160)
    bio: str | None = None
    website: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=120)
    state: str | None = Field(default=None, max_length=120)
    country: str | None = Field(default=None, max_length=120)
    avatar_url: str | None = Field(default=None, max_length=500)
    cover_url: str | None = Field(default=None, max_length=500)
    social_links: dict[str, Any] | None = None
    host_type_slugs: list[str] | None = None
    category_slugs: list[str] | None = None
    audience_slugs: list[str] | None = None
    primary_city_slug: str | None = None
    service_area_slugs: list[str] | None = None
    niche_positioning: str | None = Field(default=None, max_length=280)


class HostProfilePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    bio: str | None
    website: str | None
    city: str | None
    state: str | None
    country: str | None
    avatar_url: str | None
    cover_url: str | None
    social_links: dict[str, Any] | None


class HostTaxonomyPublic(BaseModel):
    host_type_slugs: list[str] = Field(default_factory=list)
    category_slugs: list[str] = Field(default_factory=list)
    audience_slugs: list[str] = Field(default_factory=list)
    primary_city_slug: str | None = None
    service_area_slugs: list[str] = Field(default_factory=list)
    niche_positioning: str | None = None


class HostPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    display_name: str
    slug: str
    status: str
    created_at: datetime
    profile: HostProfilePublic | None = None
    taxonomy: HostTaxonomyPublic | None = None
    gender: str | None = None
    gender_short: str | None = None
    gender_label: str | None = None
    gender_visible: bool = False
    shows_personal_gender: bool = False
