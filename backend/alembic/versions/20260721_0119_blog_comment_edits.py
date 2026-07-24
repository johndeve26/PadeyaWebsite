"""Alembic: blog comment edit metadata + edit history.

Revision ID: 20260721_0119
Revises: 20260721_0118
Create Date: 2026-07-21
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260721_0119"
down_revision = "20260721_0118"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "blog_comments",
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "blog_comments",
        sa.Column("edited_by_user_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "blog_comments",
        sa.Column("edited_by_admin_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_blog_comments_edited_by_user_id",
        "blog_comments",
        "users",
        ["edited_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_blog_comments_edited_by_admin_id",
        "blog_comments",
        "users",
        ["edited_by_admin_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "blog_comment_edits",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("comment_id", sa.Uuid(), nullable=False),
        sa.Column("edited_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("edited_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("previous_body", sa.Text(), nullable=False),
        sa.Column("new_body", sa.Text(), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=True),
        # owner | admin | moderator
        sa.Column("edit_type", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["comment_id"], ["blog_comments.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["edited_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["edited_by_admin_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_blog_comment_edits_comment_id", "blog_comment_edits", ["comment_id"]
    )
    op.create_index(
        "ix_blog_comment_edits_created_at", "blog_comment_edits", ["created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_blog_comment_edits_created_at", table_name="blog_comment_edits")
    op.drop_index("ix_blog_comment_edits_comment_id", table_name="blog_comment_edits")
    op.drop_table("blog_comment_edits")
    op.drop_constraint(
        "fk_blog_comments_edited_by_admin_id", "blog_comments", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_blog_comments_edited_by_user_id", "blog_comments", type_="foreignkey"
    )
    op.drop_column("blog_comments", "edited_by_admin_id")
    op.drop_column("blog_comments", "edited_by_user_id")
    op.drop_column("blog_comments", "edited_at")
