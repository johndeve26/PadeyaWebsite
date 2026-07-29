"""Blog draft creation idempotency — client_creation_id."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260729_0200"
down_revision = "20260729_0150"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "blog_posts",
        sa.Column("client_creation_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        "ix_blog_posts_client_creation_id",
        "blog_posts",
        ["client_creation_id"],
        unique=False,
    )
    op.create_index(
        "uq_blog_posts_created_by_client_creation_id",
        "blog_posts",
        ["created_by", "client_creation_id"],
        unique=True,
        postgresql_where=sa.text("client_creation_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_blog_posts_created_by_client_creation_id",
        table_name="blog_posts",
    )
    op.drop_index("ix_blog_posts_client_creation_id", table_name="blog_posts")
    op.drop_column("blog_posts", "client_creation_id")
