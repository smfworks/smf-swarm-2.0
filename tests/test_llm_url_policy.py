"""LLM URL allowlist / SSRF policy."""
from __future__ import annotations

import pytest

from smf_swarm.app.llm_url import validate_llm_base_url
from smf_swarm.logutil import safe_url_for_log


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "file://C:/Windows/win.ini",
        "ftp://127.0.0.1/v1",
        "gopher://127.0.0.1/v1",
    ],
)
def test_rejects_non_http_schemes(url: str) -> None:
    with pytest.raises(ValueError):
        validate_llm_base_url(url)


def test_rejects_embedded_credentials() -> None:
    with pytest.raises(ValueError, match="credentials"):
        validate_llm_base_url("http://user:secret@127.0.0.1:8000/v1")


@pytest.mark.parametrize(
    "url",
    [
        "http://169.254.169.254/latest/meta-data",
        "http://169.254.169.254",
        "http://metadata.google.internal/computeMetadata/v1/",
        "http://metadata/computeMetadata/v1/",
    ],
)
def test_rejects_metadata_targets(url: str) -> None:
    with pytest.raises(ValueError):
        validate_llm_base_url(url)


def test_rejects_link_local() -> None:
    with pytest.raises(ValueError):
        validate_llm_base_url("http://169.254.1.1/")


def test_default_denies_private_lan() -> None:
    with pytest.raises(ValueError, match="private"):
        validate_llm_base_url("http://10.0.0.5:8000/v1")
    with pytest.raises(ValueError, match="private"):
        validate_llm_base_url("http://192.168.1.10:8000/v1")
    with pytest.raises(ValueError, match="private"):
        validate_llm_base_url("http://172.16.0.2:8000/v1")


def test_private_allowed_when_opted_in(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMF_SWARM_LLM_ALLOW_PRIVATE", "1")
    assert validate_llm_base_url("http://10.0.0.5:8000/v1") == "http://10.0.0.5:8000/v1"


def test_allows_loopback() -> None:
    assert validate_llm_base_url("http://127.0.0.1:8000/v1") == "http://127.0.0.1:8000/v1"


def test_strips_trailing_slash() -> None:
    assert validate_llm_base_url("https://example.com/v1/") == "https://example.com/v1"


def test_safe_url_for_log_strips_userinfo() -> None:
    logged = safe_url_for_log("http://alice:super-secret@127.0.0.1:8000/v1?k=1")
    assert "super-secret" not in logged
    assert "alice" not in logged
    assert "k=1" not in logged
    assert "127.0.0.1:8000" in logged
