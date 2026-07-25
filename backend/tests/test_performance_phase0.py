"""Phase 0 reliability/observability — request ID, timing, health/ready, errors."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.core.redis import (
    REDIS_SOCKET_CONNECT_TIMEOUT,
    REDIS_SOCKET_TIMEOUT,
    reset_redis_client_for_tests,
)
from app.core.request_context import sanitize_request_id
from app.core.timing_middleware import normalize_path, slow_label
from app.main import app


def test_sanitize_request_id_rejects_unsafe():
    assert sanitize_request_id(None) is None
    assert sanitize_request_id("") is None
    assert sanitize_request_id("a" * 100) is None
    assert sanitize_request_id("bad id with spaces") is None
    assert sanitize_request_id("../../../etc/passwd") is None
    assert sanitize_request_id("abc-123_OK.1") == "abc-123_OK.1"


def test_normalize_path_collapses_slugs():
    assert (
        normalize_path("/api/v1/events/demo-afrobeats-night-live")
        == "/api/v1/events/{slug}"
    )
    assert normalize_path("/api/v1/f/pizzlecole") == "/api/v1/f/{username}"
    assert (
        normalize_path("/api/v1/sponsors/public/korawave-pay")
        == "/api/v1/sponsors/public/{slug}"
    )


def test_slow_label_thresholds():
    assert slow_label(500) is None
    assert slow_label(1000) == "SLOW"
    assert slow_label(3000) == "VERY_SLOW"
    assert slow_label(10000) == "CRITICAL"


def test_request_id_generated(client: TestClient):
    res = client.get("/health")
    assert res.status_code == 200
    rid = res.headers.get("X-Request-ID")
    assert rid
    assert sanitize_request_id(rid) == rid


def test_request_id_preserved_when_valid(client: TestClient):
    res = client.get("/health", headers={"X-Request-ID": "audit-phase0-req-1"})
    assert res.status_code == 200
    assert res.headers.get("X-Request-ID") == "audit-phase0-req-1"


def test_request_id_rejected_when_huge(client: TestClient):
    res = client.get("/health", headers={"X-Request-ID": "x" * 200})
    assert res.status_code == 200
    rid = res.headers.get("X-Request-ID")
    assert rid
    assert rid != "x" * 200
    assert len(rid) <= 64


def test_server_timing_emitted(client: TestClient):
    res = client.get("/health")
    assert res.status_code == 200
    st = res.headers.get("Server-Timing")
    assert st
    assert "app;dur=" in st


def test_health_is_cheap_and_200(client: TestClient):
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert "database" not in body


def test_ready_db_success(client: TestClient):
    res = client.get("/ready")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ready"
    assert body["database"] == "ok"
    assert "redis" in body
    blob = str(body).lower()
    assert "password" not in blob
    assert "postgresql" not in blob
    assert "://" not in blob


def test_ready_db_failure_returns_503(client: TestClient):
    with patch("app.main.SessionLocal") as mock_session:
        mock_db = MagicMock()
        mock_db.execute.side_effect = RuntimeError("db down")
        mock_session.return_value = mock_db
        res = client.get("/ready")
    assert res.status_code == 503
    body = res.json()
    assert body["status"] == "not_ready"
    assert body["database"] == "error"


def test_http_exception_not_converted_to_500(client: TestClient):
    res = client.get("/api/v1/events/this-slug-should-not-exist-xyz")
    assert res.status_code in {404, 422}
    assert res.status_code != 500


def test_unhandled_exception_hides_traceback(db_session, db_engine):
    from app.core.database import get_db
    import app.core.database as database
    from sqlalchemy.orm import sessionmaker

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    @app.get("/__phase0_boom")
    def boom():
        raise RuntimeError("secret internals should not leak")

    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=db_engine
    )
    previous = database.SessionLocal
    database.SessionLocal = TestingSessionLocal
    app.dependency_overrides[get_db] = _override_get_db
    try:
        with TestClient(app, raise_server_exceptions=False) as c:
            res = c.get("/__phase0_boom")
        assert res.status_code == 500
        body = res.json()
        assert "Internal server error" in body["detail"]
        assert "secret internals" not in str(body)
        assert "Traceback" not in str(body)
        assert res.headers.get("X-Request-ID")
    finally:
        app.dependency_overrides.clear()
        database.SessionLocal = previous
        app.router.routes = [
            r
            for r in app.router.routes
            if getattr(r, "path", None) != "/__phase0_boom"
        ]


def test_redis_timeout_constants():
    assert 2.0 <= REDIS_SOCKET_CONNECT_TIMEOUT <= 5.0
    assert 2.0 <= REDIS_SOCKET_TIMEOUT <= 5.0


def test_redis_fail_open_returns_none(monkeypatch):
    reset_redis_client_for_tests()

    class BoomRedis:
        @staticmethod
        def from_url(*_a, **_k):
            raise ConnectionError("down")

    import sys

    monkeypatch.setitem(sys.modules, "redis", BoomRedis)
    from app.core import redis as redis_mod

    reset_redis_client_for_tests()
    assert redis_mod.get_redis() is None
    assert redis_mod.get_redis() is None
    reset_redis_client_for_tests()
