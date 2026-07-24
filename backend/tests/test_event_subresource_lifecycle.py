"""Agenda/people/questions upsert + question archive + media delete."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.events.models import (
    Event,
    EventAgendaItem,
    EventCategory,
    EventCheckoutQuestion,
    EventMedia,
    EventPerson,
    TicketType,
)
from app.hosts.models import Host
from app.payments.models import Order, OrderCheckoutAnswer
from app.users.models import User


def _auth_headers(client: TestClient, email: str) -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepass1", "full_name": "Life Host"},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _onboard(client: TestClient, headers: dict[str, str], name: str) -> None:
    response = client.post(
        "/api/v1/hosts/onboard",
        headers=headers,
        json={
            "display_name": name,
            "bio": "Lifecycle host",
            "city": "Lagos",
            "state": "Lagos",
            "country": "Nigeria",
        },
    )
    assert response.status_code == 201, response.text


def _seed_draft(db: Session, host: Host, slug: str) -> Event:
    category = db.scalar(select(EventCategory).limit(1))
    if category is None:
        category = EventCategory(name="Music", slug="music-life", is_active=True)
        db.add(category)
        db.flush()
    start = datetime.now(UTC) + timedelta(days=14)
    event = Event(
        title="Lifecycle Night",
        slug=slug,
        description="A long enough description for the event studio lifecycle tests.",
        host_id=host.id,
        category_id=category.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=4),
        status="draft",
        city="Lagos",
        state="Lagos",
    )
    db.add(event)
    db.flush()
    db.add(
        TicketType(
            event_id=event.id,
            name="GA",
            type="regular",
            price=Decimal("5000"),
            quantity=100,
            quantity_sold=0,
            quantity_reserved=0,
            status="active",
            visibility="public",
            min_per_order=1,
            max_per_order=5,
        )
    )
    db.commit()
    db.refresh(event)
    return event


def test_agenda_people_upsert_preserves_ids(client: TestClient, db_session: Session):
    headers = _auth_headers(client, "upsert@example.com")
    _onboard(client, headers, "Upsert Host")
    host = db_session.scalar(select(Host).where(Host.slug.is_not(None)))
    assert host is not None
    event = _seed_draft(db_session, host, "lifecycle-upsert")
    agenda = EventAgendaItem(
        event_id=event.id, title="Doors", type="doors_open", sort_order=0
    )
    person = EventPerson(event_id=event.id, name="DJ One", role="DJ", sort_order=0)
    db_session.add_all([agenda, person])
    db_session.commit()
    db_session.refresh(agenda)
    db_session.refresh(person)

    response = client.patch(
        f"/api/v1/events/by-id/{event.id}",
        headers=headers,
        json={
            "agenda_items": [
                {
                    "id": str(agenda.id),
                    "title": "Doors Open",
                    "type": "doors_open",
                    "sort_order": 0,
                },
                {"title": "Headliner", "type": "performance", "sort_order": 1},
            ],
            "people": [
                {
                    "id": str(person.id),
                    "name": "DJ One",
                    "role": "Headliner",
                    "sort_order": 0,
                }
            ],
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    agenda_ids = {row["id"] for row in body["agenda_items"]}
    assert str(agenda.id) in agenda_ids
    assert len(body["agenda_items"]) == 2
    assert body["people"][0]["id"] == str(person.id)
    assert body["people"][0]["role"] == "Headliner"


def test_answered_checkout_question_archives_instead_of_delete(
    client: TestClient, db_session: Session
):
    headers = _auth_headers(client, "q-archive@example.com")
    _onboard(client, headers, "Archive Q Host")
    host = db_session.scalar(
        select(Host).where(Host.display_name == "Archive Q Host")
    )
    assert host is not None
    event = _seed_draft(db_session, host, "lifecycle-q-archive")
    question = EventCheckoutQuestion(
        event_id=event.id,
        label="WhatsApp",
        type="phone",
        required=True,
        sort_order=0,
        status="active",
    )
    db_session.add(question)
    db_session.flush()

    buyer_headers = _auth_headers(client, "buyer-life@example.com")
    buyer = db_session.scalar(select(User).where(User.email == "buyer-life@example.com"))
    assert buyer is not None
    order = Order(
        reference="PDY-LIFE-TEST",
        buyer_user_id=buyer.id,
        event_id=event.id,
        status="paid",
        currency="NGN",
        subtotal_amount=Decimal("5000"),
        discount_amount=Decimal("0"),
        total_amount=Decimal("5000"),
        buyer_email=buyer.email,
        buyer_name=buyer.full_name,
    )
    db_session.add(order)
    db_session.flush()
    db_session.add(
        OrderCheckoutAnswer(
            order_id=order.id,
            question_id=question.id,
            question_label=question.label,
            question_type=question.type,
            value="+2348012345678",
        )
    )
    db_session.commit()
    db_session.refresh(question)

    response = client.patch(
        f"/api/v1/events/by-id/{event.id}",
        headers=headers,
        json={"checkout_questions": []},
    )
    assert response.status_code == 200, response.text
    db_session.expire_all()
    archived = db_session.get(EventCheckoutQuestion, question.id)
    assert archived is not None
    assert archived.status == "archived"
    assert archived.archived_at is not None

    host_view = client.get(f"/api/v1/events/by-id/{event.id}", headers=headers)
    assert host_view.status_code == 200
    statuses = {q["status"] for q in host_view.json()["checkout_questions"]}
    assert "archived" in statuses
    _ = buyer_headers


def test_delete_event_media(client: TestClient, db_session: Session):
    headers = _auth_headers(client, "media-del@example.com")
    _onboard(client, headers, "Media Del Host")
    host = db_session.scalar(
        select(Host).where(Host.display_name == "Media Del Host")
    )
    assert host is not None
    event = _seed_draft(db_session, host, "lifecycle-media-del")
    media = EventMedia(
        event_id=event.id,
        url="https://cdn.example.com/gallery-1.jpg",
        media_type="gallery",
        sort_order=0,
    )
    db_session.add(media)
    db_session.commit()
    db_session.refresh(media)

    response = client.delete(
        f"/api/v1/events/by-id/{event.id}/media/{media.id}",
        headers=headers,
    )
    assert response.status_code == 200, response.text
    assert db_session.get(EventMedia, media.id) is None


def test_restore_archived_unused_draft(client: TestClient, db_session: Session):
    headers = _auth_headers(client, "restore@example.com")
    _onboard(client, headers, "Restore Host")
    host = db_session.scalar(select(Host).where(Host.display_name == "Restore Host"))
    assert host is not None
    event = _seed_draft(db_session, host, "lifecycle-restore")
    event.status = "archived"
    db_session.commit()

    response = client.post(
        f"/api/v1/events/by-id/{event.id}/restore",
        headers=headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "draft"
