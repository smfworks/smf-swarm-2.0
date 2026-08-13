"""Allowlist policy for caller-supplied LLM base URLs (SSRF control)."""
from __future__ import annotations

import ipaddress
import os
import socket
import unicodedata
from urllib.parse import urlsplit, urlunsplit

_METADATA_HOSTS = frozenset(
    {
        "metadata.google.internal",
        "metadata",
        "metadata.goog",
    }
)
_METADATA_IPS = frozenset(
    {
        ipaddress.ip_address("169.254.169.254"),
        ipaddress.ip_address("fd00:ec2::254"),
    }
)


def _contains_control_characters(value: str) -> bool:
    return any(unicodedata.category(char) in {"Cc", "Cf", "Zl", "Zp"} for char in value)


def allow_private_llm_urls() -> bool:
    return os.environ.get("SMF_SWARM_LLM_ALLOW_PRIVATE", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _host_is_loopback_name(host: str) -> bool:
    return host.lower() in {"localhost", "127.0.0.1", "::1", "0:0:0:0:0:0:0:1"}


def _ip_is_metadata(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if ip in _METADATA_IPS:
        return True
    mapped = getattr(ip, "ipv4_mapped", None)
    return bool(mapped and mapped in _METADATA_IPS)


def _collect_ips(host: str, port: int) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    try:
        return [ipaddress.ip_address(host)]
    except ValueError:
        pass
    found: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return found
    for info in infos:
        addr = info[4][0]
        try:
            found.append(ipaddress.ip_address(addr))
        except ValueError:
            continue
    return found


def validate_llm_base_url(
    base_url: str,
    *,
    allow_private: bool | None = None,
) -> str:
    """Return a canonical http(s) base URL or raise ValueError.

    Always blocked: non-http(s), file://, credentials-in-URL, control characters,
    cloud metadata hosts/IPs.

    Private RFC1918 and link-local destinations are denied unless the host is
    loopback or ``SMF_SWARM_LLM_ALLOW_PRIVATE=1`` (or ``allow_private=True``).
    """
    if not base_url or not str(base_url).strip():
        raise ValueError("LLM base URL is required")
    if _contains_control_characters(base_url):
        raise ValueError("LLM base URL must not include control characters")
    if base_url != base_url.strip():
        raise ValueError("LLM base URL must not include surrounding whitespace")

    parsed = urlsplit(base_url)
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("LLM base URL must not include credentials")
    scheme = parsed.scheme.lower()
    if scheme == "file":
        raise ValueError("LLM base URL must not use the file:// scheme")
    if scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("LLM base URL must be an absolute HTTP(S) URL")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("LLM base URL must be an absolute HTTP(S) URL") from exc

    host = parsed.hostname.lower()
    if host in _METADATA_HOSTS or host.endswith(".metadata.google.internal"):
        raise ValueError("LLM base URL host is not allowed")

    if allow_private is None:
        allow_private = allow_private_llm_urls()

    default_port = 443 if scheme == "https" else 80
    for ip in _collect_ips(host, port or default_port):
        if _ip_is_metadata(ip):
            raise ValueError("LLM base URL must not target cloud metadata")
        if ip.is_loopback:
            continue
        if ip.is_link_local or ip.is_multicast or ip.is_unspecified:
            raise ValueError(
                "LLM base URL must not target link-local or special-use addresses"
            )
        if ip.is_private and not allow_private:
            raise ValueError(
                "LLM base URL must not target private addresses "
                "(set SMF_SWARM_LLM_ALLOW_PRIVATE=1 to allow)"
            )

    # Hostname that did not resolve: still reject obvious private-looking names
    # only when we have an IP literal check above. Unresolved public DNS is
    # allowed; the HTTP client will fail closed on connect.
    if _host_is_loopback_name(host):
        pass

    return urlunsplit((scheme, parsed.netloc, parsed.path.rstrip("/"), "", ""))
