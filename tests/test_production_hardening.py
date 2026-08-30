"""Fail-closed share signing, URL policy, and upload hygiene."""

from __future__ import annotations

import hashlib
import hmac
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


def test_old_literal_share_secret_hmac_rejected(client, monkeypatch):
    """Unsigned /r/ must not accept HMAC of the retired public default."""
    monkeypatch.delenv("SMF_SWARM_SHARE_SECRET", raising=False)
    monkeypatch.delenv("SMF_SWARM_API_TOKEN", raising=False)
    run_id = "abc123"
    forged = hmac.new(
        b"smf-swarm-dev-share-secret",
        run_id.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()[:24]
    assert not verify_run_signature(run_id, forged)
    r = client.get(f"/r/{run_id}?s={forged}")
    assert r.status_code == 403


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "http://user:pass@example.com/v1",
        "http://169.254.169.254/latest/meta-data",
        "http://metadata.google.internal/computeMetadata/v1",
        "ftp://example.com/v1",
        "http://instance-data/latest/meta-data",
        "http://0xa9fea9fe/",
        "http://0.0.0.0:80/",
        "http://127.0.0.1:8888/v1?api_key=MARKER",
        "https://ollama.com/v1",
    ],
)
def test_llm_url_rejects_unsafe(url):
    with pytest.raises(UnsafeLLMURL):
        validate_llm_base_url(url)


def test_env_key_not_forwarded_to_foreign_url(monkeypatch):
    from smf_swarm.app.url_policy import env_llm_key_for

    monkeypatch.setenv("SMF_SWARM_LLM_BASE_URL", "http://127.0.0.1:8888/v1")
    monkeypatch.setenv("SMF_SWARM_LLM_API_KEY", "ENVKEY_MARKER_DO_NOT_LEAK")
    assert env_llm_key_for("http://attacker.example:9/v1", "") == ""
    assert env_llm_key_for("http://127.0.0.1:8888/v1", "") == "ENVKEY_MARKER_DO_NOT_LEAK"


def test_llm_url_accepts_http():
    assert validate_llm_base_url("http://127.0.0.1:8888/v1") == "http://127.0.0.1:8888/v1"


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "http://user:pass@example.com/v1",
        "http://169.254.169.254/",
        "http://metadata.google.internal/",
    ],
)
def test_ssrf_reject_matrix(url):
    with pytest.raises(UnsafeLLMURL):
        validate_llm_base_url(url)


def test_ssrf_allows_loopback_without_listener():
    assert validate_llm_base_url("http://127.0.0.1:9/v1") == "http://127.0.0.1:9/v1"


def test_engine_llm_requires_explicit_endpoint():
    from smf_swarm.analysis import PredictiveSwarmEngine

    with pytest.raises(ValueError, match="llm_base_url"):
        PredictiveSwarmEngine(mode="llm")
    engine = PredictiveSwarmEngine(mode="mock")
    assert "spark-56bc" not in str(engine.llm_base_url or "")


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


def test_upload_path_traversal_secret_json_is_basename_only(client):
    r = client.post(
        "/api/analyze",
        data={"question": "Will demand grow next quarter?", "mode": "mock"},
        files=[("files", ("../secret.json", b'{"k":1}\n', "application/json"))],
    )
    assert r.status_code == 200, r.text
    used = r.json().get("attachments_used") or []
    assert used == ["secret.json"]
    assert all(".." not in str(name) for name in used)


def test_upload_accepts_report_csv(client):
    r = client.post(
        "/api/analyze",
        data={"question": "Will demand grow next quarter?", "mode": "mock"},
        files=[("files", ("report.csv", b"week,n\n1,10\n2,12\n", "text/csv"))],
    )
    assert r.status_code == 200, r.text
    used = r.json().get("attachments_used") or []
    assert "report.csv" in used


@pytest.mark.skipif(os.name != "posix", reason="mode bits are POSIX-only")
def test_history_posix_perms(tmp_path):
    from smf_swarm.app.history import RunHistory

    path = tmp_path / "hist" / "history.jsonl"
    hist = RunHistory(path)
    hist.append({"run_id": "r1", "question": "q"})
    assert oct(path.stat().st_mode & 0o777) == "0o600"
    assert oct(path.parent.stat().st_mode & 0o777) == "0o700"


@pytest.mark.skipif(os.name != "posix", reason="mode bits are POSIX-only")
def test_history_posix_perms_after_analyze(tmp_path, monkeypatch):
    hist = tmp_path / "hist" / "history.jsonl"
    monkeypatch.setenv("SMF_SWARM_HISTORY", str(hist))
    monkeypatch.delenv("SMF_SWARM_API_TOKEN", raising=False)
    monkeypatch.delenv("SMF_SWARM_SHARE_SECRET", raising=False)
    client = TestClient(create_app())
    r = client.post(
        "/api/analyze",
        data={"question": "Will demand grow next quarter?", "mode": "mock"},
    )
    assert r.status_code == 200, r.text
    assert hist.is_file()
    assert oct(hist.stat().st_mode & 0o777) == "0o600"
    assert oct(hist.parent.stat().st_mode & 0o777) == "0o700"
