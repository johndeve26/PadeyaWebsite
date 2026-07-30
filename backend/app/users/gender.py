"""Privacy-aware gender field — single authoritative policy for all serializers.

Gender is stored on ``User`` (shared across Fan Passport and host identity).
Never infer gender. Never send a hidden value for the frontend to hide.
"""

from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.users.models import User

# Host taxonomy slugs that represent orgs/venues/brands/collectives — not a person.
ORG_HOST_TYPE_SLUGS = frozenset(
    {
        "venue-operator",
        "faith-organization",
        "comedy-collective",
        "tech-community",
        "lifestyle-brand",
    }
)


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


class GenderVisibility(str, Enum):
    PUBLIC = "public"
    CONNECTIONS_ONLY = "connections_only"
    PRIVATE = "private"


GENDER_VALUES = frozenset(g.value for g in Gender)
GENDER_VISIBILITY_VALUES = frozenset(v.value for v in GenderVisibility)

GENDER_LABELS: dict[str, str] = {
    Gender.MALE.value: "Male",
    Gender.FEMALE.value: "Female",
    Gender.PREFER_NOT_TO_SAY.value: "Prefer not to say",
}

GENDER_SHORT: dict[str, str] = {
    Gender.MALE.value: "M",
    Gender.FEMALE.value: "F",
}

DEFAULT_GENDER_VISIBILITY = GenderVisibility.PUBLIC.value

HIDDEN_GENDER_PAYLOAD: dict[str, Any] = {
    "gender": None,
    "gender_short": None,
    "gender_label": None,
    "gender_visible": False,
}


