"""CLI: sync Ask Pàdéyá knowledge documents from the public sitemap.

Examples:
  python -m scripts.sync_assistant_knowledge
  python -m scripts.sync_assistant_knowledge --max-urls 200
  python -m scripts.sync_assistant_knowledge --sitemap-url https://padeya.com/sitemap.xml

Requires ASSISTANT_KNOWLEDGE_SYNC_ENABLED=true (or Settings.assistant_knowledge_sync_enabled).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.assistant.knowledge.sync import sync_knowledge
from app.core.database import SessionLocal

# Register ORM models
from app.assistant import models as assistant_models  # noqa: F401
from app.auth import models as auth_models  # noqa: F401
from app.users import models as user_models  # noqa: F401


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync assistant knowledge from sitemap")
    parser.add_argument("--sitemap-url", default=None, help="Override sitemap URL")
    parser.add_argument("--max-urls", type=int, default=500, help="Max URLs to index")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        report = sync_knowledge(
            db, sitemap_url=args.sitemap_url, max_urls=args.max_urls
        )
        print(
            "Knowledge sync finished:",
            f"seen={report.urls_seen}",
            f"created={report.documents_created}",
            f"updated={report.documents_updated}",
            f"unchanged={report.documents_unchanged}",
            f"archived={report.documents_archived}",
            f"failed={report.documents_failed}",
            f"chunks={report.chunks_upserted}",
        )
        if report.errors:
            print("Errors:")
            for err in report.errors:
                print(f"  - {err}")
        return 0 if report.documents_failed == 0 or report.urls_seen > 0 else 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
