"""API smoke tests for the app (requires fastapi)."""
import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from smf_swarm.app.server import create_app


@pytest.fixture
def client():
    return TestClient(create_app())


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_index(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "SMF Swarm" in r.text


def test_analyze_mock(client):
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
    assert body["chain_valid"] is True
    assert body["mode"] == "mock"
