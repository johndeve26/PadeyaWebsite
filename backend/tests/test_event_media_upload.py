"""Event image upload tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient


def _auth_headers(client: TestClient, email: str) -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepass1", "full_name": "Uploader"},
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
            "display_name": "Upload Host",
            "bio": "We upload banners",
            "city": "Lagos",
            "state": "Lagos",
            "country": "Nigeria",
        },
    )
    assert response.status_code == 201, response.text


def test_host_can_upload_image_while_creating(client: TestClient):
    headers = _auth_headers(client, "upload-host@example.com")
    _onboard(client, headers)

    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
        b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    response = client.post(
        "/api/v1/events/media/upload",
        headers=headers,
        files={"file": ("banner.png", BytesIO(png), "image/png")},
        data={"media_type": "banner"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["url"].startswith("http://testserver/media/")
    assert body["media_type"] == "banner"

    # File is served from the mounted static path
    media_path = body["url"].removeprefix("http://testserver")
    served = client.get(media_path)
    assert served.status_code == 200
    assert served.content.startswith(b"\x89PNG")

    start = datetime.now(UTC) + timedelta(days=8)
    created = client.post(
        "/api/v1/events",
        headers=headers,
        json={
            "title": "Uploaded Banner Night",
            "description": "Event created with an uploaded banner image from Event Studio.",
            "start_datetime": start.isoformat(),
            "end_datetime": (start + timedelta(hours=3)).isoformat(),
            "banner_url": body["url"],
            "venue_name": "The Yard",
            "city": "Lagos",
            "state": "Lagos",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["banner_url"] == body["url"]


def test_event_media_upload_sets_banner(client: TestClient):
    headers = _auth_headers(client, "upload-event@example.com")
    _onboard(client, headers)
    start = datetime.now(UTC) + timedelta(days=9)
    event = client.post(
        "/api/v1/events",
        headers=headers,
        json={
            "title": "Attach Upload Night",
            "description": "Event that receives a direct multipart media upload.",
            "start_datetime": start.isoformat(),
            "end_datetime": (start + timedelta(hours=3)).isoformat(),
            "city": "Lagos",
        },
    ).json()

    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
        b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    response = client.post(
        f"/api/v1/events/by-id/{event['id']}/media/upload",
        headers=headers,
        files={"file": ("hero.png", BytesIO(png), "image/png")},
        data={"media_type": "banner", "set_as_banner": "true"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["banner_url"]
    assert any(m["media_type"] == "banner" for m in body["media"])


def test_rejects_non_image_upload(client: TestClient):
    headers = _auth_headers(client, "upload-bad@example.com")
    _onboard(client, headers)
    response = client.post(
        "/api/v1/events/media/upload",
        headers=headers,
        files={"file": ("notes.txt", BytesIO(b"hello"), "text/plain")},
        data={"media_type": "banner"},
    )
    assert response.status_code == 400


def teardown_module(_module):  # type: ignore[no-untyped-def]
    root = Path("media_uploads_test")
    if root.exists():
        for path in sorted(root.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink(missing_ok=True)
            elif path.is_dir():
                path.rmdir()
        root.rmdir()
