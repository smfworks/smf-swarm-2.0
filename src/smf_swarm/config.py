"""Environment, URL, and model validation for SMF Swarm.

Shared by the app, engine, CLI, and eval harness so production paths
cannot silently target lab hosts or accept tainted LLM endpoints.
"""
from __future__ import annotations

import ipaddress
import logging
import os
import unicodedata
from pathlib import Path
from typing import Optional
from urllib.parse import urlsplit, urlunsplit

MAX_MODEL_ID_LENGTH = 256
MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_FILES = 8
MAX_QUESTION_CHARS = 8000

DEFAULT_EVAL_BASE_URL = "http://127.0.0.1:8888/v1"

_METADATA_HOSTS = frozenset(
    {
        "metadata.google.internal",
        "metadata.goog",
        "metadata",
        "169.254.169.254",
        "fd00:ec2::254",
    }
)
_METADATA_IPS = frozenset(
    {
        ipaddress.ip_address("169.254.169.254"),
        ipaddress.ip_address("fd00:ec2::254"),
        ipaddress.ip_address("100.100.100.200"),
    }
)

logger = logging.getLogger("smf_swarm")


def configure_logging(level: str | int = "INFO") -> None:
    """Idempotent stderr logging for CLI/server."""
    root = logging.getLogger("smf_swarm")
    if root.handlers:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    root.addHandler(handler)
    root.setLevel(level if isinstance(level, int) else getattr(logging, str(level).upper(), logging.INFO))
    root.propagate = False


def contains_control_characters(value: str) -> bool:
    return any(unicodedata.category(char) in {"Cc", "Cf", "Zl", "Zp"} for char in value)


def env_str(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()


def normalize_llm_base_url(base_url: str, *, name: str = "LLM base URL") -> str:
    """Return a canonical HTTP(S) endpoint with no output-tainting metadata."""
    if contains_control_characters(base_url):
        raise ValueError(f"{name} must not include control characters")
    if base_url != base_url.strip():
        raise ValueError(f"{name} must not include surrounding whitespace")
    parsed = urlsplit(base_url)
    if parsed.username is not None or parsed.password is not None:
        raise ValueError(f"{name} must not include credentials")
    if "?" in base_url or "#" in base_url:
        raise ValueError(f"{name} must not include a query or fragment")
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise ValueError(f"{name} must be an absolute HTTP(S) URL")
    try:
        _port = parsed.port  # raises ValueError on malformed ports
    except ValueError:
        raise ValueError(f"{name} must be an absolute HTTP(S) URL") from None
    del _port
    host = parsed.hostname.rstrip(".").lower()
    if _is_blocked_host(host):
        raise ValueError(f"{name} must not target cloud metadata endpoints")
    return urlunsplit(
        (parsed.scheme.lower(), parsed.netloc, parsed.path.rstrip("/"), "", "")
    )


def _canonical_ip(hostname: str) -> ipaddress._BaseAddress | None:
    host = hostname.strip().lower()
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return None
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        return ip.ipv4_mapped
    return ip


def _is_blocked_host(hostname: str) -> bool:
    host = hostname.strip().lower().rstrip(".")
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    if host in _METADATA_HOSTS or host.endswith(".metadata.google.internal"):
        return True
    ip = _canonical_ip(host)
    if ip is None:
        return False
    if ip in _METADATA_IPS:
        return True
    if ip.is_link_local or ip.is_multicast:
        return True
    return False


def validate_model_id(model: str, *, name: str = "LLM model") -> str:
    if contains_control_characters(model):
        raise ValueError(f"{name} must not include control characters")
    model = model.strip()
    if not model:
        raise ValueError(f"{name} is required")
    if len(model) > MAX_MODEL_ID_LENGTH:
        raise ValueError(f"{name} must be at most {MAX_MODEL_ID_LENGTH} characters")
    return model


def optional_model_id(model: Optional[str], *, name: str = "LLM model") -> Optional[str]:
    if model is None:
        return None
    text = str(model).strip()
    if not text:
        return None
    return validate_model_id(text, name=name)


def safe_filename(name: str) -> str:
    base = Path(str(name or "")).name.replace("\x00", "").strip()
    if not base or base in {".", ".."}:
        return "upload"
    return base[:255]


def httpx_client_kwargs(timeout: float) -> dict:
    """Safe defaults: ignore proxy env, do not follow redirects (SSRF)."""
    return {
        "timeout": timeout,
        "trust_env": False,
        "follow_redirects": False,
    }
