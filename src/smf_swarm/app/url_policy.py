"""Allowlist checks for operator-supplied LLM base URLs."""

from __future__ import annotations

import ipaddress
from urllib.parse import urlparse, urlunsplit

_BLOCKED_HOSTS = {
    "169.254.169.254",
    "metadata.google.internal",
    "metadata.internal",
    "metadata",
    "instance-data",
    "metadata.nicob.net",
    "ollama.com",
    "api.ollama.com",
}


class UnsafeLLMURL(ValueError):
    """Raised when an LLM base URL is not safe to fetch."""


def _host_ip(host: str):
    try:
        return ipaddress.ip_address(host)
    except ValueError:
        pass
    if host.startswith("0x") or host.isdigit():
        try:
            return ipaddress.IPv4Address(int(host, 0))
        except (ValueError, OverflowError):
            return None
    return None


def validate_llm_base_url(url: str) -> str:
    """Return a cleaned http(s) URL or raise UnsafeLLMURL."""
    cleaned = (url or "").strip()
    if not cleaned:
        raise UnsafeLLMURL("LLM base URL is required")
    if any(ord(ch) < 32 for ch in cleaned) or "?" in cleaned or "#" in cleaned:
        raise UnsafeLLMURL("LLM base URL must not contain query, fragment, or controls")
    parsed = urlparse(cleaned)
    if parsed.scheme not in ("http", "https"):
        raise UnsafeLLMURL("LLM base URL must use http or https")
    if parsed.username or parsed.password:
        raise UnsafeLLMURL("LLM base URL must not contain credentials")
    host = (parsed.hostname or "").lower()
    if not host:
        raise UnsafeLLMURL("LLM base URL host is required")
    if host in _BLOCKED_HOSTS or host.endswith(".internal") or host.endswith(".ollama.com"):
        raise UnsafeLLMURL("LLM base URL host is not allowed (metadata or blocked provider)")
    ip = _host_ip(host)
    if ip is not None:
        mapped = getattr(ip, "ipv4_mapped", None)
        if mapped is not None:
            ip = mapped
        if (
            ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
            or ip in ipaddress.ip_network("169.254.0.0/16")
        ):
            raise UnsafeLLMURL("LLM base URL must not target metadata or unspecified addresses")
    return urlunsplit((parsed.scheme, parsed.netloc.lower(), parsed.path.rstrip("/") or "", "", ""))


def env_llm_key_for(caller_url: str, caller_key: str = "") -> str:
    """Attach SMF_SWARM_LLM_API_KEY only when the caller URL is the configured origin."""
    import os

    supplied = (caller_key or "").strip()
    if supplied:
        return supplied
    env_url = (os.environ.get("SMF_SWARM_LLM_BASE_URL") or "").strip()
    env_key = (os.environ.get("SMF_SWARM_LLM_API_KEY") or "").strip()
    if not env_url or not env_key:
        return ""
    try:
        if validate_llm_base_url(caller_url) == validate_llm_base_url(env_url):
            return env_key
    except UnsafeLLMURL:
        return ""
    return ""
