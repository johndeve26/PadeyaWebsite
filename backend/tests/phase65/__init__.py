"""Phase 6.5 helpers — lifecycle vs checkout boundary tests."""

from __future__ import annotations

import os

from tests.phase6.helpers import (  # noqa: F401
    ITERATIONS,
    create_user,
    login,
    pending_order,
    run_barriered,
    seed_published_event,
)

PHASE65_POSTGRES = os.environ.get("PHASE45_POSTGRES", "").strip() == "1"