def parse_gender(value: Any) -> str | None:
    """Validate an explicit gender selection. Rejects aliases and wrong types."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("gender must be male, female, or prefer_not_to_say")
    key = value.strip()
    if key == "":
        raise ValueError("gender must be male, female, or prefer_not_to_say")
    # Exact enum values only — reject Male/M/man/etc.
    if key not in GENDER_VALUES:
        raise ValueError("gender must be male, female, or prefer_not_to_say")
    return key


def parse_gender_visibility(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError(
            "gender_visibility must be public, connections_only, or private"
        )
    key = value.strip()
    if key not in GENDER_VISIBILITY_VALUES:
        raise ValueError(
            "gender_visibility must be public, connections_only, or private"
        )
    return key


def gender_label(value: str | None) -> str | None:
    if not value:
        return None
    return GENDER_LABELS.get(value)


def gender_short(value: str | None) -> str | None:
    if not value:
        return None
    return GENDER_SHORT.get(value)


def host_shows_personal_gender(host_type_slugs: list[str] | None) -> bool:
    """Personal hosts may show gender; org/venue/brand/collective hosts must not."""
    slugs = {str(s).strip().lower() for s in (host_type_slugs or []) if s}
    return not bool(slugs & ORG_HOST_TYPE_SLUGS)


def _viewer_id(viewer: User | None) -> UUID | None:
    return viewer.id if viewer is not None else None


def _is_accepted_connection(db: Session, a: UUID, b: UUID) -> bool:
    from app.fan_connect import constants as FC
    from app.fan_connect.eligibility import get_connection_pair, is_connect_blocked

    if is_connect_blocked(db, a, b):
        return False
    conn = get_connection_pair(db, a, b)
    return conn is not None and conn.status == FC.STATUS_CONNECTED


def _is_admin_user_viewer(viewer: User) -> bool:
    from app.users.service import user_has_permission

    return user_has_permission(viewer, "admin.users.view") or user_has_permission(
        viewer, "admin.full_access"
    )


def can_view_gender(
    db: Session,
    *,
    viewer: User | None,
    profile_owner: User,
    gender_visibility: str | None = None,
    relationship_context: str | None = None,
) -> bool:
    """Backend-authoritative gender visibility.

    relationship_context:
      - None / \"profile\" / \"directory\" / \"messaging\": standard rules
      - \"connect_request\": also allow connections_only for the two parties
        on an explicit direct connect request (pending or otherwise involving them)
      - \"admin\": use admin.users.view (caller must already authorize the page)
    """
    visibility = (gender_visibility or getattr(profile_owner, "gender_visibility", None)
                  or DEFAULT_GENDER_VISIBILITY)
    if visibility not in GENDER_VISIBILITY_VALUES:
        visibility = DEFAULT_GENDER_VISIBILITY

    owner_id = profile_owner.id
    vid = _viewer_id(viewer)

    if vid is not None and vid == owner_id:
        return True

    # Admins only see gender on authorized admin surfaces (explicit context),
    # not via ordinary profile/directory/messaging browsing.
    if relationship_context == "admin" and viewer is not None:
        return _is_admin_user_viewer(viewer)

    if visibility == GenderVisibility.PUBLIC.value:
        return True

    if visibility == GenderVisibility.PRIVATE.value:
        return False

    # connections_only
    if vid is None:
        return False

    if relationship_context == "connect_request":
        # Explicit direct connect-request exception (pending OK). Blocked pairs no.
        from app.fan_connect.eligibility import get_connection_pair, is_connect_blocked

        if is_connect_blocked(db, vid, owner_id):
            return False
        conn = get_connection_pair(db, vid, owner_id)
        return conn is not None

    return _is_accepted_connection(db, vid, owner_id)


def gender_display_payload(
    db: Session,
    *,
    viewer: User | None,
    profile_owner: User,
    relationship_context: str | None = None,
    include_for_org_host: bool = True,
) -> dict[str, Any]:
    """Permission-filtered gender fields. Never includes a hidden raw value."""
    if not include_for_org_host:
        return dict(HIDDEN_GENDER_PAYLOAD)

    raw = getattr(profile_owner, "gender", None)
    visibility = getattr(profile_owner, "gender_visibility", None) or DEFAULT_GENDER_VISIBILITY

    if not can_view_gender(
        db,
        viewer=viewer,
        profile_owner=profile_owner,
        gender_visibility=visibility,
        relationship_context=relationship_context,
    ):
        return dict(HIDDEN_GENDER_PAYLOAD)

    if raw not in GENDER_VALUES:
        return dict(HIDDEN_GENDER_PAYLOAD)

    return {
        "gender": raw,
        "gender_short": gender_short(raw),
        "gender_label": gender_label(raw),
        "gender_visible": True,
    }


def owner_gender_settings_payload(user: User) -> dict[str, Any]:
    """Owner/settings view — always includes selected value + visibility."""
    raw = getattr(user, "gender", None)
    visibility = getattr(user, "gender_visibility", None) or DEFAULT_GENDER_VISIBILITY
    return {
        "gender": raw if raw in GENDER_VALUES else None,
        "gender_short": gender_short(raw) if raw in GENDER_VALUES else None,
        "gender_label": gender_label(raw) if raw in GENDER_VALUES else None,
        "gender_visible": True,
        "gender_visibility": visibility
        if visibility in GENDER_VISIBILITY_VALUES
        else DEFAULT_GENDER_VISIBILITY,
    }


def public_cache_safe_gender_payload(owner: User) -> dict[str, Any]:
    """Only values safe to store in anonymous public caches (visibility=public)."""
    raw = getattr(owner, "gender", None)
    visibility = getattr(owner, "gender_visibility", None) or DEFAULT_GENDER_VISIBILITY
    if visibility != GenderVisibility.PUBLIC.value or raw not in GENDER_VALUES:
        return dict(HIDDEN_GENDER_PAYLOAD)
    if raw == Gender.PREFER_NOT_TO_SAY.value:
        # Prefer-not-to-say is a selection, but compact public badge is omitted.
        return {
            "gender": raw,
            "gender_short": None,
            "gender_label": gender_label(raw),
            "gender_visible": True,
        }
    return {
        "gender": raw,
        "gender_short": gender_short(raw),
        "gender_label": gender_label(raw),
        "gender_visible": True,
    }
