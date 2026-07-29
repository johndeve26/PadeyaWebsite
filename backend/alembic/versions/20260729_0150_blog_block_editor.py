"""Blog block editor — content_document, templates, reusable sections."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260729_0150"
down_revision = "20260729_0149"
branch_labels = None
depends_on = None

JSONB = postgresql.JSONB().with_variant(sa.JSON(), "sqlite")


def upgrade() -> None:
    op.add_column("blog_posts", sa.Column("content_document", JSONB, nullable=True))
    op.add_column(
        "blog_posts",
        sa.Column("content_document_version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "blog_posts",
        sa.Column("editor_mode", sa.String(length=32), nullable=True),
    )
    op.add_column("blog_posts", sa.Column("hero_settings", JSONB, nullable=True))
    op.add_column("blog_revisions", sa.Column("content_document", JSONB, nullable=True))
    op.add_column("blog_revisions", sa.Column("hero_settings", JSONB, nullable=True))

    op.create_table(
        "blog_layout_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("slug", sa.String(length=180), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=64), nullable=False, server_default="general"),
        sa.Column("document", JSONB, nullable=False),
        sa.Column("hero_settings", JSONB, nullable=True),
        sa.Column("is_builtin", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_blog_layout_templates_slug", "blog_layout_templates", ["slug"])

    op.create_table(
        "blog_reusable_sections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("slug", sa.String(length=180), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("section", JSONB, nullable=False),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_blog_reusable_sections_slug", "blog_reusable_sections", ["slug"])


def downgrade() -> None:
    op.drop_index("ix_blog_reusable_sections_slug", table_name="blog_reusable_sections")
    op.drop_table("blog_reusable_sections")
    op.drop_index("ix_blog_layout_templates_slug", table_name="blog_layout_templates")
    op.drop_table("blog_layout_templates")
    op.drop_column("blog_revisions", "hero_settings")
    op.drop_column("blog_revisions", "content_document")
    op.drop_column("blog_posts", "hero_settings")
    op.drop_column("blog_posts", "editor_mode")
    op.drop_column("blog_posts", "content_document_version")
    op.drop_column("blog_posts", "content_document")
