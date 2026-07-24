"""CMS Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BlogPostCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    slug: str | None = Field(default=None, max_length=220)
    excerpt: str | None = None
    body: str = Field(min_length=1)
    cover_url: str | None = Field(default=None, max_length=500)


class BlogPostUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    slug: str | None = Field(default=None, max_length=220)
    excerpt: str | None = None
    body: str | None = None
    cover_url: str | None = Field(default=None, max_length=500)


class BlogPostPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    slug: str
    excerpt: str | None
    body: str
    cover_url: str | None
    status: str
    published_at: datetime | None
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class FaqCreate(BaseModel):
    question: str = Field(min_length=3, max_length=300)
    answer: str = Field(min_length=1)
    category: str = Field(default="general", max_length=80)
    sort_order: int = 0


class FaqUpdate(BaseModel):
    question: str | None = Field(default=None, min_length=3, max_length=300)
    answer: str | None = None
    category: str | None = Field(default=None, max_length=80)
    sort_order: int | None = None


class FaqPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    question: str
    answer: str
    category: str
    sort_order: int
    status: str
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class BannerCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    subtitle: str | None = Field(default=None, max_length=300)
    image_url: str = Field(min_length=1, max_length=500)
    cta_label: str | None = Field(default=None, max_length=80)
    cta_href: str | None = Field(default=None, max_length=500)
    sort_order: int = 0


class BannerUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    subtitle: str | None = Field(default=None, max_length=300)
    image_url: str | None = Field(default=None, max_length=500)
    cta_label: str | None = Field(default=None, max_length=80)
    cta_href: str | None = Field(default=None, max_length=500)
    sort_order: int | None = None


class BannerPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    subtitle: str | None
    image_url: str
    cta_label: str | None
    cta_href: str | None
    sort_order: int
    status: str
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


BROWSE_RAILS = frozenset({"interest", "city", "price", "when"})


class BrowseTileCreate(BaseModel):
    rail: str = Field(min_length=2, max_length=32)
    label: str = Field(min_length=1, max_length=120)
    hint: str | None = Field(default=None, max_length=200)
    href: str = Field(min_length=1, max_length=500)
    image_url: str = Field(min_length=1, max_length=500)
    sort_order: int = 0


class BrowseTileUpdate(BaseModel):
    rail: str | None = Field(default=None, min_length=2, max_length=32)
    label: str | None = Field(default=None, min_length=1, max_length=120)
    hint: str | None = Field(default=None, max_length=200)
    href: str | None = Field(default=None, min_length=1, max_length=500)
    image_url: str | None = Field(default=None, min_length=1, max_length=500)
    sort_order: int | None = None


class BrowseTilePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    rail: str
    label: str
    hint: str | None
    href: str
    image_url: str
    sort_order: int
    status: str
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime
