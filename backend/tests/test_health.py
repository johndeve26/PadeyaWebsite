"""Smoke tests for foundation health endpoints."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root() -> None:
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert "Pàdéyá" in body["message"]


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "service" in body


def test_module_health_placeholders() -> None:
    response = client.get("/api/v1/events/health")
    assert response.status_code == 200
    assert response.json()["module"] == "events"
