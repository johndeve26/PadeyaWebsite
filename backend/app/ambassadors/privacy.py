"""Ambassador privacy allowlist / denylist (phase 13).

Ambassadors are promoters — never buyers, staff, or host-team members.
Serialize only aggregate attribution metrics; never buyer PII, payment refs,
QRs, venues, shipping, Fan Connect, or host-team data.
"""

from __future__ import annotations

from typing import Any

# Keys that must never appear on ambassador-facing JSON (self dashboards,
# enrollments, earnings, event promote status/link, eligible events).
FORBIDDEN_AMBASSADOR_KEYS = frozenset(
    {
        # Buyer / attendee
        "buyer_email",
        "buyer_phone",
        "buyer_user_id",
        "holder_email",
        "holder_phone",
        "attendee_email",
        "attendee_phone",
        "attendees",
        "attendee_list",
        # QRs (ticket / merch pickup — referral share QR is separate FE asset)
        "ticket_qr",
        "qr_payload",
        "qr_token",
        "pickup_qr",
        "pickup_token",
        "signed_qr",
        # Payments / orders
        "order_id",
        "order_reference",
        "payment_reference",
        "paystack_reference",
        "gateway_reference",
        "payment_intent_id",
        "dedupe_key",
        # Venue / shipping
        "address",
        "street_address",
        "venue_address",
        "hidden_venue",
        "shipping_address",
        "shipping_street",
        "shipping_phone",
        "delivery_notes",
        "maps_url",
        "meeting_url",
        "latitude",
        "longitude",
        # Fan Connect / host team
        "fan_connect",
        "connection_graph",
        "team_members",
        "host_team",
        "invite_token",
        "staff_assignments",
    }
)

# Sale / conversion line items returned to the ambassador (self).
ALLOWED_SALE_SELF_KEYS = frozenset(
    {
        "id",
        "ambassador_id",
        "tickets_sold",
        "merch_units_sold",
        "revenue_amount",
        "commission_owed",
        "commission_type",
        "hold_until",
        "status",
        "created_at",
        "event_title",
    }
)


def sale_row_for_ambassador(
    *,
    sale_id: Any,
    ambassador_id: Any,
    tickets_sold: int,
    merch_units_sold: int,
    revenue_amount: Any,
    commission_owed: Any,
    commission_type: str | None,
    hold_until: Any,
    status: str,
    created_at: Any,
    event_title: str | None,
) -> dict[str, Any]:
    """Allowlisted sale row for ambassador self dashboards."""
    row = {
        "id": sale_id,
        "ambassador_id": ambassador_id,
        "tickets_sold": tickets_sold,
        "merch_units_sold": merch_units_sold,
        "revenue_amount": revenue_amount,
        "commission_owed": commission_owed,
        "commission_type": commission_type,
        "hold_until": hold_until,
        "status": status,
        "created_at": created_at,
        "event_title": event_title,
    }
    assert set(row) <= ALLOWED_SALE_SELF_KEYS
    return row


def collect_forbidden_keys(payload: Any, *, path: str = "$") -> list[str]:
    """Return dotted paths of forbidden keys found in a nested payload."""
    found: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            key_l = str(key)
            here = f"{path}.{key_l}"
            if key_l in FORBIDDEN_AMBASSADOR_KEYS:
                found.append(here)
            found.extend(collect_forbidden_keys(value, path=here))
    elif isinstance(payload, list):
        for index, item in enumerate(payload):
            found.extend(collect_forbidden_keys(item, path=f"{path}[{index}]"))
    return found


def assert_ambassador_payload_safe(payload: Any) -> None:
    """Raise AssertionError if forbidden keys appear (tests / debug)."""
    hits = collect_forbidden_keys(payload)
    if hits:
        raise AssertionError(
            "Ambassador payload leaked forbidden keys: " + ", ".join(hits[:20])
        )
