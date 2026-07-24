"""Block off-platform payments and contact-sharing in merch listings."""

from __future__ import annotations

import re

from fastapi import HTTPException

# Hard-block: off-platform payment, contact extraction, or banned listing copy.
_UNSAFE_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"https?://",
        r"www\.",
        r"paystack\.com",
        r"flutterwave",
        r"wa\.me",
        r"whatsapp",
        r"telegram\.me",
        r"t\.me/",
        r"\bwire\s+me\b",
        r"\bbank\s+transfer\b",
        r"\bbank\s+details\b",
        r"\baccount\s+number\b",
        r"\bpayment\s+link\b",
        r"\bsend\s+money\b",
        r"\boutside\s+padeya\b",
        r"\boutside\s+pàdéyá\b",
        r"\bmy\s+number\s+is\b",
        r"\bmy\s+phone\s+is\b",
        r"\bcall\s+me\s+on\b",
        r"\btext\s+me\s+at\b",
        r"\bemail\s+me\b",
        r"[\w.+-]+@[\w.-]+\.\w+",
        r"\b(?:\+?234|0)\d{8,12}\b",
        # Basic banned product categories (not exhaustive legal advice).
        r"\bfirearm\b",
        r"\bammunition\b",
        r"\bweapon\b",
        r"\bexplosive\b",
        r"\bnarcotic\b",
        r"\billegal\s+drug\b",
        r"\bcounterfeit\b",
        r"\bfake\s+id\b",
    )
)

_STREETISH = re.compile(
    r"\b(\d{1,5}\s+[A-Za-z]|street|st\.|road|rd\.|avenue|ave\.|close|drive|lane|estate)\b",
    re.IGNORECASE,
)


def text_contains_unsafe_content(value: str | None) -> bool:
    if not value:
        return False
    text = value.strip()
    if not text:
        return False
    return any(p.search(text) for p in _UNSAFE_PATTERNS)


def label_looks_like_street_address(
    label: str | None, *, event_address: str | None = None
) -> bool:
    if not label:
        return False
    cleaned = label.strip()
    if event_address and event_address.strip().lower() in cleaned.lower():
        return True
    return bool(_STREETISH.search(cleaned))


def assert_public_merch_copy_safe(**fields: str | None) -> None:
    """Reject listing copy that pushes buyers off Pàdéyá for payment/contact."""
    for name, value in fields.items():
        if text_contains_unsafe_content(value):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Unsafe content in {name}: keep payments and contact on Pàdéyá. "
                    "Do not include payment links, bank details, phone numbers, or emails."
                ),
            )
