"""API smoke tests for the app (requires fastapi) v0.3."""
import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from smf_swarm.app.server import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("SMF_SWARM_HISTORY", str(tmp_path / "history.jsonl"))
    return TestClient(create_app())


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["version"].startswith("0.3")


def test_index(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "SMF Swarm" in r.text
    assert "Recent runs" in r.text


def test_analyze_mock_and_history(client):
    r = client.post(
        "/api/analyze",
        data={
            "question": "Will demand grow next quarter given these signals?",
            "mode": "mock",
        },
        files=[
            (
                "files",
                ("signals.csv", b"week,signups\n1,10\n2,14\n3,18\n", "text/csv"),
            )
        ],
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["prediction"]
    assert body["prediction_headline"]
    assert body["evidence"]
    assert body["methodology"]
    assert body["markdown"]
    assert body["chain_valid"] is True
    assert body["mode"] == "mock"

    h = client.get("/api/history")
    assert h.status_code == 200
    items = h.json()["items"]
    assert items
    run_id = body["run_id"]
    one = client.get(f"/api/history/{run_id}")
    assert one.status_code == 200
    md = client.get(f"/api/history/{run_id}/export.md")
    assert md.status_code == 200
    assert "Prediction" in md.text
