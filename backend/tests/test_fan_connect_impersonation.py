"""Fan Connect must remain readable during audited impersonation."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.helpers.auth import register_json
from tests.test_impersonation import _auth_header, _register, _start, _user_id


def test_fan_connect_reads_work_under_full_impersonation(
    client: TestClient, assign_role
) -> None:
    target = _register(
        client, email="fc-imp-target@example.com", full_name="FC Target"
    ).json()
    admin = _register(client, email="fc-imp-admin@example.com").json()
    assign_role("fc-imp-admin@example.com", "super_admin")
    target_id = _user_id(client, target["access_token"])

    started = _start(
        client,
        admin_token=admin["access_token"],
        user_id=target_id,
        reason="fan connect QA",
    )
    assert started.status_code == 200, started.text
    headers = _auth_header(started.json()["access_token"])

    settings = client.get("/api/v1/fan-connect/settings", headers=headers)
    assert settings.status_code == 200, settings.text

    suggestions = client.get(
        "/api/v1/fan-connect/suggestions?limit=5&mode=mixed",
        headers=headers,
    )
    assert suggestions.status_code == 200, suggestions.text

    same_interests = client.get(
        "/api/v1/fan-connect/suggestions?limit=5&mode=same_interests",
        headers=headers,
    )
    assert same_interests.status_code == 200, same_interests.text

    incoming = client.get("/api/v1/fan-connect/requests?box=incoming", headers=headers)
    assert incoming.status_code == 200, incoming.text

    connections = client.get("/api/v1/fan-connect/connections", headers=headers)
    assert connections.status_code == 200, connections.text
