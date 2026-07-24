"""Run abandoned merch cart recovery (mark abandoned + one in-app reminder).

Safe to run repeatedly — one recovery per cart; per-user min gap enforced.

Examples:
  python -m scripts.run_merch_cart_recovery
  python -m scripts.run_merch_cart_recovery --limit 100
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow `python -m scripts.run_merch_cart_recovery` from backend/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal
from app.merch.cart import recover_abandoned_carts

# Ensure ORM relationship targets are registered before Session use.
from app.auth import models as auth_models  # noqa: F401
from app.users import models as user_models  # noqa: F401
from app.hosts import models as host_models  # noqa: F401
from app.events import models as event_models  # noqa: F401
from app.payments import models as payment_models  # noqa: F401
from app.tickets import models as ticket_models  # noqa: F401
from app.merch import models as merch_models  # noqa: F401
from app.messaging import models as messaging_models  # noqa: F401
from app.crm import models as crm_models  # noqa: F401


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Recover abandoned Pàdéyá merch carts: mark idle carts abandoned, "
            "send one in-app reminder (no paid-state invention)."
        )
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Max carts to process per status batch (default 50)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    db = SessionLocal()
    try:
        sent = recover_abandoned_carts(db, limit=max(1, int(args.limit)))
        print(f"merch_cart_recovery: reminders_sent={sent}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
