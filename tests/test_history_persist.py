"""History persist failures must be visible to the client."""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from smf_swarm.app.history import RunHistory
from smf_swarm.app.server import create_app


def test_history_failure_sets_flag(tmp_path, monkeypatch):
    monkeypatch.setenv("SMF_SWARM_HISTORY", str(tmp_path / "history.jsonl"))
    monkeypatch.delenv("SMF_SWARM_API_TOKEN", raising=False)
    monkeypatch.delenv("SMF_SWARM_STRICT", raising=False)

    def boom(self, report):
        raise OSError("disk full")

    monkeypatch.setattr(RunHistory, "append", boom)
    client = TestClient(create_app())
    r = client.post(
        "/api/analyze",
        data={"question": "Will history failure be visible?", "mode": "mock"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["history_persisted"] is False


def test_history_failure_strict_is_500(tmp_path, monkeypatch):
    monkeypatch.setenv("SMF_SWARM_HISTORY", str(tmp_path / "history.jsonl"))
    monkeypatch.setenv("SMF_SWARM_STRICT", "1")
    monkeypatch.delenv("SMF_SWARM_API_TOKEN", raising=False)

    def boom(self, report):
        raise OSError("disk full")

    monkeypatch.setattr(RunHistory, "append", boom)
    client = TestClient(create_app())
    r = client.post(
        "/api/analyze",
        data={"question": "Strict history failure?", "mode": "mock"},
    )
    assert r.status_code == 500
