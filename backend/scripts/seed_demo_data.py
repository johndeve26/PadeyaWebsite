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


def _print_memories_summary(value: dict) -> None:
    print("Memories demo seed complete")
    food = value.get("food_and_flow") or value.get("albums", {}).get("food-and-flow")
    if isinstance(food, dict):
        print(
            "\nFood & Flow\n"
            f"Host memories: {food.get('host')}\n"
            f"Community memories: {food.get('community')}\n"
            f"Contributors: {food.get('contributors')}\n"
            f"Total: {food.get('total')}\n"
            "Cover: set\n"
            "External gallery: unset"
        )
    for album_key, stats in (value.get("albums") or {}).items():
        if album_key == "food-and-flow" or not isinstance(stats, dict):
            continue
        print(
            f"\n{album_key}\n"
            f"Total: {stats.get('total')} "
            f"(host={stats.get('host')} community={stats.get('community')})"
        )
    integrity = value.get("integrity")
    if isinstance(integrity, dict):
        print(
            f"\nIntegrity: {'OK' if integrity.get('ok') else 'FAILED'} "
            f"(demo_rows={integrity.get('demo_media_rows')} "
            f"unique_keys={integrity.get('unique_demo_keys')})"
        )
        for issue in integrity.get("issues") or []:
            print(f"  - {issue}")


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
    parser.add_argument(
        "--memories-only",
        action="store_true",
        help="Idempotent Event Memories seed only (requires existing demo events)",
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
        if args.memories_only:
            from app.demo.memories_seed import seed_memories_only

            result = seed_memories_only(db)
            print("Demo seed result:")
            print(f"  status: {result.get('status')}")
            if result.get("message"):
                print(f"  message: {result['message']}")
            _print_memories_summary(result)
            return 0 if result.get("status") == "ok" else 1

        result = seed_demo_data(db, reset=args.reset, repair=args.repair)
    except DemoEnvironmentError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()

    print("Demo seed result:")
    for key, value in result.items():
        if key == "memories" and isinstance(value, dict):
            _print_memories_summary(value)
            continue
        print(f"  {key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
