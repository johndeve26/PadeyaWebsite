"""Print the Pàdéyá media storage classification matrix.

Usage (from backend/):
  PYTHONPATH=. python scripts/report_media_storage_classification.py

Never prints credentials.
"""

from __future__ import annotations

from app.core.media import media_storage_provider


PUBLIC_ROWS = [
    ("Blog covers / OG (URL fields; no dedicated upload API)", "public-r2 / url-only"),
    ("Event covers / banners / gallery uploads", "public-r2"),
    ("Event Memories photos", "public-r2"),
    ("Host staging / public host imagery uploads", "public-r2"),
    ("Merch product imagery (via public upload staging)", "public-r2"),
    ("Sponsor logos/covers (URL fields; no dedicated upload API)", "public-r2 / url-only"),
    ("Fan Event Memories (public album contributions)", "public-r2"),
    ("Legacy / passport avatar uploads (via public staging)", "public-r2"),
]

PRIVATE_ROWS = [
    ("Inbox message attachments", "private-r2"),
    ("Support ticket attachments", "private-r2"),
    ("Vault private media / file_url", "private-r2 (keys) / reject public CDN"),
    ("Ticket PDFs", "generated in-memory (not persisted to R2)"),
    ("Private exports", "not implemented as R2 uploads"),
    ("Refund/dispute evidence", "URL-only today (not R2)"),
]

UNKNOWN_ROWS = [
    ("Payout evidence_file_url", "admin paste URL — no Padeya upload"),
    ("Blog inline editor binary upload", "not implemented (URL paste only)"),
    ("Sponsor contract/document uploads", "not implemented"),
]


def main() -> int:
    provider = media_storage_provider()
    target = "public-r2 / private-r2" if provider == "r2" else "local public + local private"
    print("Media storage classification")
    print(f"Active MEDIA_STORAGE_PROVIDER={provider} → {target}")
    print()
    print("PUBLIC")
    for feature, storage in PUBLIC_ROWS:
        print(f"  {feature:<55} {storage}")
    print()
    print("PRIVATE")
    for feature, storage in PRIVATE_ROWS:
        print(f"  {feature:<55} {storage}")
    print()
    print("UNKNOWN")
    for feature, note in UNKNOWN_ROWS:
        print(f"  {feature:<55} {note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
