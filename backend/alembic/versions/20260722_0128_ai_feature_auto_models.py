"""Feature routes default to auto model selection (try all provider models)."""

from alembic import op

revision = "20260722_0128"
down_revision = "20260722_0127"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE ai_feature_routes
        SET primary_model = NULL,
            fallback_model = NULL
        """
    )


def downgrade() -> None:
    pass
