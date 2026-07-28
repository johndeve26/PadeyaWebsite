"""Blog AI Studio fields, revisions, and AI operations.

Revision ID: 20260729_0147
Revises: 20260728_0146
Create Date: 2026-07-29
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260729_0147"
down_revision = "20260728_0146"
branch_labels = None
depends_on = None

JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.add_column("blog_posts", sa.Column("studio_brief", JSON_TYPE, nullable=True))
    op.add_column("blog_posts", sa.Column("studio_outline", JSON_TYPE, nullable=True))
    op.add_column("blog_posts", sa.Column("faqs", JSON_TYPE, nullable=True))
    op.add_column(
        "blog_posts",
        sa.Column("content_version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "blog_posts", sa.Column("focus_keyword", sa.String(length=120), nullable=True)
    )
    op.add_column("blog_posts", sa.Column("secondary_keywords", JSON_TYPE, nullable=True))
    op.add_column("blog_posts", sa.Column("social_share_text", sa.Text(), nullable=True))
    op.add_column(
        "blog_posts", sa.Column("og_title", sa.String(length=200), nullable=True)
    )

    op.create_table(
        "blog_revisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("post_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("seo_title", sa.String(length=200), nullable=True),
        sa.Column("seo_description", sa.String(length=320), nullable=True),
        sa.Column("faqs", JSON_TYPE, nullable=True),
        sa.Column("studio_outline", JSON_TYPE, nullable=True),
        sa.Column("studio_brief", JSON_TYPE, nullable=True),
        sa.Column("content_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="manual"),
        sa.Column(
            "action_type", sa.String(length=64), nullable=False, server_default="checkpoint"
        ),
        sa.Column("provider", sa.String(length=64), nullable=True),
        sa.Column("model_name", sa.String(length=120), nullable=True),
        sa.Column("summary", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["post_id"], ["blog_posts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_blog_revisions_post_id", "blog_revisions", ["post_id"])
    op.create_index("ix_blog_revisions_created_at", "blog_revisions", ["created_at"])

    op.create_table(
        "blog_ai_operations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("post_id", sa.Uuid(), nullable=True),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("operation", sa.String(length=64), nullable=False),
        sa.Column("feature_key", sa.String(length=120), nullable=True),
        sa.Column("provider", sa.String(length=64), nullable=True),
        sa.Column("model_name", sa.String(length=120), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("tokens_in", sa.Integer(), nullable=True),
        sa.Column("tokens_out", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("client_request_id", sa.String(length=120), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["post_id"], ["blog_posts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_blog_ai_operations_post_id", "blog_ai_operations", ["post_id"])
    op.create_index("ix_blog_ai_operations_operation", "blog_ai_operations", ["operation"])
    op.create_index(
        "ix_blog_ai_operations_client_request_id",
        "blog_ai_operations",
        ["client_request_id"],
    )
    op.create_index(
        "ix_blog_ai_operations_created_at", "blog_ai_operations", ["created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_blog_ai_operations_created_at", table_name="blog_ai_operations")
    op.drop_index(
        "ix_blog_ai_operations_client_request_id", table_name="blog_ai_operations"
    )
    op.drop_index("ix_blog_ai_operations_operation", table_name="blog_ai_operations")
    op.drop_index("ix_blog_ai_operations_post_id", table_name="blog_ai_operations")
    op.drop_table("blog_ai_operations")

    op.drop_index("ix_blog_revisions_created_at", table_name="blog_revisions")
    op.drop_index("ix_blog_revisions_post_id", table_name="blog_revisions")
    op.drop_table("blog_revisions")

    op.drop_column("blog_posts", "og_title")
    op.drop_column("blog_posts", "social_share_text")
    op.drop_column("blog_posts", "secondary_keywords")
    op.drop_column("blog_posts", "focus_keyword")
    op.drop_column("blog_posts", "content_version")
    op.drop_column("blog_posts", "faqs")
    op.drop_column("blog_posts", "studio_outline")
    op.drop_column("blog_posts", "studio_brief")
