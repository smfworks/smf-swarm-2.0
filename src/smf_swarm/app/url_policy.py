"""Allowlist checks for operator-supplied LLM base URLs."""

from __future__ import annotations

import ipaddress
from urllib.parse import urlparse

_BLOCKED_HOSTS = {
    "169.254.169.254",
    "metadata.google.internal",
    "metadata.internal",
    "metadata",
}


class UnsafeLLMURL(ValueError):
    """Raised when an LLM base URL is not safe to fetch."""


def _host_is_blocked_ip(host: str) -> bool:
    addr = None
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        if host.isdigit():
            try:
                addr = ipaddress.IPv4Address(int(host))
            except (ValueError, OverflowError):
                return False
        else:
            return False
    if addr is None:
        return False
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None:
        addr = addr.ipv4_mapped
    if addr.is_link_local or addr.is_multicast or addr.is_reserved:
        return True
    if addr in ipaddress.ip_network("169.254.0.0/16"):
        return True
    return False


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
    if host.startswith("169.254.") or _host_is_blocked_ip(host):
        raise UnsafeLLMURL("LLM base URL must not target link-local addresses")
    return cleaned.rstrip("/")
