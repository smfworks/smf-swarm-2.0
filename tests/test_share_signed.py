"""Signed /r/{run_id} share links: 403 without/wrong sig, 200 with valid sig."""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from smf_swarm.app.server import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("SMF_SWARM_HISTORY", str(tmp_path / "history.jsonl"))
    monkeypatch.setenv("SMF_SWARM_SHARE_SECRET", "test-share-secret")
    monkeypatch.delenv("SMF_SWARM_API_TOKEN", raising=False)
    return TestClient(create_app())


def _analyze(client: TestClient) -> dict:
    r = client.post(
        "/api/analyze",
        data={"question": "What is the signed-share outlook?", "mode": "mock"},
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_signed_path_403_without_signature(client: TestClient) -> None:
    body = _analyze(client)
    r = client.get(f"/r/{body['run_id']}")
    assert r.status_code == 403


def test_signed_path_403_wrong_signature(client: TestClient) -> None:
    body = _analyze(client)
    r = client.get(f"/r/{body['run_id']}?s=deadbeefdeadbeefdeadbeef")
    assert r.status_code == 403


def test_signed_path_200_with_signature(client: TestClient) -> None:
    body = _analyze(client)
    r = client.get(body["signed_url_path"])
    assert r.status_code == 200
    assert body["run_id"] in r.text


def test_signed_path_403_after_secret_rotation(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("SMF_SWARM_HISTORY", str(tmp_path / "history.jsonl"))
    monkeypatch.setenv("SMF_SWARM_SHARE_SECRET", "secret-one")
    monkeypatch.delenv("SMF_SWARM_API_TOKEN", raising=False)
    client = TestClient(create_app())
    body = _analyze(client)
    path = body["signed_url_path"]
    monkeypatch.setenv("SMF_SWARM_SHARE_SECRET", "secret-two")
    assert client.get(path).status_code == 403
