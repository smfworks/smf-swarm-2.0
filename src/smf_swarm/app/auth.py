"""Optional API token auth + share tokens for reports."""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from typing import Optional

from fastapi import Header, HTTPException

from smf_swarm.logutil import get_logger

_log = get_logger("smf_swarm.auth")
_process_share_secret: str | None = None


def api_token() -> str:
    return (os.environ.get("SMF_SWARM_API_TOKEN") or "").strip()


def auth_enabled() -> bool:
    return bool(api_token())


def is_loopback_bind(host: str) -> bool:
    h = (host or "").strip().lower()
    if h.startswith("[") and h.endswith("]"):
        h = h[1:-1]
    return h in {"127.0.0.1", "localhost", "::1", "::ffff:127.0.0.1"}


def require_share_secret_for_bind(host: str) -> None:
    """Non-loopback binds must set SMF_SWARM_SHARE_SECRET (no hardcoded HMAC)."""
    if is_loopback_bind(host):
        return
    if (os.environ.get("SMF_SWARM_SHARE_SECRET") or "").strip():
        return
    raise RuntimeError(
        "Non-loopback bind requires SMF_SWARM_SHARE_SECRET "
        "(refusing hardcoded share HMAC)"
    )


def require_api_auth(
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
) -> None:
    """If SMF_SWARM_API_TOKEN is set, require Bearer or X-API-Key match."""
    expected = api_token()
    if not expected:
        return
    token = None
    if x_api_key:
        token = x_api_key.strip()
    elif authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    if not token or not hmac.compare_digest(token, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing API token")


def new_share_id() -> str:
    return secrets.token_urlsafe(16)


def share_secret() -> str:
    """HMAC key for /r/ signatures.

    Prefer SMF_SWARM_SHARE_SECRET, then the API token. Otherwise generate a
    per-process random secret (loopback/dev only). Never fall back to a
    hardcoded constant.
    """
    global _process_share_secret
    env = (os.environ.get("SMF_SWARM_SHARE_SECRET") or "").strip()
    if env:
        return env
    tok = api_token()
    if tok:
        return tok
    if _process_share_secret is None:
        _process_share_secret = secrets.token_hex(32)
        _log.warning(
            "SMF_SWARM_SHARE_SECRET unset; using a per-process random secret. "
            "Signed /r/ links will not survive restart."
        )
    return _process_share_secret


def sign_run_id(run_id: str) -> str:
    return hmac.new(
        share_secret().encode("utf-8"),
        run_id.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()[:24]


def verify_run_signature(run_id: str, sig: str) -> bool:
    if not run_id or not sig:
        return False
    expected = sign_run_id(run_id)
    return hmac.compare_digest(expected, sig)
