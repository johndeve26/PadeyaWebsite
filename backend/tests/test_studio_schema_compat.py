"""Event Studio schema compatibility — existing tables, dual-writes, no rebuilds."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.events.models import (
    EventAgendaItem,
    EventCheckoutQuestion,
    EventMedia,
    EventPerson,
    EventTemplate,
    EventVenue,
)
from app.events.service import build_publish_checklist
from app.payments.models import OrderCheckoutAnswer
from app.taxonomy.models import TaxonomyCategory
from app.taxonomy.service import seed_taxonomy_vocab


def _auth_headers(client: TestClient, email: str) -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepass1", "full_name": "Studio Host", "gender": "prefer_not_to_say"},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _onboard(client: TestClient, headers: dict[str, str]) -> None:
    response = client.post(
        "/api/v1/hosts/onboard",
        headers=headers,
        json={
            "display_name": "Studio Schema Host",
            "bio": "We ship Event Studio events",
            "city": "Lagos",
            "state": "Lagos",
            "country": "Nigeria",
        },
    )
    assert response.status_code == 201, response.text


def test_studio_tables_exist(db_session: Session):
    names = set(inspect(db_session.bind).get_table_names())
    required = {
        "events",
        "event_venues",
        "event_media",
        "event_agenda_items",
        "event_people",
        "event_checkout_questions",
        "order_checkout_answers",
        "event_templates",
        "ticket_types",
    }
    assert required.issubset(names)
    # Intentionally absent — use event_media / computed checklist instead.
    assert "event_gallery_media" not in names
    assert "event_publish_checklists" not in names
    assert "event_checkout_answers" not in names


def test_studio_columns_nullable_for_backcompat(db_session: Session):
    cols = {c["name"] for c in inspect(db_session.bind).get_columns("events")}
    for name in (
        "short_tagline",
        "venue_type",
        "public_location_label",
        "location_id",
        "primary_category_id",
        "refund_policy_type",
        "seo_title",
        "social_share_title",
        "hashtags",
        "discoverable_keywords",
        "doors_open_datetime",
        "check_in_start_time",
    ):
        assert name in cols

    qcols = {
        c["name"]
        for c in inspect(db_session.bind).get_columns("event_checkout_questions")
    }
    assert "help_text" in qcols
    assert "status" in qcols
    assert "archived_at" in qcols

    tcols = {c["name"] for c in inspect(db_session.bind).get_columns("ticket_types")}
    for name in (
        "transfer_allowed",
        "refund_allowed",
        "access_code",
        "waitlist_enabled",
        "seats_per_unit",
        "quantity_sold",
        "quantity_reserved",
    ):
        assert name in tcols


def test_category_dual_write_and_nested_studio_payload(
    client: TestClient, db_session: Session
):
    seed_taxonomy_vocab(db_session)
    headers = _auth_headers(client, "studio-schema@example.com")
    _onboard(client, headers)

    cats = client.get("/api/v1/events/categories", headers=headers).json()
    assert cats, "expected seeded event categories"
    category_id = cats[0]["id"]
    legacy_slug = cats[0]["slug"]

    start = datetime.now(UTC) + timedelta(days=21)
    created = client.post(
        "/api/v1/events",
        headers=headers,
        json={
            "title": "Schema Compat Night",
            "description": "Verifies nested Studio models and category dual-write stay compatible.",
            "category_id": category_id,
            "start_datetime": start.isoformat(),
            "end_datetime": (start + timedelta(hours=4)).isoformat(),
            "timezone": "Africa/Lagos",
            "venue_name": "Studio Hall",
            "city": "Lagos",
            "state": "Lagos",
            "public_location_label": "Lagos Island",
            "location_visibility": "area_only",
            "refund_policy_type": "admin_controlled",
            "agenda_items": [
                {
                    "title": "Doors",
                    "type": "doors_open",
                    "start_time": start.isoformat(),
                    "sort_order": 0,
                }
            ],
            "people": [{"name": "MC Ade", "role": "Host", "sort_order": 0}],
            "checkout_questions": [
                {
                    "label": "WhatsApp",
                    "type": "phone",
                    "required": False,
                    "help_text": "For updates",
                    "sort_order": 0,
                }
            ],
            "gallery_urls": ["/demo/events/afrobeats-night-live-gallery.svg"],
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["category_id"] == category_id
    assert body.get("primary_category_id")
    assert len(body["agenda_items"]) == 1
    assert body["people"][0]["name"] == "MC Ade"
    assert body["checkout_questions"][0]["help_text"] == "For updates"
    assert body["publish_checklist"]["category_complete"] is True
    # Checklist is computed — never persisted as a table row.
    assert "id" not in body["publish_checklist"]

    tax = db_session.scalar(
        select(TaxonomyCategory).where(TaxonomyCategory.slug == legacy_slug)
    )
    assert tax is not None
    assert body["primary_category_id"] == str(tax.id)

    event_id = UUID(body["id"])
    assert db_session.scalar(
        select(EventAgendaItem).where(EventAgendaItem.event_id == event_id)
    )
    assert db_session.scalar(select(EventPerson).where(EventPerson.event_id == event_id))
    assert db_session.scalar(
        select(EventCheckoutQuestion).where(EventCheckoutQuestion.event_id == event_id)
    )
    assert db_session.scalar(
        select(EventMedia).where(
            EventMedia.event_id == event_id, EventMedia.media_type == "gallery"
        )
    )


def test_publish_checklist_is_computed_not_stored(db_session: Session):
    from app.events.models import Event

    event = Event(
        title="Computed Checklist",
        slug="computed-checklist-compat",
        description="Enough text for basics complete checks.",
        start_datetime=datetime.now(UTC) + timedelta(days=3),
        end_datetime=datetime.now(UTC) + timedelta(days=3, hours=2),
        timezone="Africa/Lagos",
        host_id=__import__("uuid").uuid4(),
        refund_policy_type="no_refunds",
        location_visibility="online_only",
        public_location_label="Online",
    )
    checklist = build_publish_checklist(event, preview_checked=False)
    assert checklist.banner_ready is True
    assert checklist.preview_checked is False
    assert checklist.ready_to_submit is False
    assert OrderCheckoutAnswer.__tablename__ == "order_checkout_answers"
    assert EventTemplate.__tablename__ == "event_templates"
    assert EventVenue.__tablename__ == "event_venues"
