"""Map raw SMTP exceptions to actionable admin messages."""

from __future__ import annotations

import re


def redact_smtp_error_text(
    exc: BaseException,
    *,
    username: str = "",
    password: str = "",
) -> str:
    text = str(exc)[:500]
    if password:
        text = text.replace(password, "***")
    if username:
        text = text.replace(username, "***")
    return text


def humanize_smtp_error_for_admin(
    raw: str,
    *,
    from_email: str | None = None,
    smtp_username: str | None = None,
) -> str:
    """Turn provider-specific SMTP text into operator-friendly guidance."""
    text = (raw or "").strip()
    if not text:
        return "SMTP send failed"

    lower = text.lower()
    from_blocked = (
        "not allowed" in lower and "from" in lower
    ) or "domain" in lower and "not allowed" in lower and "header" in lower

    if from_blocked:
        from_addr = (from_email or "").strip()
        user = (smtp_username or "").strip()
        parts = [
            "SMTP rejected the From address"
            + (f" ({from_addr})" if from_addr else "")
            + ".",
            "Most providers only allow sending from addresses on domains you verified, "
            "or from the same mailbox you use to log in.",
        ]
        if user and "@" in user and from_addr and user.lower() != from_addr.lower():
            parts.append(
                f"For testing, set From email to your SMTP username ({user}), save, then send again."
            )
        elif user and "@" in user:
            parts.append("Confirm From email matches your SMTP login address.")
        else:
            parts.append(
                "Update From email in Admin → Email settings to an address this SMTP account may send as."
            )
        if from_addr and "@" in from_addr:
            domain = from_addr.split("@", 1)[1].lower()
            user_domain = user.split("@", 1)[1].lower() if "@" in user else ""
            if user_domain and domain != user_domain:
                parts.append(
                    f"To send as @{domain} in production, verify that domain with your email provider "
                    "(SPF/DKIM) — not only in Pàdéyá."
                )
        return " ".join(parts) + f" Raw: {text[:220]}"

    if re.search(r"\b550\b", text) and "authentication" in lower:
        return (
            "SMTP authentication failed. Check username and password in Admin → Email settings. "
            f"Raw: {text[:220]}"
        )

    return text
