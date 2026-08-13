"""Optional API token auth + share tokens for reports."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from typing import Optional

from fastapi import Header, HTTPException


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


def share_signing_configured() -> bool:
    """True when a dedicated share secret or API token can sign /r/ links."""
    return bool((os.environ.get("SMF_SWARM_SHARE_SECRET") or "").strip() or api_token())


def share_secret() -> str:
    """Return the HMAC key for signed report URLs.

    Fail closed: never fall back to a public default string.
    """
    secret = (os.environ.get("SMF_SWARM_SHARE_SECRET") or "").strip() or api_token()
    if not secret:
        raise RuntimeError(
            "Share signing is not configured. Set SMF_SWARM_SHARE_SECRET or SMF_SWARM_API_TOKEN."
        )
    return secret


def sign_run_id(run_id: str) -> str:
    return hmac.new(
        share_secret().encode("utf-8"),
        run_id.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()[:24]


def verify_run_signature(run_id: str, sig: str) -> bool:
    if not run_id or not sig or not share_signing_configured():
        return False
    expected = sign_run_id(run_id)
    return hmac.compare_digest(expected, sig)


def require_share_access(share_id: str, sig: str = "") -> None:
    """When API auth is on, capability URLs must also carry a valid HMAC."""
    if not auth_enabled():
        return
    if not verify_run_signature(share_id, sig):
        raise HTTPException(status_code=403, detail="invalid or missing share signature")


def public_share_path(share_id: str) -> str:
    if auth_enabled():
        return f"/share/{share_id}?s={sign_run_id(share_id)}"
    return f"/share/{share_id}"


def public_share_report(rep: dict) -> dict:
    """Drop signing material from unauthenticated share payloads."""
    out = dict(rep)
    out.pop("signed_url_path", None)
    return out
