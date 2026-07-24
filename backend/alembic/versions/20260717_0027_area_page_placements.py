"""Allow area_page featured placement type.

Revision ID: 20260717_0027
Revises: 20260717_0026
Create Date: 2026-07-17
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "20260717_0027"
down_revision: Union[str, Sequence[str], None] = "20260717_0026"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_featured_placements_type", "featured_placements", type_="check"
    )
    op.create_check_constraint(
        "ck_featured_placements_type",
        "featured_placements",
        "placement_type IN ("
        "'homepage', 'events_page', 'country_page', 'state_page', "
        "'city_page', 'area_page', 'category_page', 'city_category_page')",
    )


def downgrade() -> None:
    op.execute(
        "UPDATE featured_placements SET placement_type = 'city_page' "
        "WHERE placement_type = 'area_page'"
    )
    op.drop_constraint(
        "ck_featured_placements_type", "featured_placements", type_="check"
    )
    op.create_check_constraint(
        "ck_featured_placements_type",
        "featured_placements",
        "placement_type IN ("
        "'homepage', 'events_page', 'country_page', 'state_page', "
        "'city_page', 'category_page', 'city_category_page')",
    )
