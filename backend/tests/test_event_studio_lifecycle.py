"""Event Studio lifecycle: taxonomy, privacy, subresources, publish, discard."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.events.models import Event, TicketType
from app.events.service import build_publish_checklist
from app.taxonomy.models import Location, TaxonomyCategory


def _auth_headers(client: TestClient, email: str, password: str = "securepass1") -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Studio Host"},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _onboard(client: TestClient, headers: dict[str, str], name: str) -> None:
    response = client.post(
        "/api/v1/hosts/onboard",
        headers=headers,
        json={
            "display_name": name,
            "bio": "Studio lifecycle host",
            "city": "Lagos",
            "state": "Lagos",
            "country": "Nigeria",
        },
    )
    assert response.status_code == 201, response.text


def _base_payload(**overrides):
    start = datetime.now(UTC) + timedelta(days=14)
    end = start + timedelta(hours=4)
    payload = {
        "title": "Studio Lifecycle Night",
        "description": "Long enough description for Event Studio lifecycle coverage.",
        "start_datetime": start.isoformat(),
        "end_datetime": end.isoformat(),
        "timezone": "Africa/Lagos",
        "venue_name": "Courtyard Hall",
        "address": "14 Palm Close, Lekki Phase 1",
        "city": "Lagos",
        "state": "Lagos",
        "capacity": 120,
        "refund_policy_type": "admin_controlled",
        "venue": {
            "name": "Courtyard Hall",
            "address": "14 Palm Close, Lekki Phase 1",
            "city": "Lagos",
            "state": "Lagos",
            "country": "Nigeria",
        },
    }
    payload.update(overrides)
    return payload


def _admin_headers(client: TestClient, assign_role, email: str) -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepass1", "full_name": "Admin"},
    )
    assign_role(email, "super_admin")
    token = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _publish(client: TestClient, host_headers: dict[str, str], assign_role, event_id: str, admin_email: str) -> dict:
    submitted = client.post(f"/api/v1/events/by-id/{event_id}/submit", headers=host_headers)
    assert submitted.status_code == 200, submitted.text
    admin = _admin_headers(client, assign_role, admin_email)
    approved = client.post(f"/api/v1/events/by-id/{event_id}/approve", headers=admin)
    assert approved.status_code == 200, approved.text
    return approved.json()


def test_create_event_with_taxonomy_and_location(client: TestClient, db_session: Session):
    headers = _auth_headers(client, "studio-tax@example.com")
    _onboard(client, headers, "Taxonomy Studio Host")

    cats = client.get("/api/v1/events/categories").json()
    assert cats
    category_id = cats[0]["id"]
    location = db_session.scalar(
        select(Location).where(Location.kind == "area", Location.slug == "lekki")
    )
    assert location is not None
    tax = db_session.scalar(
        select(TaxonomyCategory).where(TaxonomyCategory.slug == cats[0]["slug"])
    )
    assert tax is not None

    created = client.post(
        "/api/v1/events",
        headers=headers,
        json=_base_payload(
            title="Taxonomy Wired Night",
            category_id=category_id,
            location_id=str(location.id),
            public_location_label="Lekki, Lagos",
            location_visibility="area_only",
        ),
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["category_id"] == category_id
    assert body["location_id"] == str(location.id)
    assert body["primary_category_id"] == str(tax.id)
    assert body["publish_checklist"]["category_complete"] is True
    assert body["publish_checklist"]["venue_privacy_complete"] is True


def test_update_location_privacy(client: TestClient):
    headers = _auth_headers(client, "studio-privacy-patch@example.com")
    _onboard(client, headers, "Privacy Patch Host")
    created = client.post(
        "/api/v1/events",
        headers=headers,
        json=_base_payload(
            location_visibility="full_public",
            reveal_timing="immediately",
        ),
    )
    assert created.status_code == 201, created.text
    event_id = created.json()["id"]

    patched = client.patch(
        f"/api/v1/events/by-id/{event_id}",
        headers=headers,
        json={
            "location_visibility": "hidden_until_payment",
            "reveal_timing": "after_payment",
            "reveal_note": "Exact venue revealed after purchase.",
            "public_location_label": "Lekki Phase 1, Lagos — exact venue revealed after purchase.",
        },
    )
    assert patched.status_code == 200, patched.text
    body = patched.json()
    assert body["location_visibility"] == "hidden_until_payment"
    assert body["reveal_timing"] == "after_payment"
    assert body["address"] == "14 Palm Close, Lekki Phase 1"


def test_public_api_hides_private_address_and_seo(
    client: TestClient, assign_role
):
    headers = _auth_headers(client, "studio-hide@example.com")
    _onboard(client, headers, "Hide Address Host")
    street = "14 Palm Close, Lekki Phase 1"
    created = client.post(
        "/api/v1/events",
        headers=headers,
        json=_base_payload(
            title="Private Address Night",
            location_visibility="hidden_until_payment",
            reveal_timing="after_payment",
            public_location_label="Lekki Phase 1, Lagos — exact venue revealed after purchase.",
            seo_title=f"Meet at {street}",
            seo_description=f"Party starts at {street}",
            social_share_description=f"Address: {street}",
        ),
    ).json()
    _publish(
        client,
        headers,
        assign_role,
        created["id"],
        "studio-hide-admin@example.com",
    )

    public = client.get(f"/api/v1/events/{created['slug']}").json()
    assert public["address"] is None
    assert public["location_address_revealed"] is False
    assert "Palm Close" not in (public.get("seo_title") or "")
    assert "Palm Close" not in (public.get("seo_description") or "")
    assert "Palm Close" not in (public.get("social_share_description") or "")


def test_ticket_buyer_sees_address_after_payment(
    client: TestClient, assign_role, db_session: Session
):
    headers = _auth_headers(client, "studio-buyer-host@example.com")
    _onboard(client, headers, "Buyer Reveal Host")
    created = client.post(
        "/api/v1/events",
        headers=headers,
        json=_base_payload(
            title="Buyer Reveal Night",
            location_visibility="hidden_until_payment",
            reveal_timing="after_payment",
            public_location_label="Lekki Phase 1, Lagos — exact venue revealed after purchase.",
        ),
    ).json()
    tt = client.post(
        f"/api/v1/events/by-id/{created['id']}/ticket-types",
        headers=headers,
        json={
            "name": "Free GA",
            "type": "regular",
            "price": "0",
            "quantity": 50,
            "visibility": "public",
            "status": "active",
        },
    )
    assert tt.status_code == 201, tt.text
    ticket_type_id = tt.json()["id"]
    published = _publish(
        client,
        headers,
        assign_role,
        created["id"],
        "studio-buyer-admin@example.com",
    )

    anon = client.get(f"/api/v1/events/{published['slug']}").json()
    assert anon["address"] is None

    buyer = _auth_headers(client, "studio-buyer@example.com")
    order = client.post(
        "/api/v1/orders",
        headers=buyer,
        json={
            "event_id": created["id"],
            "items": [{"ticket_type_id": ticket_type_id, "quantity": 1}],
        },
    )
    assert order.status_code == 201, order.text
    checkout = client.post(
        f"/api/v1/payments/checkout/{order.json()['id']}",
        headers=buyer,
    )
    assert checkout.status_code == 200, checkout.text
    assert checkout.json()["free_checkout"] is True

    revealed = client.get(f"/api/v1/events/{published['slug']}", headers=buyer).json()
    assert revealed["location_address_revealed"] is True
    assert revealed["address"] == "14 Palm Close, Lekki Phase 1"
    _ = db_session


def test_agenda_people_checkout_question_crud(client: TestClient):
    headers = _auth_headers(client, "studio-crud@example.com")
    _onboard(client, headers, "CRUD Studio Host")
    start = datetime.now(UTC) + timedelta(days=16)
    created = client.post(
        "/api/v1/events",
        headers=headers,
        json=_base_payload(
            title="Subresource CRUD Night",
            agenda_items=[
                {
                    "title": "Doors",
                    "type": "doors_open",
                    "start_time": start.isoformat(),
                    "sort_order": 0,
                }
            ],
            people=[{"name": "DJ One", "role": "DJ", "sort_order": 0}],
            checkout_questions=[
                {
                    "label": "WhatsApp",
                    "type": "phone",
                    "required": True,
                    "help_text": "Include country code",
                    "sort_order": 0,
                }
            ],
        ),
    )
    assert created.status_code == 201, created.text
    body = created.json()
    agenda_id = body["agenda_items"][0]["id"]
    person_id = body["people"][0]["id"]
    question_id = body["checkout_questions"][0]["id"]

    updated = client.patch(
        f"/api/v1/events/by-id/{body['id']}",
        headers=headers,
        json={
            "agenda_items": [
                {
                    "id": agenda_id,
                    "title": "Doors Open",
                    "type": "doors_open",
                    "start_time": start.isoformat(),
                    "sort_order": 0,
                },
                {
                    "title": "Headliner",
                    "type": "performance",
                    "start_time": (start + timedelta(hours=1)).isoformat(),
                    "sort_order": 1,
                },
            ],
            "people": [
                {
                    "id": person_id,
                    "name": "DJ One",
                    "role": "Headliner",
                    "sort_order": 0,
                },
                {"name": "MC Ade", "role": "Host", "sort_order": 1},
            ],
            "checkout_questions": [
                {
                    "id": question_id,
                    "label": "WhatsApp number",
                    "type": "phone",
                    "required": True,
                    "help_text": "NG format",
                    "sort_order": 0,
                },
                {
                    "label": "Meal preference",
                    "type": "dropdown",
                    "required": False,
                    "options": ["Vegan", "Meat"],
                    "sort_order": 1,
                },
            ],
        },
    )
    assert updated.status_code == 200, updated.text
    out = updated.json()
    assert len(out["agenda_items"]) == 2
    assert out["agenda_items"][0]["id"] == agenda_id
    assert out["agenda_items"][0]["title"] == "Doors Open"
    assert len(out["people"]) == 2
    assert out["people"][0]["role"] == "Headliner"
    assert out["checkout_questions"][0]["label"] == "WhatsApp number"
    assert len(out["checkout_questions"]) == 2

    # Unused questions/agenda/people can be removed via sync (hard-delete path).
    cleared = client.patch(
        f"/api/v1/events/by-id/{body['id']}",
        headers=headers,
        json={
            "agenda_items": [
                {
                    "id": agenda_id,
                    "title": "Doors Open",
                    "type": "doors_open",
                    "sort_order": 0,
                }
            ],
            "people": [
                {
                    "id": person_id,
                    "name": "DJ One",
                    "role": "Headliner",
                    "sort_order": 0,
                }
            ],
            "checkout_questions": [
                {
                    "id": question_id,
                    "label": "WhatsApp number",
                    "type": "phone",
                    "required": True,
                    "sort_order": 0,
                }
            ],
        },
    )
    assert cleared.status_code == 200, cleared.text
    slim = cleared.json()
    assert len(slim["agenda_items"]) == 1
    assert len(slim["people"]) == 1
    assert len(slim["checkout_questions"]) == 1


def test_ticket_type_deactivate_vs_delete_with_sales(
    client: TestClient, db_session: Session
):
    headers = _auth_headers(client, "studio-tt@example.com")
    _onboard(client, headers, "Ticket Rules Host")
    event = client.post(
        "/api/v1/events",
        headers=headers,
        json=_base_payload(title="Ticket Rules Night"),
    ).json()

    unused = client.post(
        f"/api/v1/events/by-id/{event['id']}/ticket-types",
        headers=headers,
        json={
            "name": "Unused",
            "type": "regular",
            "price": "3000",
            "quantity": 40,
            "visibility": "public",
            "status": "active",
        },
    ).json()
    sold = client.post(
        f"/api/v1/events/by-id/{event['id']}/ticket-types",
        headers=headers,
        json={
            "name": "Sold",
            "type": "regular",
            "price": "5000",
            "quantity": 40,
            "visibility": "public",
            "status": "active",
        },
    ).json()

    tt_sold = db_session.get(TicketType, UUID(sold["id"]))
    assert tt_sold is not None
    tt_sold.quantity_sold = 2
    db_session.commit()

    deactivated = client.post(
        f"/api/v1/events/by-id/{event['id']}/ticket-types/{sold['id']}/deactivate",
        headers=headers,
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["status"] == "inactive"

    blocked = client.delete(
        f"/api/v1/events/by-id/{event['id']}/ticket-types/{sold['id']}",
        headers=headers,
    )
    assert blocked.status_code == 400
    assert "deactivate" in blocked.json()["detail"].lower()

    deleted = client.delete(
        f"/api/v1/events/by-id/{event['id']}/ticket-types/{unused['id']}",
        headers=headers,
    )
    assert deleted.status_code == 200


def test_publish_checklist_and_submit_for_review(client: TestClient, db_session: Session):
    headers = _auth_headers(client, "studio-publish@example.com")
    _onboard(client, headers, "Publish Checklist Host")
    cats = client.get("/api/v1/events/categories").json()
    created = client.post(
        "/api/v1/events",
        headers=headers,
        json=_base_payload(
            title="Checklist Night",
            category_id=cats[0]["id"],
            seo_title="Checklist Night | Pàdéyá",
            seo_description="Get tickets for Checklist Night on Pàdéyá.",
        ),
    )
    assert created.status_code == 201, created.text
    body = created.json()
    checklist = body["publish_checklist"]
    assert checklist["basics_complete"] is True
    assert checklist["category_complete"] is True
    assert checklist["has_ticket_type"] is False
    assert checklist["preview_checked"] is False
    assert checklist["ready_to_submit"] is False

    client.post(
        f"/api/v1/events/by-id/{body['id']}/ticket-types",
        headers=headers,
        json={
            "name": "GA",
            "type": "regular",
            "price": "4000",
            "quantity": 80,
            "visibility": "public",
            "status": "active",
        },
    )
    refreshed = client.get(f"/api/v1/events/by-id/{body['id']}", headers=headers).json()
    assert refreshed["publish_checklist"]["has_ticket_type"] is True
    assert refreshed["publish_checklist"]["ready_to_submit"] is False

    # Preview is a client-side gate; service readiness includes it.
    event_row = db_session.scalar(
        select(Event)
        .options(selectinload(Event.ticket_types), selectinload(Event.venue))
        .where(Event.id == UUID(body["id"]))
    )
    assert event_row is not None
    ready = build_publish_checklist(event_row, preview_checked=True)
    assert ready.has_ticket_type is True
    assert ready.ready_to_submit is True

    submitted = client.post(
        f"/api/v1/events/by-id/{body['id']}/submit",
        headers=headers,
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["status"] == "pending_review"


def test_delete_draft_event(client: TestClient):
    headers = _auth_headers(client, "studio-discard@example.com")
    _onboard(client, headers, "Discard Draft Host")
    draft = client.post(
        "/api/v1/events",
        headers=headers,
        json=_base_payload(title="Discard Me"),
    ).json()

    deleted = client.delete(f"/api/v1/events/by-id/{draft['id']}", headers=headers)
    assert deleted.status_code == 200
    missing = client.get(f"/api/v1/events/by-id/{draft['id']}", headers=headers)
    assert missing.status_code == 404


def test_block_hard_delete_event_with_ticket_sales(
    client: TestClient, db_session: Session
):
    headers = _auth_headers(client, "studio-block-del@example.com")
    _onboard(client, headers, "Block Delete Host")
    draft = client.post(
        "/api/v1/events",
        headers=headers,
        json=_base_payload(title="Has Sales Draft"),
    ).json()
    tt = client.post(
        f"/api/v1/events/by-id/{draft['id']}/ticket-types",
        headers=headers,
        json={
            "name": "GA",
            "type": "regular",
            "price": "5000",
            "quantity": 20,
            "visibility": "public",
            "status": "active",
        },
    ).json()
    row = db_session.get(TicketType, UUID(tt["id"]))
    assert row is not None
    row.quantity_sold = 1
    db_session.commit()

    blocked = client.delete(f"/api/v1/events/by-id/{draft['id']}", headers=headers)
    assert blocked.status_code == 400
    assert "ticket sales" in blocked.json()["detail"].lower()

    still = client.get(f"/api/v1/events/by-id/{draft['id']}", headers=headers)
    assert still.status_code == 200


def test_checkout_question_validation_required(client: TestClient, assign_role):
    headers = _auth_headers(client, "studio-q-host@example.com")
    _onboard(client, headers, "Question Validation Host")
    created = client.post(
        "/api/v1/events",
        headers=headers,
        json=_base_payload(
            title="Question Validation Night",
            checkout_questions=[
                {
                    "label": "Dietary needs",
                    "type": "short_text",
                    "required": True,
                    "sort_order": 0,
                }
            ],
        ),
    ).json()
    tt = client.post(
        f"/api/v1/events/by-id/{created['id']}/ticket-types",
        headers=headers,
        json={
            "name": "GA",
            "type": "regular",
            "price": "0",
            "quantity": 30,
            "visibility": "public",
            "status": "active",
        },
    ).json()
    published = _publish(
        client,
        headers,
        assign_role,
        created["id"],
        "studio-q-admin@example.com",
    )
    question_id = published["checkout_questions"][0]["id"]

    buyer = _auth_headers(client, "studio-q-buyer@example.com")
    missing = client.post(
        "/api/v1/orders",
        headers=buyer,
        json={
            "event_id": created["id"],
            "items": [{"ticket_type_id": tt["id"], "quantity": 1}],
        },
    )
    assert missing.status_code == 400
    assert "Dietary" in missing.json()["detail"]

    ok = client.post(
        "/api/v1/orders",
        headers=buyer,
        json={
            "event_id": created["id"],
            "items": [{"ticket_type_id": tt["id"], "quantity": 1}],
            "checkout_answers": [
                {"question_id": question_id, "value": "Vegetarian"},
            ],
        },
    )
    assert ok.status_code == 201, ok.text
    assert ok.json()["checkout_answers"][0]["value"] == "Vegetarian"
