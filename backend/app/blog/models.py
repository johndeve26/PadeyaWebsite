"""Pàdéyá Blog ORM models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.database import Base

JSON_TYPE = JSON().with_variant(JSONB(), "postgresql")


class BlogCategory(Base):
    __tablename__ = "blog_categories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(140), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    seo_title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    seo_description: Mapped[str | None] = mapped_column(String(320), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class BlogTag(Base):
    __tablename__ = "blog_tags"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class BlogPostType(Base):
    """Admin-managed editorial post types (replaces hardcoded BLOG_CONTENT_TYPES)."""

    __tablename__ = "blog_post_types"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(140), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class BlogMediaRole(Base):
    """Blog-only media role vocabulary (cover, og, inline, …)."""

    __tablename__ = "blog_media_roles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    storage_folder: Mapped[str] = mapped_column(String(80), nullable=False, default="content")
    allowed_contexts: Mapped[list[Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class BlogTaxonomySlugRedirect(Base):
    """Preserve public category/tag URLs when slugs change."""

    __tablename__ = "blog_taxonomy_slug_redirects"
    __table_args__ = (
        UniqueConstraint(
            "resource_type",
            "old_slug",
            name="uq_blog_taxonomy_slug_redirects_type_old",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    resource_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    old_slug: Mapped[str] = mapped_column(String(140), nullable=False, index=True)
    new_slug: Mapped[str] = mapped_column(String(140), nullable=False)
    resource_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class BlogAuthor(Base):
    __tablename__ = "blog_authors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(140), unique=True, nullable=False, index=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    role_title: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class BlogPost(Base):
    """Public editorial posts — draft / scheduled / published / archived."""

    __tablename__ = "blog_posts"
    __table_args__ = (
        UniqueConstraint(
            "created_by",
            "client_creation_id",
            name="uq_blog_posts_created_by_client_creation_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), unique=True, nullable=False, index=True)
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Markdown / structured source (never trust raw HTML from clients)
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    cover_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cover_media: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    # draft | scheduled | published | archived
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", index=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reading_time_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("blog_categories.id", ondelete="SET NULL"), nullable=True
    )
    post_type_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("blog_post_types.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    author_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("blog_authors.id", ondelete="SET NULL"), nullable=True
    )
    seo_title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    seo_description: Mapped[str | None] = mapped_column(String(320), nullable=True)
    canonical_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    og_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    admin_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Blog AI Studio fields (draft-only; never auto-publish)
    studio_brief: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    studio_outline: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    faqs: Mapped[list[Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    content_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # Block editor structured document (canonical when present)
    content_document: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    content_document_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )
    editor_mode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    hero_settings: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    focus_keyword: Mapped[str | None] = mapped_column(String(120), nullable=True)
    secondary_keywords: Mapped[list[Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    social_share_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    og_title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    client_creation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    category = relationship("BlogCategory", lazy="joined")
    post_type = relationship("BlogPostType", lazy="joined")
    author = relationship("BlogAuthor", lazy="joined")
    tags = relationship(
        "BlogTag",
        secondary="blog_post_tags",
        lazy="selectin",
    )
    revisions = relationship(
        "BlogRevision",
        back_populates="post",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    ai_operations = relationship(
        "BlogAiOperation",
        back_populates="post",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class BlogPostTag(Base):
    __tablename__ = "blog_post_tags"
    __table_args__ = (
        UniqueConstraint("post_id", "tag_id", name="uq_blog_post_tags_post_tag"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("blog_posts.id", ondelete="CASCADE"), nullable=False
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("blog_tags.id", ondelete="CASCADE"), nullable=False
    )


class BlogComment(Base):
    """Public comments on published blog posts — guest or authenticated."""

    __tablename__ = "blog_comments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("blog_posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    parent_comment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("blog_comments.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    # 0 = top-level comment, 1 = reply (one-level threading only)
    depth: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reply_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Snapshot: author had staff/moderator perms when posting (badge on FE)
    is_staff_author: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Guest attribution (ignored when user_id is set)
    guest_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    guest_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    # published | hidden | archived
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="published", index=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    edited_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    edited_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    post = relationship("BlogPost", lazy="joined")


class BlogCommentEdit(Base):
    """Immutable history of blog comment body edits (not exposed publicly)."""

    __tablename__ = "blog_comment_edits"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    comment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("blog_comments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    edited_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    edited_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    previous_body: Mapped[str] = mapped_column(Text, nullable=False)
    new_body: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # owner | admin | moderator
    edit_type: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class BlogRevision(Base):
    """Immutable draft snapshots for Blog AI Studio / manual checkpoints."""

    __tablename__ = "blog_revisions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("blog_posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Snapshot fields (never store secrets/prompts)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    seo_title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    seo_description: Mapped[str | None] = mapped_column(String(320), nullable=True)
    faqs: Mapped[list[Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    studio_outline: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    studio_brief: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    content_document: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    hero_settings: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    content_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # Metadata
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    # manual | ai
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    # checkpoint | autosave | publish | full_draft | restore | etc.
    action_type: Mapped[str] = mapped_column(String(64), nullable=False, default="checkpoint")
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    post = relationship("BlogPost", back_populates="revisions")


class BlogAiOperation(Base):
    """Safe metadata log for Blog AI Studio operations (no prompts/secrets/bodies)."""

    __tablename__ = "blog_ai_operations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    post_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("blog_posts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    operation: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    feature_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_in: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_out: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Safe error summary only — never API keys or full prompts
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    client_request_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    post = relationship("BlogPost", back_populates="ai_operations")


class BlogLayoutTemplate(Base):
    """Article layout templates — built-in or admin-created."""

    __tablename__ = "blog_layout_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(180), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False, default="general")
    document: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    hero_settings: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    is_builtin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class BlogReusableSection(Base):
    """Saved reusable section blocks — copied on insert."""

    __tablename__ = "blog_reusable_sections"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(180), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    section: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
