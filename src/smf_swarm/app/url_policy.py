"""Allowlist checks for operator-supplied LLM base URLs."""

from __future__ import annotations

from urllib.parse import urlparse

_BLOCKED_HOSTS = {
    "169.254.169.254",
    "metadata.google.internal",
    "metadata.internal",
    "metadata",
}


class UnsafeLLMURL(ValueError):
    """Raised when an LLM base URL is not safe to fetch."""


def validate_llm_base_url(url: str) -> str:
    """Return a cleaned http(s) URL or raise UnsafeLLMURL."""
    cleaned = (url or "").strip()
    if not cleaned:
        raise UnsafeLLMURL("LLM base URL is required")
    parsed = urlparse(cleaned)
    if parsed.scheme not in ("http", "https"):
        raise UnsafeLLMURL("LLM base URL must use http or https")
    if parsed.username or parsed.password:
        raise UnsafeLLMURL("LLM base URL must not contain credentials")
    host = (parsed.hostname or "").lower()
    if not host:
        raise UnsafeLLMURL("LLM base URL host is required")
    if host in _BLOCKED_HOSTS or host.endswith(".internal"):
        raise UnsafeLLMURL("LLM base URL host is not allowed")
    if host.startswith("169.254."):
        raise UnsafeLLMURL("LLM base URL must not target link-local addresses")
    return cleaned.rstrip("/")
