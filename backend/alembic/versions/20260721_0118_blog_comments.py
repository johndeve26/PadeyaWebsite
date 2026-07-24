"""Alembic: blog comments for guest + authenticated readers.

Revision ID: 20260721_0118
Revises: 20260721_0117
Create Date: 2026-07-21
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260721_0118"
down_revision = "20260721_0117"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "blog_comments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("post_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("guest_name", sa.String(length=120), nullable=True),
        sa.Column("guest_email", sa.String(length=255), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="published"),
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
        sa.ForeignKeyConstraint(["post_id"], ["blog_posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["archived_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_blog_comments_post_id", "blog_comments", ["post_id"])
    op.create_index("ix_blog_comments_user_id", "blog_comments", ["user_id"])
    op.create_index("ix_blog_comments_status", "blog_comments", ["status"])
    op.create_index(
        "ix_blog_comments_post_status_created",
        "blog_comments",
        ["post_id", "status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_blog_comments_post_status_created", table_name="blog_comments")
    op.drop_index("ix_blog_comments_status", table_name="blog_comments")
    op.drop_index("ix_blog_comments_user_id", table_name="blog_comments")
    op.drop_index("ix_blog_comments_post_id", table_name="blog_comments")
    op.drop_table("blog_comments")
