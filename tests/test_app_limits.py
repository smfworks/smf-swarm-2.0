"""Upload limit enforcement on /api/analyze."""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from smf_swarm.app.server import MAX_FILE_BYTES, MAX_FILES, create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("SMF_SWARM_HISTORY", str(tmp_path / "history.jsonl"))
    monkeypatch.delenv("SMF_SWARM_API_TOKEN", raising=False)
    return TestClient(create_app())


def test_file_too_large_is_400(client: TestClient) -> None:
    payload = b"x" * (MAX_FILE_BYTES + 1)
    r = client.post(
        "/api/analyze",
        data={"question": "Will this upload be rejected?", "mode": "mock"},
        files=[("files", ("huge.bin", payload, "application/octet-stream"))],
    )
    assert r.status_code == 400
    assert "too large" in r.json()["detail"].lower()


def test_too_many_files_is_400(client: TestClient) -> None:
    files = [
        ("files", (f"f{i}.txt", b"ok", "text/plain"))
        for i in range(MAX_FILES + 1)
    ]
    r = client.post(
        "/api/analyze",
        data={"question": "Too many attachments?", "mode": "mock"},
        files=files,
    )
    assert r.status_code == 400
    assert str(MAX_FILES) in r.json()["detail"]
