"""Alembic: one-level blog comment replies (parent_comment_id + depth).

Revision ID: 20260721_0120
Revises: 20260721_0119
Create Date: 2026-07-21
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260721_0120"
down_revision = "20260721_0119"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "blog_comments",
        sa.Column("parent_comment_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "blog_comments",
        sa.Column("depth", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "blog_comments",
        sa.Column("reply_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "blog_comments",
        sa.Column(
            "is_staff_author",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.create_foreign_key(
        "fk_blog_comments_parent_comment_id",
        "blog_comments",
        "blog_comments",
        ["parent_comment_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_blog_comments_parent_comment_id",
        "blog_comments",
        ["parent_comment_id"],
    )
    op.create_index(
        "ix_blog_comments_post_parent_created",
        "blog_comments",
        ["post_id", "parent_comment_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_blog_comments_post_parent_created", table_name="blog_comments")
    op.drop_index("ix_blog_comments_parent_comment_id", table_name="blog_comments")
    op.drop_constraint(
        "fk_blog_comments_parent_comment_id", "blog_comments", type_="foreignkey"
    )
    op.drop_column("blog_comments", "is_staff_author")
    op.drop_column("blog_comments", "reply_count")
    op.drop_column("blog_comments", "depth")
    op.drop_column("blog_comments", "parent_comment_id")
