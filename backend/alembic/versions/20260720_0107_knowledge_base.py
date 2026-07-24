"""Alembic: knowledge base / help center tables.

Revision ID: 20260720_0107
Revises: 20260720_0106
Create Date: 2026-07-20
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260720_0107"
down_revision = "20260720_0106"
branch_labels = None
depends_on = None

JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "knowledge_base_categories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=140), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "group_key",
            sa.String(length=40),
            nullable=False,
            server_default="general",
        ),
        sa.Column(
            "sort_order", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("icon_key", sa.String(length=40), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index(
        "ix_knowledge_base_categories_slug",
        "knowledge_base_categories",
        ["slug"],
    )

    op.create_table(
        "knowledge_base_tags",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index(
        "ix_knowledge_base_tags_slug", "knowledge_base_tags", ["slug"]
    )

    op.create_table(
        "knowledge_base_articles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=220), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "content_type",
            sa.String(length=40),
            nullable=False,
            server_default="text",
        ),
        sa.Column(
            "difficulty",
            sa.String(length=32),
            nullable=False,
            server_default="beginner",
        ),
        sa.Column("audiences", JSON_TYPE, nullable=False),
        sa.Column("cover_url", sa.String(length=500), nullable=True),
        sa.Column("video_url", sa.String(length=500), nullable=True),
        sa.Column("video_provider", sa.String(length=32), nullable=True),
        sa.Column("video_thumbnail_url", sa.String(length=500), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="draft",
        ),
        sa.Column(
            "is_featured",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "featured_sort", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "reading_time_minutes",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
        sa.Column(
            "helpful_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "not_helpful_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "view_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("category_id", sa.Uuid(), nullable=True),
        sa.Column("seo_title", sa.String(length=200), nullable=True),
        sa.Column("seo_description", sa.String(length=320), nullable=True),
        sa.Column("related_article_ids", JSON_TYPE, nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_by", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["knowledge_base_categories.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"], ["users.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["archived_by"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index(
        "ix_knowledge_base_articles_slug",
        "knowledge_base_articles",
        ["slug"],
    )
    op.create_index(
        "ix_knowledge_base_articles_status",
        "knowledge_base_articles",
        ["status"],
    )
    op.create_index(
        "ix_knowledge_base_articles_category_id",
        "knowledge_base_articles",
        ["category_id"],
    )
    op.create_index(
        "ix_knowledge_base_articles_published_at",
        "knowledge_base_articles",
        ["published_at"],
    )
    op.create_index(
        "ix_knowledge_base_articles_scheduled_at",
        "knowledge_base_articles",
        ["scheduled_at"],
    )

    op.create_table(
        "knowledge_base_article_tags",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("article_id", sa.Uuid(), nullable=False),
        sa.Column("tag_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["article_id"],
            ["knowledge_base_articles.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"], ["knowledge_base_tags.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "article_id",
            "tag_id",
            name="uq_kb_article_tags_article_tag",
        ),
    )

    op.create_table(
        "knowledge_base_feedback",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("article_id", sa.Uuid(), nullable=False),
        sa.Column("is_helpful", sa.Boolean(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("comment", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["article_id"],
            ["knowledge_base_articles.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_knowledge_base_feedback_article_id",
        "knowledge_base_feedback",
        ["article_id"],
    )

    op.create_table(
        "knowledge_base_search_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("query", sa.String(length=120), nullable=False),
        sa.Column(
            "result_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("audience", sa.String(length=40), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_knowledge_base_search_logs_query",
        "knowledge_base_search_logs",
        ["query"],
    )
    op.create_index(
        "ix_knowledge_base_search_logs_created_at",
        "knowledge_base_search_logs",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_knowledge_base_search_logs_created_at",
        table_name="knowledge_base_search_logs",
    )
    op.drop_index(
        "ix_knowledge_base_search_logs_query",
        table_name="knowledge_base_search_logs",
    )
    op.drop_table("knowledge_base_search_logs")
    op.drop_index(
        "ix_knowledge_base_feedback_article_id",
        table_name="knowledge_base_feedback",
    )
    op.drop_table("knowledge_base_feedback")
    op.drop_table("knowledge_base_article_tags")
    op.drop_index(
        "ix_knowledge_base_articles_scheduled_at",
        table_name="knowledge_base_articles",
    )
    op.drop_index(
        "ix_knowledge_base_articles_published_at",
        table_name="knowledge_base_articles",
    )
    op.drop_index(
        "ix_knowledge_base_articles_category_id",
        table_name="knowledge_base_articles",
    )
    op.drop_index(
        "ix_knowledge_base_articles_status",
        table_name="knowledge_base_articles",
    )
    op.drop_index(
        "ix_knowledge_base_articles_slug",
        table_name="knowledge_base_articles",
    )
    op.drop_table("knowledge_base_articles")
    op.drop_index(
        "ix_knowledge_base_tags_slug", table_name="knowledge_base_tags"
    )
    op.drop_table("knowledge_base_tags")
    op.drop_index(
        "ix_knowledge_base_categories_slug",
        table_name="knowledge_base_categories",
    )
    op.drop_table("knowledge_base_categories")
