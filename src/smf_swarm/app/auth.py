"""Optional API token auth + share tokens for reports."""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
from typing import Optional

from fastapi import Header, HTTPException

_log = logging.getLogger("smf_swarm.auth")
_ephemeral_share_secret: Optional[str] = None


def api_token() -> str:
    return (os.environ.get("SMF_SWARM_API_TOKEN") or "").strip()


def auth_enabled() -> bool:
    return bool(api_token())


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
    """HMAC key for signed /r/{run_id} links.

    Prefer SMF_SWARM_SHARE_SECRET, then the API token. If neither is set,
    use a process-ephemeral key (signed links will not survive restart).
    Never fall back to a committed static string.
    """
    configured = (os.environ.get("SMF_SWARM_SHARE_SECRET") or "").strip() or api_token()
    if configured:
        return configured
    global _ephemeral_share_secret
    if _ephemeral_share_secret is None:
        _ephemeral_share_secret = secrets.token_hex(32)
        _log.warning(
            "SMF_SWARM_SHARE_SECRET unset; using a process-ephemeral HMAC key. "
            "Signed /r/ links will not survive process restart."
        )
    return _ephemeral_share_secret


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
