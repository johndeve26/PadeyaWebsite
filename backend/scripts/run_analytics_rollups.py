"""Recalculate analytics daily rollups from the raw event stream.

Safe to run repeatedly — each event×day upsert is idempotent.

Examples:
  python -m scripts.run_analytics_rollups --date-from 2026-01-01 --date-to 2026-01-31
  python -m scripts.run_analytics_rollups --last-days 7
  python -m scripts.run_analytics_rollups --last-days 1
  python -m scripts.run_analytics_rollups --last-days 7 --event-id <uuid>
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path
from uuid import UUID

# Allow `python -m scripts.run_analytics_rollups` from backend/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.analytics.rollups import run_rollups
from app.core.database import SessionLocal

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
from app.memories import models as memories_models  # noqa: F401
from app.analytics import models as analytics_models  # noqa: F401
from app.ai import models as ai_models  # noqa: F401
from app.sponsorships import models as sponsorships_models  # noqa: F401
from app.tickets import advanced_models as ticket_advanced_models  # noqa: F401
from app.demo import models as demo_models  # noqa: F401


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid date {value!r}; use YYYY-MM-DD"
        ) from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Aggregate raw analytics_events into daily rollup tables "
            "(event daily, source, ticket type, geo/device)."
        )
    )
    parser.add_argument(
        "--date-from",
        type=_parse_date,
        default=None,
        help="Inclusive start date (UTC calendar day), YYYY-MM-DD",
    )
    parser.add_argument(
        "--date-to",
        type=_parse_date,
        default=None,
        help="Inclusive end date (UTC calendar day), YYYY-MM-DD",
    )
    parser.add_argument(
        "--last-days",
        type=int,
        default=None,
        help="Recalculate the last N days including today (UTC). Overrides date-from/to.",
    )
    parser.add_argument(
        "--event-id",
        type=UUID,
        default=None,
        help="Optional: only recalculate rollups for one product event",
    )
    parser.add_argument(
        "--commit-every",
        type=int,
        default=25,
        help="Commit after this many event×day recalculations (default: 25)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.last_days is None:
        if (args.date_from is None) ^ (args.date_to is None):
            print(
                "ERROR: provide both --date-from and --date-to, or use --last-days",
                file=sys.stderr,
            )
            return 2
        if args.date_from is None and args.date_to is None:
            # Sensible default for cron: yesterday+today catch late arrivals.
            args.last_days = 2

    if args.last_days is not None and args.last_days < 1:
        print("ERROR: --last-days must be >= 1", file=sys.stderr)
        return 2

    if (
        args.last_days is None
        and args.date_from is not None
        and args.date_to is not None
        and args.date_to < args.date_from
    ):
        print("ERROR: --date-to must be on or after --date-from", file=sys.stderr)
        return 2

    db = SessionLocal()
    try:
        result = run_rollups(
            db,
            date_from=args.date_from,
            date_to=args.date_to,
            last_days=args.last_days,
            event_id=args.event_id,
            commit_every=max(0, args.commit_every),
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 — CLI surface
        print(f"ERROR: rollup failed: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()

    print("Analytics rollups complete:")
    for key, value in result.items():
        print(f"  {key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
