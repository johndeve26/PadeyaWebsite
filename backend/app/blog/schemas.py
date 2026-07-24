"""Blog API schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class CategoryPublic(BaseModel):
    id: UUID
    name: str
    slug: str
    description: str | None = None

    model_config = {"from_attributes": True}


class TagPublic(BaseModel):
    id: UUID
    name: str
    slug: str

    model_config = {"from_attributes": True}


class AuthorPublic(BaseModel):
    id: UUID
    display_name: str
    slug: str
    bio: str | None = None
    avatar_url: str | None = None
    role_title: str | None = None

    model_config = {"from_attributes": True}


class PostListItem(BaseModel):
    id: UUID
    title: str
    slug: str
    excerpt: str | None = None
    cover_url: str | None = None
    status: str
    is_featured: bool = False
    reading_time_minutes: int = 1
    published_at: datetime | None = None
    scheduled_at: datetime | None = None
    updated_at: datetime | None = None
    category: CategoryPublic | None = None
    author: AuthorPublic | None = None
    tags: list[TagPublic] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class PostPublic(PostListItem):
    body: str
    body_html: str
    seo_title: str | None = None
    seo_description: str | None = None
    canonical_url: str | None = None
    og_image_url: str | None = None
    related: list[PostListItem] = Field(default_factory=list)


class PostAdmin(PostPublic):
    admin_notes: str | None = None
    created_at: datetime | None = None
    created_by: UUID | None = None
    updated_by: UUID | None = None
    archived_at: datetime | None = None


class PostCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    slug: str | None = Field(default=None, max_length=220)
    excerpt: str | None = None
    body: str = ""
    cover_url: str | None = None
    category_id: UUID | None = None
    author_id: UUID | None = None
    tag_ids: list[UUID] = Field(default_factory=list)
    is_featured: bool = False
    seo_title: str | None = Field(default=None, max_length=200)
    seo_description: str | None = Field(default=None, max_length=320)
    canonical_url: str | None = Field(default=None, max_length=500)
    og_image_url: str | None = None
    admin_notes: str | None = None
    scheduled_at: datetime | None = None

    @field_validator("title")
    @classmethod
    def strip_title(cls, v: str) -> str:
        return v.strip()


class PostUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    slug: str | None = Field(default=None, max_length=220)
    excerpt: str | None = None
    body: str | None = None
    cover_url: str | None = None
    category_id: UUID | None = None
    author_id: UUID | None = None
    tag_ids: list[UUID] | None = None
    is_featured: bool | None = None
    seo_title: str | None = None
    seo_description: str | None = None
    canonical_url: str | None = None
    og_image_url: str | None = None
    admin_notes: str | None = None
    scheduled_at: datetime | None = None
    status: str | None = None


class CategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    slug: str | None = None
    description: str | None = None
    sort_order: int = 0


class TagCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    slug: str | None = None


class AuthorCreate(BaseModel):
    display_name: str = Field(min_length=2, max_length=120)
    slug: str | None = None
    bio: str | None = None
    avatar_url: str | None = None
    role_title: str | None = None
    user_id: UUID | None = None


class SlugCheck(BaseModel):
    slug: str
    available: bool


class CommentPublic(BaseModel):
    id: UUID
    post_id: UUID
    body: str
    status: str
    display_name: str
    is_guest: bool = False
    # Set only when the author has a public Fan Passport — FE links only when present.
    passport_path: str | None = None
    created_at: datetime
    # True when the current viewer owns this comment (authenticated create/list).
    is_mine: bool = False
    # Viewer may edit (owner with permission, or admin/moderator).
    can_edit: bool = False
    can_reply: bool = False
    is_edited: bool = False
    edited_at: datetime | None = None
    # True when last material edit was by a moderator/admin (not the owner).
    edited_by_moderator: bool = False
    parent_comment_id: UUID | None = None
    depth: int = 0
    reply_count: int = 0
    is_staff_author: bool = False
    # Public badge only — never private roles/emails.
    author_badge: str | None = None
    replies: list["CommentPublic"] = Field(default_factory=list)


class CommentCreate(BaseModel):
    body: str = Field(min_length=2, max_length=2000)
    # Guest: name required when not authenticated; email optional (moderation only).
    guest_name: str | None = Field(default=None, max_length=120)
    guest_email: str | None = Field(default=None, max_length=255)
    # Honeypot — bots fill this; leave empty
    website: str | None = Field(default="", max_length=200)

    @field_validator("body")
    @classmethod
    def strip_body(cls, v: str) -> str:
        return (v or "").strip()

    @field_validator("guest_name")
    @classmethod
    def strip_name(cls, v: str | None) -> str | None:
        if v is None:
            return None
        cleaned = v.strip()
        return cleaned or None

    @field_validator("guest_email")
    @classmethod
    def strip_guest_email(cls, v: str | None) -> str | None:
        if v is None:
            return None
        cleaned = v.strip().lower()
        return cleaned or None


class CommentReplyCreate(BaseModel):
    """Body for POST /blog/comments/{id}/reply — parent comes from the route."""

    body: str = Field(min_length=2, max_length=2000)
    guest_name: str | None = Field(default=None, max_length=120)
    guest_email: str | None = Field(default=None, max_length=255)
    website: str | None = Field(default="", max_length=200)

    @field_validator("body")
    @classmethod
    def strip_body(cls, v: str) -> str:
        return (v or "").strip()

    @field_validator("guest_name")
    @classmethod
    def strip_name(cls, v: str | None) -> str | None:
        if v is None:
            return None
        cleaned = v.strip()
        return cleaned or None

    @field_validator("guest_email")
    @classmethod
    def strip_guest_email(cls, v: str | None) -> str | None:
        if v is None:
            return None
        cleaned = v.strip().lower()
        return cleaned or None


class CommentUpdate(BaseModel):
    body: str = Field(min_length=2, max_length=2000)
    edit_reason: str | None = Field(default=None, max_length=500)

    @field_validator("body")
    @classmethod
    def strip_body(cls, v: str) -> str:
        return (v or "").strip()

    @field_validator("edit_reason")
    @classmethod
    def strip_reason(cls, v: str | None) -> str | None:
        if v is None:
            return None
        cleaned = v.strip()
        return cleaned or None


class CommentAdmin(CommentPublic):
    user_id: UUID | None = None
    guest_email: str | None = None
    archived_at: datetime | None = None
    archived_by: UUID | None = None
    updated_at: datetime | None = None
    edited_by_user_id: UUID | None = None
    edited_by_admin_id: UUID | None = None


CommentPublic.model_rebuild()
