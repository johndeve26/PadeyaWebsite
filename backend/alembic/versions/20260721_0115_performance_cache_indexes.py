"""Alembic: discovery performance indexes for public caching.

Revision ID: 20260721_0115
Revises: 20260721_0114
Create Date: 2026-07-21

Composite indexes for published event discovery and blog public lists.
"""

from __future__ import annotations

from alembic import op

revision = "20260721_0115"
down_revision = "20260721_0114"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_events_status_start_datetime",
        "events",
        ["status", "start_datetime"],
        unique=False,
    )
    op.create_index(
        "ix_events_status_featured_start",
        "events",
        ["status", "featured", "start_datetime"],
        unique=False,
    )
    op.create_index(
        "ix_blog_posts_status_published_at",
        "blog_posts",
        ["status", "published_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_blog_posts_status_published_at", table_name="blog_posts")
    op.drop_index("ix_events_status_featured_start", table_name="events")
    op.drop_index("ix_events_status_start_datetime", table_name="events")
