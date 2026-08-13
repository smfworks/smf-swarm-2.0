"""Fail-closed share signing, URL policy, and upload hygiene."""

import os

import pytest

from smf_swarm.app.auth import (
    share_secret,
    share_signing_configured,
    sign_run_id,
    verify_run_signature,
)
from smf_swarm.app.url_policy import UnsafeLLMURL, validate_llm_base_url

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from smf_swarm.app.server import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("SMF_SWARM_HISTORY", str(tmp_path / "h.jsonl"))
    monkeypatch.delenv("SMF_SWARM_API_TOKEN", raising=False)
    monkeypatch.delenv("SMF_SWARM_SHARE_SECRET", raising=False)
    monkeypatch.delenv("SMF_SWARM_LLM_BASE_URL", raising=False)
    return TestClient(create_app())


def test_share_secret_fail_closed(monkeypatch):
    monkeypatch.delenv("SMF_SWARM_SHARE_SECRET", raising=False)
    monkeypatch.delenv("SMF_SWARM_API_TOKEN", raising=False)
    assert share_signing_configured() is False
    with pytest.raises(RuntimeError, match="not configured"):
        share_secret()


def test_share_signature_requires_configured_secret(monkeypatch):
    monkeypatch.setenv("SMF_SWARM_SHARE_SECRET", "unit-test-secret")
    assert verify_run_signature("abc123", sign_run_id("abc123"))
    assert not verify_run_signature("abc123", "deadbeef")


def test_analyze_omits_signed_path_without_secret(client):
    r = client.post("/api/analyze", data={"question": "Will demand grow?", "mode": "mock"})
    assert r.status_code == 200
    assert r.json()["signed_url_path"] is None
    assert r.json()["share_url_path"].startswith("/share/")


def test_signed_report_forbidden_without_secret(client):
    r = client.get("/r/any-run?s=deadbeef")
    assert r.status_code == 403


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "http://user:pass@example.com/v1",
        "http://169.254.169.254/latest/meta-data",
        "http://metadata.google.internal/computeMetadata/v1",
        "ftp://example.com/v1",
    ],
)
def test_llm_url_rejects_unsafe(url):
    with pytest.raises(UnsafeLLMURL):
        validate_llm_base_url(url)


def test_llm_url_accepts_http():
    assert validate_llm_base_url("http://127.0.0.1:8888/v1") == "http://127.0.0.1:8888/v1"


def test_llm_test_rejects_metadata_url(client):
    r = client.post("/api/llm/test", data={"base_url": "http://169.254.169.254/"})
    assert r.status_code == 400


def test_health_does_not_echo_base_url(client, monkeypatch):
    monkeypatch.setenv("SMF_SWARM_LLM_BASE_URL", "http://secret-lab.internal:8888/v1")
    # Recreate app so health reads env; fixture already created one — call health on new client
    from smf_swarm.app.server import create_app as _create

    h = TestClient(_create()).get("/api/health")
    body = h.json()
    dumped = str(body)
    assert "secret-lab" not in dumped
    assert "8888" not in dumped
    assert body["llm_defaults"]["has_llm_base_url"] is True
    assert "base_url" not in body["llm_defaults"]


def test_upload_rejects_exe(client):
    r = client.post(
        "/api/analyze",
        data={"question": "x?", "mode": "mock"},
        files=[("files", ("payload.exe", b"MZ", "application/octet-stream"))],
    )
    assert r.status_code == 400
    assert "extension" in r.json()["detail"]


def test_upload_strips_path(client):
    r = client.post(
        "/api/analyze",
        data={"question": "Will demand grow next quarter?", "mode": "mock"},
        files=[("files", ("../../etc/passwd.txt", b"a,b\n1,2\n", "text/plain"))],
    )
    assert r.status_code == 200
    used = r.json().get("attachments_used") or []
    assert all(".." not in str(name) for name in used)


@pytest.mark.skipif(os.name != "posix", reason="mode bits are POSIX-only")
def test_history_posix_perms(tmp_path):
    from smf_swarm.app.history import RunHistory

    path = tmp_path / "hist" / "history.jsonl"
    hist = RunHistory(path)
    hist.append({"run_id": "r1", "question": "q"})
    assert oct(path.stat().st_mode & 0o777) == "0o600"
    assert oct(path.parent.stat().st_mode & 0o777) == "0o700"
