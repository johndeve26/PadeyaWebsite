"""Knowledge Base Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CategoryPublic(BaseModel):
    id: UUID
    name: str
    slug: str
    description: str | None = None
    group_key: str
    sort_order: int = 0
    icon_key: str | None = None
    article_count: int = 0

    model_config = {"from_attributes": True}


class CategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    slug: str | None = Field(default=None, max_length=140)
    description: str | None = None
    group_key: str = Field(default="general", max_length=40)
    sort_order: int = 0
    icon_key: str | None = Field(default=None, max_length=40)


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    slug: str | None = Field(default=None, max_length=140)
    description: str | None = None
    group_key: str | None = Field(default=None, max_length=40)
    sort_order: int | None = None
    icon_key: str | None = Field(default=None, max_length=40)


class TagPublic(BaseModel):
    id: UUID
    name: str
    slug: str

    model_config = {"from_attributes": True}


class ArticleListItem(BaseModel):
    id: UUID
    title: str
    slug: str
    excerpt: str | None = None
    content_type: str
    difficulty: str
    audiences: list[str] = []
    cover_url: str | None = None
    video_url: str | None = None
    video_provider: str | None = None
    video_thumbnail_url: str | None = None
    status: str
    is_featured: bool = False
    reading_time_minutes: int = 1
    helpful_count: int = 0
    not_helpful_count: int = 0
    view_count: int = 0
    published_at: datetime | None = None
    updated_at: datetime | None = None
    category: CategoryPublic | None = None
    tags: list[TagPublic] = []

    model_config = {"from_attributes": True}


class ArticlePublic(ArticleListItem):
    body: str = ""
    body_html: str = ""
    video_embed_url: str | None = None
    seo_title: str | None = None
    seo_description: str | None = None
    related: list[ArticleListItem] = []


class ArticleAdmin(ArticlePublic):
    scheduled_at: datetime | None = None
    related_article_ids: list[UUID] = []
    created_by: UUID | None = None
    updated_by: UUID | None = None
    archived_at: datetime | None = None
    created_at: datetime | None = None


class ArticleCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    slug: str | None = Field(default=None, max_length=220)
    excerpt: str | None = None
    body: str = ""
    content_type: str = "text"
    difficulty: str = "beginner"
    audiences: list[str] = Field(default_factory=lambda: ["visitor"])
    cover_url: str | None = None
    video_url: str | None = None
    category_id: UUID | None = None
    tag_slugs: list[str] = Field(default_factory=list)
    is_featured: bool = False
    featured_sort: int = 0
    seo_title: str | None = None
    seo_description: str | None = None
    related_article_ids: list[UUID] = Field(default_factory=list)
    status: str = "draft"
    scheduled_at: datetime | None = None


class ArticleUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    slug: str | None = Field(default=None, max_length=220)
    excerpt: str | None = None
    body: str | None = None
    content_type: str | None = None
    difficulty: str | None = None
    audiences: list[str] | None = None
    cover_url: str | None = None
    video_url: str | None = None
    category_id: UUID | None = None
    tag_slugs: list[str] | None = None
    is_featured: bool | None = None
    featured_sort: int | None = None
    seo_title: str | None = None
    seo_description: str | None = None
    related_article_ids: list[UUID] | None = None
    status: str | None = None
    scheduled_at: datetime | None = None


class FeedbackCreate(BaseModel):
    is_helpful: bool
    comment: str | None = Field(default=None, max_length=500)
