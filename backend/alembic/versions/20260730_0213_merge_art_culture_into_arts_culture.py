"""Merge duplicate Art & Culture into Arts & Culture.

Revision ID: 20260730_0213
Revises: 20260730_0212
Create Date: 2026-07-30

Canonical slug: arts-culture (Arts & Culture).
Legacy slug art-culture is deactivated/archived after remapping.
"""

from __future__ import annotations

from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision = "20260730_0213"
down_revision = "20260730_0212"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    keep_event = conn.execute(
        sa.text("SELECT id FROM event_categories WHERE slug = 'arts-culture' LIMIT 1")
    ).scalar()
    drop_event = conn.execute(
        sa.text("SELECT id FROM event_categories WHERE slug = 'art-culture' LIMIT 1")
    ).scalar()

    if keep_event and drop_event:
        conn.execute(
            sa.text(
                "UPDATE events SET category_id = :keep WHERE category_id = :drop"
            ),
            {"keep": keep_event, "drop": drop_event},
        )
        conn.execute(
            sa.text(
                "UPDATE events SET primary_category_id = :keep "
                "WHERE primary_category_id = :drop"
            ),
            {"keep": keep_event, "drop": drop_event},
        )
        conn.execute(
            sa.text(
                "UPDATE event_categories SET is_active = false WHERE id = :drop"
            ),
            {"drop": drop_event},
        )

    keep_tax = conn.execute(
        sa.text(
            "SELECT id FROM taxonomy_categories WHERE slug = 'arts-culture' LIMIT 1"
        )
    ).scalar()
    drop_tax = conn.execute(
        sa.text(
            "SELECT id FROM taxonomy_categories WHERE slug = 'art-culture' LIMIT 1"
        )
    ).scalar()

    if keep_tax and drop_tax:
        # Drop event links that would collide with an existing arts-culture link.
        conn.execute(
            sa.text(
                """
                DELETE FROM event_taxonomy_links AS doomed
                WHERE doomed.link_type = 'category'
                  AND doomed.taxonomy_id = :drop
                  AND EXISTS (
                    SELECT 1 FROM event_taxonomy_links AS kept
                    WHERE kept.link_type = 'category'
                      AND kept.taxonomy_id = :keep
                      AND kept.event_id = doomed.event_id
                  )
                """
            ),
            {"keep": keep_tax, "drop": drop_tax},
        )
        conn.execute(
            sa.text(
                """
                UPDATE event_taxonomy_links
                SET taxonomy_id = :keep, taxonomy_slug = 'arts-culture'
                WHERE link_type = 'category' AND taxonomy_id = :drop
                """
            ),
            {"keep": keep_tax, "drop": drop_tax},
        )

        conn.execute(
            sa.text(
                """
                DELETE FROM host_taxonomy_links AS doomed
                WHERE doomed.link_type = 'category'
                  AND doomed.taxonomy_id = :drop
                  AND EXISTS (
                    SELECT 1 FROM host_taxonomy_links AS kept
                    WHERE kept.link_type = 'category'
                      AND kept.taxonomy_id = :keep
                      AND kept.host_id = doomed.host_id
                  )
                """
            ),
            {"keep": keep_tax, "drop": drop_tax},
        )
        conn.execute(
            sa.text(
                """
                UPDATE host_taxonomy_links
                SET taxonomy_id = :keep, taxonomy_slug = 'arts-culture'
                WHERE link_type = 'category' AND taxonomy_id = :drop
                """
            ),
            {"keep": keep_tax, "drop": drop_tax},
        )

        conn.execute(
            sa.text(
                """
                UPDATE taxonomy_subcategories
                SET category_id = :keep
                WHERE category_id = :drop
                  AND NOT EXISTS (
                    SELECT 1 FROM taxonomy_subcategories AS kept
                    WHERE kept.category_id = :keep
                      AND kept.slug = taxonomy_subcategories.slug
                  )
                """
            ),
            {"keep": keep_tax, "drop": drop_tax},
        )
        conn.execute(
            sa.text(
                "DELETE FROM taxonomy_subcategories WHERE category_id = :drop"
            ),
            {"drop": drop_tax},
        )
        conn.execute(
            sa.text(
                """
                UPDATE taxonomy_categories
                SET is_active = false, archived_at = :now
                WHERE id = :drop
                """
            ),
            {"drop": drop_tax, "now": datetime.now(UTC)},
        )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "UPDATE event_categories SET is_active = true WHERE slug = 'art-culture'"
        )
    )
    conn.execute(
        sa.text(
            """
            UPDATE taxonomy_categories
            SET is_active = true, archived_at = NULL
            WHERE slug = 'art-culture'
            """
        )
    )
