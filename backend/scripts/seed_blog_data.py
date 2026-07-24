"""Seed demo blog posts on Neon/local (idempotent).

Usage:
  python -m scripts.seed_blog_data
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.auth import models as auth_models  # noqa: F401
from app.blog import models as blog_models  # noqa: F401
from app.blog.seed import seed_blog_content
from app.core.database import SessionLocal
from app.users import models as user_models  # noqa: F401


def main() -> int:
    db = SessionLocal()
    try:
        result = seed_blog_content(db)
        db.commit()
    except Exception as exc:
        db.rollback()
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()

    print("Blog seed result:")
    for key, value in result.items():
        print(f"  {key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
