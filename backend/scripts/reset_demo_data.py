"""Reset (clear) local Pàdéyá demo content only.

Usage:
  python -m scripts.reset_demo_data
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal
from app.demo.guards import DemoEnvironmentError

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

from app.demo.reset import reset_demo_data


def main() -> int:
    db = SessionLocal()
    try:
        counts = reset_demo_data(db)
    except DemoEnvironmentError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()

    print("Demo reset complete (demo-scoped rows only):")
    for key, value in counts.items():
        print(f"  {key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
