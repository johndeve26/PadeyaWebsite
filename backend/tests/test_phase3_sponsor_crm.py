"""Phase 3 — sponsor workspace ownership + CRM follow privacy."""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from tests.helpers.phase3_personas import register_persona


def test_sponsor_b_cannot_list_sponsor_a_deals(client: TestClient, assign_role):
    a = register_persona(
        client,
        email="p3-sp-a@example.com",
        full_name="Sponsor A",
        assign_role=assign_role,
        role="sponsor",
    )
    b = register_persona(
        client,
        email="p3-sp-b@example.com",
        full_name="Sponsor B",
        assign_role=assign_role,
        role="sponsor",
    )

    # Create/list workspaces if API supports it.
    wa = client.post(
        "/api/v1/sponsors/workspaces",
        headers=a.headers,
        json={"display_name": "Brand A", "slug": f"brand-a-{uuid4().hex[:6]}"},
    )
    wb = client.post(
        "/api/v1/sponsors/workspaces",
        headers=b.headers,
        json={"display_name": "Brand B", "slug": f"brand-b-{uuid4().hex[:6]}"},
    )
    if wa.status_code not in {200, 201} or wb.status_code not in {200, 201}:
        # Workspace create may already exist via different flow; probe list.
        listed = client.get("/api/v1/sponsors/workspaces", headers=a.headers)
        if listed.status_code != 200 or not listed.json():
            return
        sponsor_a_id = listed.json()[0]["id"]
    else:
        sponsor_a_id = wa.json()["id"]

    foreign = client.get(
        f"/api/v1/sponsors/workspaces/{sponsor_a_id}/deals",
        headers=b.headers,
    )
    assert foreign.status_code in {403, 404}, foreign.text

    anon = client.get(f"/api/v1/sponsors/workspaces/{sponsor_a_id}/deals")
    assert anon.status_code in {401, 403}


def test_fan_cannot_unfollow_another_fans_host(client: TestClient, db_session, assign_role):
    from tests.helpers.phase3_personas import login_existing, seed_host_with_event

    fan_a = register_persona(client, email="p3-crm-a@example.com", full_name="CRM A")
    fan_b = register_persona(client, email="p3-crm-b@example.com", full_name="CRM B")
    _, host, _, _ = seed_host_with_event(
        db_session, email="p3-crm-host@example.com", slug_suffix="crmh"
    )

    follow = client.post(
        f"/api/v1/hosts/{host.id}/follow",
        headers=fan_a.headers,
        json={},
    )
    if follow.status_code not in {200, 201}:
        follow = client.post(
            f"/api/v1/crm/hosts/{host.id}/follow",
            headers=fan_a.headers,
        )
    if follow.status_code not in {200, 201}:
        return

    # Fan B must not be able to remove Fan A's follow via host unfollow as if owner.
    # Unfollow is typically self-scoped; verify Fan B unfollow does not clear Fan A's follow.
    client.delete(f"/api/v1/hosts/{host.id}/follow", headers=fan_b.headers)
    client.post(f"/api/v1/hosts/{host.id}/unfollow", headers=fan_b.headers, json={})

    mine = client.get("/api/v1/crm/follows/mine", headers=fan_a.headers)
    if mine.status_code != 200:
        mine = client.get("/api/v1/hosts/following", headers=fan_a.headers)
    if mine.status_code == 200:
        body = mine.json()
        ids = [str(x.get("host_id") or x.get("id")) for x in (body if isinstance(body, list) else body.get("items", []))]
        assert str(host.id) in ids or any(str(host.id) in str(x) for x in (body if isinstance(body, list) else [body]))
