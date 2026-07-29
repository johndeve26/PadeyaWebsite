"""Blog taxonomy lifecycle — categories/tags archive, post types, media roles."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260729_0210"
down_revision = "20260729_0200"
branch_labels = None
depends_on = None

SYSTEM_POST_TYPES = [
    ("guide", "Guide", "General how-to or evergreen guide", 10),
    ("how_to", "How-to guide", "Step-by-step instructional article", 20),
    ("list_article", "List article", "Numbered or curated list format", 30),
    ("case_study", "Case study", "Real-world story with outcomes", 40),
    ("product_update", "Product update", "Platform or feature announcements", 50),
    ("news", "News analysis", "Industry news and analysis", 60),
    ("editorial", "Editorial", "Opinion or brand editorial", 70),
    ("interview", "Interview", "Q&A or conversation format", 80),
    ("comparison", "Comparison", "Compare options or approaches", 90),
    ("event_planning", "Event planning guide", "Planning a night or event", 100),
    ("venue_guide", "Venue guide", "Venue-focused guidance", 110),
    ("host_resource", "Host resource", "Resources for hosts", 120),
    ("attendee_guide", "Attendee guide", "Guidance for fans and attendees", 130),
]

CONTENT_TYPE_TO_KEY = {
    "guide": "guide",
    "How-to guide": "how_to",
    "how_to": "how_to",
    "how-to": "how_to",
    "Event planning guide": "event_planning",
    "event_planning": "event_planning",
    "Industry insight": "news",
    "industry_insight": "news",
    "Venue guide": "venue_guide",
    "venue_guide": "venue_guide",
    "Host resource": "host_resource",
    "host_resource": "host_resource",
    "Attendee guide": "attendee_guide",
    "attendee_guide": "attendee_guide",
    "Product update": "product_update",
    "product_update": "product_update",
    "Case study": "case_study",
    "case_study": "case_study",
    "List article": "list_article",
    "list_article": "list_article",
    "News analysis": "news",
    "news": "news",
    "Editorial": "editorial",
    "editorial": "editorial",
    "interview": "interview",
    "Interview": "interview",
    "comparison": "comparison",
    "Comparison": "comparison",
    "practical": "guide",
}

SYSTEM_MEDIA_ROLES = [
    ("cover", "Featured image", "Primary cover image for the post", 10, "covers", True, ["cover", "featured"]),
    ("og", "Open Graph image", "Social sharing / Open Graph image", 20, "covers", True, ["og", "social"]),
    ("inline", "Inline image", "Images inside the article body", 30, "content", True, ["inline", "block"]),
    ("gallery", "Gallery image", "Images in gallery blocks", 40, "content", False, ["gallery"]),
    ("social_share", "Social share image", "Dedicated social share creative", 50, "covers", False, ["social_share"]),
    ("teaser", "Teaser image", "Teaser or preview image", 60, "content", False, ["teaser"]),
]


def upgrade() -> None:
    op.add_column(
        "blog_categories",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.add_column(
        "blog_categories",
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "blog_categories",
        sa.Column("seo_title", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "blog_categories",
        sa.Column("seo_description", sa.String(length=320), nullable=True),
    )
    op.add_column(
        "blog_categories",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.add_column(
        "blog_tags",
        sa.Column("description", sa.Text(), nullable=True),
    )
    op.add_column(
        "blog_tags",
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "blog_tags",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.add_column(
        "blog_tags",
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "blog_tags",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_table(
        "blog_post_types",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=140), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
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
        sa.UniqueConstraint("key"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_blog_post_types_key", "blog_post_types", ["key"])
    op.create_index("ix_blog_post_types_slug", "blog_post_types", ["slug"])

    op.create_table(
        "blog_media_roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("storage_folder", sa.String(length=80), nullable=False, server_default="content"),
        sa.Column("allowed_contexts", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
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
        sa.UniqueConstraint("key"),
    )
    op.create_index("ix_blog_media_roles_key", "blog_media_roles", ["key"])

    op.create_table(
        "blog_taxonomy_slug_redirects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("resource_type", sa.String(length=32), nullable=False),
        sa.Column("old_slug", sa.String(length=140), nullable=False),
        sa.Column("new_slug", sa.String(length=140), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "resource_type",
            "old_slug",
            name="uq_blog_taxonomy_slug_redirects_type_old",
        ),
    )
    op.create_index(
        "ix_blog_taxonomy_slug_redirects_resource_type",
        "blog_taxonomy_slug_redirects",
        ["resource_type"],
    )
    op.create_index(
        "ix_blog_taxonomy_slug_redirects_old_slug",
        "blog_taxonomy_slug_redirects",
        ["old_slug"],
    )

    op.add_column(
        "blog_posts",
        sa.Column("post_type_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_blog_posts_post_type_id",
        "blog_posts",
        "blog_post_types",
        ["post_type_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_blog_posts_post_type_id", "blog_posts", ["post_type_id"])

    conn = op.get_bind()
    _seed_system_rows(conn)
    report = _migrate_content_types(conn)
    artifact = Path(__file__).resolve().parents[3] / "docs" / "blog_content_type_migration_report.json"
    try:
        artifact.write_text(json.dumps(report, indent=2), encoding="utf-8")
    except OSError:
        pass


def _seed_system_rows(conn) -> None:
    for key, name, desc, sort in SYSTEM_POST_TYPES:
        exists = conn.execute(
            sa.text("SELECT 1 FROM blog_post_types WHERE key = :key"),
            {"key": key},
        ).first()
        if exists:
            continue
        slug = name.lower().replace(" ", "-").replace("&", "").replace("/", "-")
        slug = "-".join(p for p in slug.split("-") if p)[:140] or key
        conn.execute(
            sa.text(
                """
                INSERT INTO blog_post_types
                  (id, key, name, slug, description, sort_order, is_system, is_active)
                VALUES
                  (:id, :key, :name, :slug, :description, :sort_order, true, true)
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "key": key,
                "name": name,
                "slug": slug,
                "description": desc,
                "sort_order": sort,
            },
        )

    for key, name, desc, sort, folder, required, contexts in SYSTEM_MEDIA_ROLES:
        exists = conn.execute(
            sa.text("SELECT 1 FROM blog_media_roles WHERE key = :key"),
            {"key": key},
        ).first()
        if exists:
            continue
        conn.execute(
            sa.text(
                """
                INSERT INTO blog_media_roles
                  (id, key, name, description, sort_order, is_system, is_required,
                   storage_folder, allowed_contexts, is_active)
                VALUES
                  (:id, :key, :name, :description, :sort_order, true, :is_required,
                   :storage_folder, CAST(:allowed_contexts AS jsonb), true)
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "key": key,
                "name": name,
                "description": desc,
                "sort_order": sort,
                "is_required": required,
                "storage_folder": folder,
                "allowed_contexts": json.dumps(contexts),
            },
        )


def _migrate_content_types(conn) -> dict:
    rows = conn.execute(
        sa.text(
            """
            SELECT id, studio_brief, post_type_id
            FROM blog_posts
            """
        )
    ).mappings().all()
    key_ids = {
        r[0]: r[1]
        for r in conn.execute(sa.text("SELECT key, id FROM blog_post_types")).all()
    }
    report = {"mapped": 0, "already_set": 0, "custom_created": [], "unmapped": []}
    for row in rows:
        if row["post_type_id"] is not None:
            report["already_set"] += 1
            continue
        brief = row["studio_brief"]
        if isinstance(brief, str):
            try:
                brief = json.loads(brief)
            except json.JSONDecodeError:
                brief = None
        if not isinstance(brief, dict):
            continue
        raw = brief.get("content_type")
        if not raw or not isinstance(raw, str):
            continue
        value = raw.strip()
        key = CONTENT_TYPE_TO_KEY.get(value)
        if key is None:
            norm = value.lower().replace(" ", "_").replace("-", "_")
            key = CONTENT_TYPE_TO_KEY.get(norm) or (norm if norm in key_ids else None)
        if key and key in key_ids:
            conn.execute(
                sa.text(
                    "UPDATE blog_posts SET post_type_id = :ptid WHERE id = :pid"
                ),
                {"ptid": str(key_ids[key]), "pid": str(row["id"])},
            )
            report["mapped"] += 1
            continue
        # custom term
        custom_key = (
            "".join(c if c.isalnum() or c == "_" else "_" for c in value.lower().replace(" ", "_"))
            [:64]
            or f"custom_{uuid.uuid4().hex[:8]}"
        )
        if custom_key[0].isdigit():
            custom_key = f"t_{custom_key}"
        if custom_key not in key_ids:
            new_id = uuid.uuid4()
            slug = custom_key.replace("_", "-")[:140]
            conn.execute(
                sa.text(
                    """
                    INSERT INTO blog_post_types
                      (id, key, name, slug, description, sort_order, is_system, is_active)
                    VALUES
                      (:id, :key, :name, :slug, :description, 900, false, true)
                    """
                ),
                {
                    "id": str(new_id),
                    "key": custom_key,
                    "name": value[:120],
                    "slug": slug,
                    "description": "Migrated from historical studio content_type",
                },
            )
            key_ids[custom_key] = new_id
            report["custom_created"].append({"key": custom_key, "name": value})
        conn.execute(
            sa.text("UPDATE blog_posts SET post_type_id = :ptid WHERE id = :pid"),
            {"ptid": str(key_ids[custom_key]), "pid": str(row["id"])},
        )
        report["mapped"] += 1
        report["unmapped"].append(
            {
                "post_id": str(row["id"]),
                "content_type": value,
                "mapped_to": custom_key,
            }
        )
    return report


def downgrade() -> None:
    op.drop_index("ix_blog_posts_post_type_id", table_name="blog_posts")
    op.drop_constraint("fk_blog_posts_post_type_id", "blog_posts", type_="foreignkey")
    op.drop_column("blog_posts", "post_type_id")

    op.drop_index(
        "ix_blog_taxonomy_slug_redirects_old_slug",
        table_name="blog_taxonomy_slug_redirects",
    )
    op.drop_index(
        "ix_blog_taxonomy_slug_redirects_resource_type",
        table_name="blog_taxonomy_slug_redirects",
    )
    op.drop_table("blog_taxonomy_slug_redirects")

    op.drop_index("ix_blog_media_roles_key", table_name="blog_media_roles")
    op.drop_table("blog_media_roles")

    op.drop_index("ix_blog_post_types_slug", table_name="blog_post_types")
    op.drop_index("ix_blog_post_types_key", table_name="blog_post_types")
    op.drop_table("blog_post_types")

    op.drop_column("blog_tags", "updated_at")
    op.drop_column("blog_tags", "archived_at")
    op.drop_column("blog_tags", "is_active")
    op.drop_column("blog_tags", "sort_order")
    op.drop_column("blog_tags", "description")

    op.drop_column("blog_categories", "updated_at")
    op.drop_column("blog_categories", "seo_description")
    op.drop_column("blog_categories", "seo_title")
    op.drop_column("blog_categories", "archived_at")
    op.drop_column("blog_categories", "is_active")
