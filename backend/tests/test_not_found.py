"""API 404 standardization + privacy-safe public resource misses."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.http_errors import NOT_FOUND_CODE, NOT_FOUND_DETAIL, not_found_payload


def test_not_found_payload_shape():
    body = not_found_payload()
    assert body == {"detail": NOT_FOUND_DETAIL, "code": NOT_FOUND_CODE}
    assert not_found_payload("Event not found")["code"] == "NOT_FOUND"
    assert not_found_payload({"detail": "x", "code": "NOT_FOUND"})["detail"] == "x"


def test_unmatched_api_route_returns_standard_404(client: TestClient):
    res = client.get("/api/v1/this-route-does-not-exist-404-padeya")
    assert res.status_code == 404
    body = res.json()
    assert body["code"] == "NOT_FOUND"
    assert "detail" in body
    assert isinstance(body["detail"], str)
    # Must not leak stack / SQL / internal keys
    assert "traceback" not in res.text.lower()
    assert "password" not in res.text.lower()


def test_missing_public_event_is_privacy_safe(client: TestClient):
    res = client.get("/api/v1/events/definitely-missing-event-slug-xyz")
    assert res.status_code == 404
    body = res.json()
    assert body["code"] == "NOT_FOUND"
    assert body["detail"] == NOT_FOUND_DETAIL
    assert "deleted" not in body["detail"].lower()
    assert "unpublished" not in body["detail"].lower()


def test_missing_legacy_host_is_privacy_safe(client: TestClient):
    res = client.get("/api/v1/u/no-such-host-xyz/legacy")
    assert res.status_code == 404
    body = res.json()
    assert body["code"] == "NOT_FOUND"
    assert body["detail"] == NOT_FOUND_DETAIL


def test_missing_passport_is_privacy_safe(client: TestClient):
    res = client.get("/api/v1/f/no-such-fan-passport-xyz")
    assert res.status_code == 404
    body = res.json()
    assert body["code"] == "NOT_FOUND"
    assert body["detail"] == NOT_FOUND_DETAIL
