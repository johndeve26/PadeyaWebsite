"""Push outbox worker CLI — safe defaults, no payload logging."""

from __future__ import annotations

import logging

from app.push.service import DrainStats
from scripts import process_push_outbox as worker_cli


def test_bare_invoke_defaults_to_loop_maintenance(monkeypatch):
    calls: list[tuple[int, bool]] = []

    def fake_run_once(*, limit: int, maintenance: bool) -> int:
        calls.append((limit, maintenance))
        raise SystemExit(0)

    monkeypatch.setattr(worker_cli, "run_once", fake_run_once)
    monkeypatch.setattr(worker_cli, "_startup_banner", lambda: None)
    monkeypatch.setattr(worker_cli.time, "sleep", lambda *_a, **_k: None)

    try:
        worker_cli.main([])
    except SystemExit:
        pass

    assert calls
    assert calls[0][1] is True  # maintenance on


def test_once_runs_single_batch(monkeypatch):
    calls: list[tuple[int, bool]] = []

    def fake_run_once(*, limit: int, maintenance: bool) -> int:
        calls.append((limit, maintenance))
        return 0

    monkeypatch.setattr(worker_cli, "run_once", fake_run_once)
    monkeypatch.setattr(worker_cli, "_startup_banner", lambda: None)

    worker_cli.main(["--once"])
    assert calls == [(worker_cli.get_settings().push_worker_batch_size or 50, False)]


def test_batch_log_has_no_payload_fields(caplog, monkeypatch):
    monkeypatch.setattr(
        worker_cli,
        "drain_push_outbox",
        lambda db, limit=50, commit=True: DrainStats(
            pending_before=1,
            attempted=1,
            sent=1,
            failed=0,
            skipped=0,
            still_pending=0,
            provider_mode="log",
            deactivated_subscriptions=0,
        ),
    )
    monkeypatch.setattr(worker_cli, "count_by_status", lambda db, status: 0)
    monkeypatch.setattr(worker_cli, "SessionLocal", lambda: _FakeSession())

    with caplog.at_level(logging.INFO, logger="padeya.push.worker_cli"):
        worker_cli.run_once(limit=10, maintenance=False)

    text = " ".join(r.message for r in caplog.records)
    assert "push_worker batch" in text
    assert "attempted=1" in text
    assert "sent=1" in text
    # Must not echo notification copy or endpoints
    assert "title=" not in text
    assert "body=" not in text
    assert "action_url" not in text
    assert "endpoint" not in text


class _FakeSession:
    def close(self) -> None:
        return None
