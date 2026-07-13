"""LLM settings via form fields + /api/llm/test (v0.4.1)."""
import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from smf_swarm.app.server import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("SMF_SWARM_HISTORY", str(tmp_path / "h.jsonl"))
    monkeypatch.delenv("SMF_SWARM_API_TOKEN", raising=False)
    monkeypatch.delenv("SMF_SWARM_LLM_BASE_URL", raising=False)
    return TestClient(create_app())


def test_llm_mode_requires_base_url(client):
    r = client.post(
        "/api/analyze",
        data={"question": "Will it rain?", "mode": "llm"},
    )
    assert r.status_code == 400
    assert "base URL" in r.json()["detail"]


def test_analyze_accepts_llm_form_fields_mock_still_works(client):
    # mock ignores llm fields but must accept them
    r = client.post(
        "/api/analyze",
        data={
            "question": "Outlook?",
            "mode": "mock",
            "llm_base_url": "http://example.invalid/v1",
            "llm_model": "test-model",
            "llm_api_key": "x",
        },
    )
    assert r.status_code == 200
    assert r.json()["mode"] == "mock"


def test_llm_test_requires_url(client):
    r = client.post("/api/llm/test", data={"base_url": ""})
    assert r.status_code == 400


def test_health_includes_llm_defaults(client):
    h = client.get("/api/health")
    assert "llm_defaults" in h.json()
    assert h.json()["version"].startswith("0.5")
