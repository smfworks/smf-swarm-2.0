"""API tests for charts, share links, auth (v0.4)."""
import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from smf_swarm.app.server import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("SMF_SWARM_HISTORY", str(tmp_path / "history.jsonl"))
    monkeypatch.delenv("SMF_SWARM_API_TOKEN", raising=False)
    return TestClient(create_app())


@pytest.fixture
def auth_client(tmp_path, monkeypatch):
    monkeypatch.setenv("SMF_SWARM_HISTORY", str(tmp_path / "history-auth.jsonl"))
    monkeypatch.setenv("SMF_SWARM_API_TOKEN", "secret-token-xyz")
    return TestClient(create_app())


def test_analyze_returns_charts_and_share(client):
    r = client.post(
        "/api/analyze",
        data={"question": "Will signups keep rising?", "mode": "mock"},
        files=[
            (
                "files",
                ("signals.csv", b"week,signups\n1,10\n2,14\n3,18\n4,22\n", "text/csv"),
            )
        ],
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("charts")
    assert body["charts"][0].get("sparkline_svg")
    assert body.get("share_id")
    assert body.get("share_url_path", "").startswith("/share/")

    share = client.get(body["share_url_path"])
    assert share.status_code == 200
    assert "shared report" in share.text.lower() or "SMF Swarm" in share.text

    api_share = client.get(f"/api/share/{body['share_id']}")
    assert api_share.status_code == 200
    assert api_share.json()["run_id"] == body["run_id"]


def test_auth_blocks_without_token(auth_client):
    r = auth_client.post(
        "/api/analyze",
        data={"question": "Hello?", "mode": "mock"},
    )
    assert r.status_code == 401


def test_auth_allows_with_token(auth_client):
    r = auth_client.post(
        "/api/analyze",
        data={"question": "Hello with auth?", "mode": "mock"},
        headers={"X-API-Key": "secret-token-xyz"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    # share remains public
    s = auth_client.get(body["share_url_path"])
    assert s.status_code == 200


def test_health_reports_auth_flag(auth_client):
    h = auth_client.get("/api/health")
    assert h.json()["auth_required"] is True
    assert h.json()["version"].startswith("0.4")
