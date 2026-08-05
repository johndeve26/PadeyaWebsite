"""Taxonomy public and admin Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    slug: str | None = Field(default=None, max_length=140)
    description: str | None = Field(default=None, max_length=255)
    sort_order: int = 0
    featured: bool = False
    seo_title: str | None = Field(default=None, max_length=200)
    seo_description: str | None = Field(default=None, max_length=320)
    is_active: bool = True


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    slug: str | None = Field(default=None, max_length=140)
    description: str | None = Field(default=None, max_length=255)
    sort_order: int | None = None
    featured: bool | None = None
    seo_title: str | None = Field(default=None, max_length=200)
    seo_description: str | None = Field(default=None, max_length=320)
    is_active: bool | None = None
    primary_image_url: str | None = Field(default=None, max_length=1000)
    primary_image_alt: str | None = Field(default=None, max_length=240)
    primary_image_focal_x: float | None = Field(default=None, ge=0, le=1)
    primary_image_focal_y: float | None = Field(default=None, ge=0, le=1)
    hero_image_url: str | None = Field(default=None, max_length=1000)
    hero_image_alt: str | None = Field(default=None, max_length=240)
    hero_image_focal_x: float | None = Field(default=None, ge=0, le=1)
    hero_image_focal_y: float | None = Field(default=None, ge=0, le=1)


class CategoryPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    description: str | None
    sort_order: int
    featured: bool
    seo_title: str | None
    seo_description: str | None
    is_active: bool
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime
    usage_count: int | None = None
    primary_image_url: str | None = None
    primary_image_alt: str | None = None
    primary_image_focal_x: float = 0.5
    primary_image_focal_y: float = 0.5
    hero_image_url: str | None = None
    hero_image_alt: str | None = None
    hero_image_focal_x: float = 0.5
    hero_image_focal_y: float = 0.5
    # Convenience aliases for public cards (primary with hero fallback handled FE-side)
    image_url: str | None = None
    image_alt: str | None = None
    image_focal_x: float | None = None
    image_focal_y: float | None = None


class VocabCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    slug: str | None = Field(default=None, max_length=140)
    description: str | None = Field(default=None, max_length=255)
    sort_order: int = 0
    featured: bool = False
    seo_title: str | None = Field(default=None, max_length=200)
    seo_description: str | None = Field(default=None, max_length=320)
    is_active: bool = True


class VocabUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    slug: str | None = Field(default=None, max_length=140)
    description: str | None = Field(default=None, max_length=255)
    sort_order: int | None = None
    featured: bool | None = None
    seo_title: str | None = Field(default=None, max_length=200)
    seo_description: str | None = Field(default=None, max_length=320)
    is_active: bool | None = None


class VocabPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    description: str | None
    sort_order: int
    featured: bool
    seo_title: str | None
    seo_description: str | None
    is_active: bool
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime
    usage_count: int | None = None


class SubcategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    slug: str | None = Field(default=None, max_length=140)
    description: str | None = Field(default=None, max_length=255)
    sort_order: int = 0
    featured: bool = False
    seo_title: str | None = Field(default=None, max_length=200)
    seo_description: str | None = Field(default=None, max_length=320)
    is_active: bool = True


class SubcategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    slug: str | None = Field(default=None, max_length=140)
    description: str | None = Field(default=None, max_length=255)
    sort_order: int | None = None
    featured: bool | None = None
    seo_title: str | None = Field(default=None, max_length=200)
    seo_description: str | None = Field(default=None, max_length=320)
    is_active: bool | None = None


class SubcategoryPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    category_id: UUID
    name: str
    slug: str
    description: str | None
    sort_order: int
    featured: bool
    seo_title: str | None
    seo_description: str | None
    is_active: bool
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class LocationCreate(BaseModel):
    kind: str = Field(min_length=2, max_length=32)
    name: str = Field(min_length=2, max_length=160)
    slug: str | None = Field(default=None, max_length=180)
    parent_id: UUID | None = None
    state_code: str | None = Field(default=None, max_length=16)
    country_code: str | None = Field(default=None, max_length=8)
    is_active: bool = True


class AreaSuggestCreate(BaseModel):
    """Host-suggested area under an existing city — becomes available to all hosts."""

    city_id: UUID
    name: str = Field(min_length=2, max_length=160)


class CitySuggestCreate(BaseModel):
    """Host-suggested city under an existing state — becomes available to all hosts."""

    state_id: UUID
    name: str = Field(min_length=2, max_length=160)


class VenueTypeSuggestCreate(BaseModel):
    """Host-suggested venue type — becomes available to all hosts."""

    name: str = Field(min_length=2, max_length=120)


class LocationUpdate(BaseModel):
    kind: str | None = Field(default=None, min_length=2, max_length=32)
    name: str | None = Field(default=None, min_length=2, max_length=160)
    slug: str | None = Field(default=None, max_length=180)
    parent_id: UUID | None = None
    state_code: str | None = Field(default=None, max_length=16)
    country_code: str | None = Field(default=None, max_length=8)
    is_active: bool | None = None
    seo_title: str | None = Field(default=None, max_length=200)
    seo_description: str | None = Field(default=None, max_length=320)
    intro_content: str | None = None
    seo_index_mode: str | None = Field(default=None, max_length=24)
    primary_image_url: str | None = Field(default=None, max_length=1000)
    primary_image_alt: str | None = Field(default=None, max_length=240)
    primary_image_focal_x: float | None = Field(default=None, ge=0, le=1)
    primary_image_focal_y: float | None = Field(default=None, ge=0, le=1)
    hero_image_url: str | None = Field(default=None, max_length=1000)
    hero_image_alt: str | None = Field(default=None, max_length=240)
    hero_image_focal_x: float | None = Field(default=None, ge=0, le=1)
    hero_image_focal_y: float | None = Field(default=None, ge=0, le=1)


class LocationPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    kind: str
    name: str
    slug: str
    parent_id: UUID | None
    state_code: str | None
    country_code: str | None
    is_active: bool
    seo_title: str | None = None
    seo_description: str | None = None
    intro_content: str | None = None
    seo_index_mode: str = "auto"
    created_at: datetime
    updated_at: datetime
    primary_image_url: str | None = None
    primary_image_alt: str | None = None
    primary_image_focal_x: float = 0.5
    primary_image_focal_y: float = 0.5
    hero_image_url: str | None = None
    hero_image_alt: str | None = None
    hero_image_focal_x: float = 0.5
    hero_image_focal_y: float = 0.5
    image_url: str | None = None
    image_alt: str | None = None
    image_focal_x: float | None = None
    image_focal_y: float | None = None


class TaxonomyImageUploadResponse(BaseModel):
    url: str
    key: str | None = None
    kind: str
    term_id: UUID
    image_role: str
    thumbnail_url: str | None = None
    card_url: str | None = None
    display_url: str | None = None
    full_url: str | None = None
    media: dict[str, Any] | None = None


class TaxonomyVisualUpdate(BaseModel):
    """Dedicated visual settings payload (clear by sending null)."""

    primary_image_url: str | None = Field(default=None, max_length=1000)
    primary_image_alt: str | None = Field(default=None, max_length=240)
    primary_image_focal_x: float | None = Field(default=None, ge=0, le=1)
    primary_image_focal_y: float | None = Field(default=None, ge=0, le=1)
    hero_image_url: str | None = Field(default=None, max_length=1000)
    hero_image_alt: str | None = Field(default=None, max_length=240)
    hero_image_focal_x: float | None = Field(default=None, ge=0, le=1)
    hero_image_focal_y: float | None = Field(default=None, ge=0, le=1)
    clear_primary: bool = False
    clear_hero: bool = False


class LocationDetailPublic(BaseModel):
    """Location hub payload with ancestor chain, children, and siblings."""

    location: LocationPublic
    ancestors: list[LocationPublic] = []
    children: list[LocationPublic] = []
    siblings: list[LocationPublic] = []
