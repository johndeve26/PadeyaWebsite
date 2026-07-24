"""Seed local Pàdéyá demo content.

Usage:
  python -m scripts.seed_demo_data
  python -m scripts.seed_demo_data --reset
  python -m scripts.seed_demo_data --repair
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow `python -m scripts.seed_demo_data` from backend/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.demo.guards import DemoEnvironmentError

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
from app.sponsorships import models as sponsorships_models  # noqa: F401
from app.tickets import advanced_models as ticket_advanced_models  # noqa: F401
from app.demo import models as demo_models  # noqa: F401
from app.taxonomy import models as taxonomy_models  # noqa: F401
from app.placements import models as placements_models  # noqa: F401

from app.demo.seed import seed_demo_data


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed local Pàdéyá demo data")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Clear demo data first, then reseed",
    )
    parser.add_argument(
        "--repair",
        action="store_true",
        help="Repair partial demo data (demo-scoped rows only)",
    )
    args = parser.parse_args()

    settings = get_settings()
    if not settings.demo_mode:
        print(
            "Warning: DEMO_MODE is not true. Seeding is still allowed outside "
            "production, but enable DEMO_MODE=true for the /demo helper page."
        )

    db = SessionLocal()
    try:
        result = seed_demo_data(db, reset=args.reset, repair=args.repair)
    except DemoEnvironmentError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()

    print("Demo seed result:")
    for key, value in result.items():
        print(f"  {key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
