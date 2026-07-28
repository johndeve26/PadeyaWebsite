"""Canonical public/private object-key folder helpers."""

from __future__ import annotations

from uuid import UUID


def event_public_folder(event_id: UUID | str, media_type: str = "gallery") -> str:
    kind = (media_type or "gallery").strip().lower()
    mapping = {
        "banner": "banner",
        "mobile_banner": "banner",
        "cover": "cover",
        "gallery": "gallery",
        "teaser": "gallery",
        "sponsor": "gallery",
        "social_share": "cover",
        "other": "gallery",
    }
    leaf = mapping.get(kind, "gallery")
    return f"events/{event_id}/{leaf}"


def host_public_folder(host_id: UUID | str, media_type: str = "showcase") -> str:
    kind = (media_type or "showcase").strip().lower()
    if kind in {"avatar", "logo"}:
        leaf = "avatar"
    elif kind in {"banner", "cover", "mobile_banner", "social_share"}:
        leaf = "covers"
    elif kind in {"legacy"}:
        leaf = "legacy"
    else:
        leaf = "showcase"
    return f"hosts/{host_id}/{leaf}"


def user_public_folder(user_id: UUID | str, media_type: str = "avatar") -> str:
    """Account-level public media (shared Fan Passport + Host Legacy avatar)."""
    kind = (media_type or "avatar").strip().lower()
    leaf = "avatar" if kind in {"avatar", "logo", "profile"} else "media"
    return f"users/{user_id}/{leaf}"


def memory_public_folder(event_id: UUID | str, *, thumb: bool = False) -> str:
    base = f"memories/events/{event_id}"
    return f"{base}/thumbs" if thumb else base


def blog_public_folder(kind: str = "content") -> str:
    leaf = "covers" if kind in {"cover", "covers", "og", "social"} else "content"
    return f"blog/{leaf}"


def merch_public_folder(product_id: UUID | str, kind: str = "gallery") -> str:
    leaf = "cover" if kind in {"cover", "banner"} else "gallery"
    return f"merch/{product_id}/{leaf}"


def sponsor_public_folder(sponsor_id: UUID | str) -> str:
    return f"sponsors/{sponsor_id}"


def inbox_private_folder(thread_id: UUID | str) -> str:
    return f"inbox/{thread_id}/attachments"


def support_private_folder(case_id: UUID | str) -> str:
    return f"support/{case_id}/attachments"


def vault_private_folder(owner_id: UUID | str) -> str:
    return f"vault/{owner_id}"


def ticket_private_folder(ticket_id: UUID | str) -> str:
    return f"tickets/{ticket_id}/documents"


def export_private_folder(user_id: UUID | str) -> str:
    return f"exports/{user_id}"


def moderation_private_folder(case_id: UUID | str) -> str:
    return f"moderation/{case_id}"
