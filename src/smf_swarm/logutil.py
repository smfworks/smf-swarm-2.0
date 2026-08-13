"""Stdlib logging helpers for SMF Swarm.

Never pass API keys, bearer tokens, or URL userinfo into these helpers.
"""
from __future__ import annotations

import logging
import os
from urllib.parse import urlsplit, urlunsplit

_configured = False


def get_logger(name: str = "smf_swarm") -> logging.Logger:
    """Return a module logger; configure root level once from SMF_SWARM_LOG_LEVEL."""
    global _configured
    if not _configured:
        level_name = (os.environ.get("SMF_SWARM_LOG_LEVEL") or "INFO").upper()
        level = getattr(logging, level_name, logging.INFO)
        logging.basicConfig(
            level=level,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
        _configured = True
    return logging.getLogger(name)


def safe_url_for_log(url: str) -> str:
    """Strip credentials / query / fragment before logging an LLM URL."""
    if not url:
        return ""
    parsed = urlsplit(url)
    host = parsed.hostname or ""
    if parsed.port:
        netloc = f"{host}:{parsed.port}"
    else:
        netloc = host
    return urlunsplit((parsed.scheme, netloc, parsed.path, "", ""))
