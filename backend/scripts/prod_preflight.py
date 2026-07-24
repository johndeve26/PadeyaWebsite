"""Production go-live preflight — read-only safety checks.

Usage (from backend/):
  PYTHONPATH=. python scripts/prod_preflight.py

Never modifies data. Never prints secrets. Safe to run on production.

Includes AI_READY (PASS/WARN/FAIL) for 24 canonical Pàdéyá Copilot features — see app.platform.ai_readiness.
"""

from __future__ import annotations

import sys

from app.core.database import SessionLocal
from app.platform.readiness import format_report_cli, run_production_readiness


def main() -> int:
    db = SessionLocal()
    try:
        report = run_production_readiness(db=db)
    finally:
        db.close()

    print(format_report_cli(report))
    return 0 if report.verdict.value == "READY_FOR_PRODUCTION" else 1


if __name__ == "__main__":
    sys.exit(main())
