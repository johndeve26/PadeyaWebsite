"""Alembic: marketplace taxonomy image fields (categories + locations).

Revision ID: 20260730_0211
Revises: 20260729_0210
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260730_0211"
down_revision: Union[str, Sequence[str], None] = "20260729_0210"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_IMAGE_COLS = (
    ("primary_image_url", sa.String(1000), True, None),
    ("primary_image_alt", sa.String(240), True, None),
    (
        "primary_image_focal_x",
        sa.Numeric(4, 3),
        False,
        sa.text("0.500"),
    ),
    (
        "primary_image_focal_y",
        sa.Numeric(4, 3),
        False,
        sa.text("0.500"),
    ),
    ("hero_image_url", sa.String(1000), True, None),
    ("hero_image_alt", sa.String(240), True, None),
    (
        "hero_image_focal_x",
        sa.Numeric(4, 3),
        False,
        sa.text("0.500"),
    ),
    (
        "hero_image_focal_y",
        sa.Numeric(4, 3),
        False,
        sa.text("0.500"),
    ),
)


def _add_image_columns(table: str) -> None:
    for name, col_type, nullable, server_default in _IMAGE_COLS:
        kwargs: dict = {"nullable": nullable}
        if server_default is not None:
            kwargs["server_default"] = server_default
        op.add_column(table, sa.Column(name, col_type, **kwargs))


def _drop_image_columns(table: str) -> None:
    for name, *_ in reversed(_IMAGE_COLS):
        op.drop_column(table, name)


def upgrade() -> None:
    _add_image_columns("taxonomy_categories")
    op.create_check_constraint(
        "ck_taxonomy_categories_primary_focal_x",
        "taxonomy_categories",
        "primary_image_focal_x >= 0 AND primary_image_focal_x <= 1",
    )
    op.create_check_constraint(
        "ck_taxonomy_categories_primary_focal_y",
        "taxonomy_categories",
        "primary_image_focal_y >= 0 AND primary_image_focal_y <= 1",
    )
    op.create_check_constraint(
        "ck_taxonomy_categories_hero_focal_x",
        "taxonomy_categories",
        "hero_image_focal_x >= 0 AND hero_image_focal_x <= 1",
    )
    op.create_check_constraint(
        "ck_taxonomy_categories_hero_focal_y",
        "taxonomy_categories",
        "hero_image_focal_y >= 0 AND hero_image_focal_y <= 1",
    )

    _add_image_columns("locations")
    op.create_check_constraint(
        "ck_locations_primary_focal_x",
        "locations",
        "primary_image_focal_x >= 0 AND primary_image_focal_x <= 1",
    )
    op.create_check_constraint(
        "ck_locations_primary_focal_y",
        "locations",
        "primary_image_focal_y >= 0 AND primary_image_focal_y <= 1",
    )
    op.create_check_constraint(
        "ck_locations_hero_focal_x",
        "locations",
        "hero_image_focal_x >= 0 AND hero_image_focal_x <= 1",
    )
    op.create_check_constraint(
        "ck_locations_hero_focal_y",
        "locations",
        "hero_image_focal_y >= 0 AND hero_image_focal_y <= 1",
    )


def downgrade() -> None:
    for name in (
        "ck_locations_hero_focal_y",
        "ck_locations_hero_focal_x",
        "ck_locations_primary_focal_y",
        "ck_locations_primary_focal_x",
    ):
        op.drop_constraint(name, "locations", type_="check")
    _drop_image_columns("locations")

    for name in (
        "ck_taxonomy_categories_hero_focal_y",
        "ck_taxonomy_categories_hero_focal_x",
        "ck_taxonomy_categories_primary_focal_y",
        "ck_taxonomy_categories_primary_focal_x",
    ):
        op.drop_constraint(name, "taxonomy_categories", type_="check")
    _drop_image_columns("taxonomy_categories")
