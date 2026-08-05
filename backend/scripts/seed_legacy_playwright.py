"""Minimal Legacy trust hosts for local Playwright (no full demo seed)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal
from app.demo.legacy_trust_seed import seed_legacy_trust_showcase_hosts
from app.legacy.seed import seed_legacy_tiers

# Ensure ORM relationship targets are registered before Session use.
from app.auth import models as auth_models  # noqa: F401
from app.users import models as user_models  # noqa: F401
from app.hosts import models as host_models  # noqa: F401
from app.events import models as event_models  # noqa: F401
from app.payments import models as payment_models  # noqa: F401
from app.tickets import models as ticket_models  # noqa: F401
from app.checkins import models as checkin_models  # noqa: F401
from app.reviews import models as review_models  # noqa: F401
from app.legacy import models as legacy_models  # noqa: F401
from app.promos import models as promo_models  # noqa: F401
from app.crm import models as crm_models  # noqa: F401
from app.finance import models as finance_models  # noqa: F401
from app.vault import models as vault_models  # noqa: F401
from app.passport import models as passport_models  # noqa: F401
from app.messaging import models as messaging_models  # noqa: F401
from app.memories import models as memories_models  # noqa: F401
from app.analytics import models as analytics_models  # noqa: F401
from app.ai import models as ai_models  # noqa: F401


def main() -> None:
    db = SessionLocal()
    try:
        seed_legacy_tiers(db)
        slugs = seed_legacy_trust_showcase_hosts(db)
        print("Legacy trust showcase hosts:", slugs)
    finally:
        db.close()


if __name__ == "__main__":
    main()
