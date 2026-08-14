"""Oppositional tests: leftovers that harden PR #1 / open PR #2 do not close.

Each case is written to fail on origin/main (d17bc62) and pass after the
breaker fixes. Do not weaken these assertions to match incomplete hardening.
"""
from __future__ import annotations

import importlib.util
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from smf_swarm.app.history import RunHistory
from smf_swarm.config import DEFAULT_EVAL_BASE_URL, normalize_llm_base_url

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from smf_swarm.app.server import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("SMF_SWARM_HISTORY", str(tmp_path / "history.jsonl"))
    monkeypatch.delenv("SMF_SWARM_API_TOKEN", raising=False)
    monkeypatch.delenv("SMF_SWARM_SHARE_SECRET", raising=False)
    return TestClient(create_app())


@pytest.fixture
def auth_client(tmp_path, monkeypatch):
    monkeypatch.setenv("SMF_SWARM_HISTORY", str(tmp_path / "history-auth.jsonl"))
    monkeypatch.setenv("SMF_SWARM_API_TOKEN", "secret-token-xyz")
    monkeypatch.setenv("SMF_SWARM_SHARE_SECRET", "unit-share-secret")
    return TestClient(create_app())


def test_share_unauthenticated_forbidden_when_auth_enabled(auth_client):
    created = auth_client.post(
        "/api/analyze",
        data={"question": "Will demand grow next quarter?", "mode": "mock"},
        headers={"X-API-Key": "secret-token-xyz"},
    )
    assert created.status_code == 200, created.text
    body = created.json()
    share_id = body["share_id"]
    unsigned = auth_client.get(f"/share/{share_id}")
    assert unsigned.status_code == 403
    unsigned_api = auth_client.get(f"/api/share/{share_id}")
    assert unsigned_api.status_code == 403


def test_share_signed_query_works_when_auth_enabled(auth_client):
    created = auth_client.post(
        "/api/analyze",
        data={"question": "Will demand grow next quarter?", "mode": "mock"},
        headers={"X-API-Key": "secret-token-xyz"},
    )
    body = created.json()
    path = body["share_url_path"]
    assert "?s=" in path
    page = auth_client.get(path)
    assert page.status_code == 200
    assert "shared report" in page.text.lower() or "SMF Swarm" in page.text
    share_id = body["share_id"]
    sig = path.split("s=", 1)[1]
    api = auth_client.get(f"/api/share/{share_id}", params={"s": sig})
    assert api.status_code == 200
    dumped = api.text
    assert "signed_url_path" not in dumped
    assert "secret-token-xyz" not in dumped


def test_share_api_redacts_signed_run_url(client):
    created = client.post(
        "/api/analyze",
        data={"question": "Will demand grow next quarter?", "mode": "mock"},
    )
    body = created.json()
    assert body.get("signed_url_path")
    api = client.get(f"/api/share/{body['share_id']}")
    assert api.status_code == 200
    assert "signed_url_path" not in api.json()


def test_ipv4_mapped_metadata_url_rejected():
    with pytest.raises(ValueError, match="metadata"):
        normalize_llm_base_url("http://[::ffff:169.254.169.254]/latest/meta-data")


def test_link_local_metadata_aliases_rejected():
    with pytest.raises(ValueError, match="metadata"):
        normalize_llm_base_url("http://169.254.169.254/")
    with pytest.raises(ValueError):
        normalize_llm_base_url("http://169.254.1.1/")


def test_eval_base_url_has_no_implicit_runtime_default():
    assert not DEFAULT_EVAL_BASE_URL


def _load_compare_module():
    path = Path(__file__).resolve().parents[1] / "scripts" / "compare_mock_vs_llm.py"
    spec = importlib.util.spec_from_file_location("compare_mock_vs_llm", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_eval_harness_requires_explicit_base_url(monkeypatch):
    monkeypatch.delenv("SMF_SWARM_EVAL_BASE_URL", raising=False)
    module = _load_compare_module()
    with pytest.raises(ValueError, match="SMF_SWARM_EVAL_BASE_URL"):
        module.configured_eval_base_url()


def test_eval_harness_does_not_bind_default_at_import(monkeypatch):
    monkeypatch.delenv("SMF_SWARM_EVAL_BASE_URL", raising=False)
    module = _load_compare_module()
    assert getattr(module, "BASE_URL", "") in {"", None}


def test_history_jsonl_concurrent_appends_stay_valid(tmp_path):
    path = tmp_path / "hist.jsonl"
    hist = RunHistory(path, max_entries=80)

    def _write(idx: int) -> None:
        hist.append({"run_id": f"r{idx}", "question": f"q{idx}", "share_id": f"s{idx}"})

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(_write, range(40)))

    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    parsed = [json.loads(ln) for ln in lines]
    assert parsed
    ids = {row["run_id"] for row in parsed}
    assert ids <= {f"r{i}" for i in range(40)}
    assert len(parsed) == len(ids)


def test_history_trim_is_atomic_under_lock(tmp_path):
    path = tmp_path / "hist.jsonl"
    hist = RunHistory(path, max_entries=5)
    barrier = threading.Barrier(6)

    def _write(idx: int) -> None:
        barrier.wait()
        hist.append({"run_id": f"r{idx}", "question": "q"})

    threads = [threading.Thread(target=_write, args=(i,)) for i in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) <= 5
    for ln in lines:
        json.loads(ln)


def test_app_js_does_not_persist_api_key_in_localstorage():
    src = Path("src/smf_swarm/app/static/app.js").read_text(encoding="utf-8")
    assert "JSON.stringify(persist)" in src
    assert "sessionStorage.setItem" in src
    assert "localStorage.setItem(SETTINGS_KEY, JSON.stringify(obj" not in src
    assert "api_key: (document.getElementById(\"llmApiKey\")" in src
    # durable blob must not include the key field
    assert "persist" in src and "api_key" in src
    persist_block = src[src.index("const persist") : src.index("localStorage.setItem(SETTINGS_KEY")]
    assert "api_key" not in persist_block


def test_package_version_is_051():
    from smf_swarm import __version__

    assert __version__ == "0.5.1"


@pytest.mark.skipif(os.name != "posix", reason="fcntl locking is POSIX")
def test_history_uses_exclusive_lock():
    src = Path("src/smf_swarm/app/history.py").read_text(encoding="utf-8")
    assert "LOCK_EX" in src
    assert "fcntl" in src
