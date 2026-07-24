"""Seed rich fictional sponsor demo data for local Pàdéyá QA.

Usage (from backend/, venv active):
  DEMO_MODE=true python -m scripts.seed_sponsor_demo_data
  SPONSOR_DEMO_SEED_ENABLED=true python -m scripts.seed_sponsor_demo_data --force

Requires base demo hosts/events first:
  python -m scripts.seed_demo_data
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.auth import models as auth_models  # noqa: F401
from app.sponsorships import models as sponsorships_models  # noqa: F401
from app.sponsor_profiles.recommendations import models as rec_models  # noqa: F401
from app.users import models as user_models  # noqa: F401
from app.hosts import models as host_models  # noqa: F401
from app.events import models as event_models  # noqa: F401
from app.demo import models as demo_models  # noqa: F401

from app.core.database import SessionLocal
from app.demo.sponsor_demo_guards import SponsorDemoSeedError
from app.demo.sponsor_demo_seed import seed_rich_sponsor_demo


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Seed fictional rich sponsor demo profiles (local only)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-run and repair partial sponsor demo data",
    )
    args = parser.parse_args()

    print("Seeding fictional sponsor demo data only.", flush=True)
    print(
        "This does not run in production and does not call Paystack or send notifications.",
        flush=True,
    )

    db = SessionLocal()
    try:
        result = seed_rich_sponsor_demo(db, force=args.force)
    except SponsorDemoSeedError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()

    print("Sponsor demo seed result:")
    for key, value in result.items():
        print(f"  {key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
