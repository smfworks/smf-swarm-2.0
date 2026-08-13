# Changelog

## 0.5.1 — 2026-08-13

Production hardening of the public platform core.

- Add GitHub Actions CI (ruff, mypy, pytest, mock CLI smoke) on Python 3.10 and 3.12.
- Pin ruff and mypy in the `dev` extra with a locked rule set (no UP* gate).
- Fail closed on signed `/r/` links when no share secret or API token is configured. Remove the public default HMAC string.
- Validate LLM base URLs before `httpx` (scheme, credentials, metadata / link-local).
- Stop echoing the raw LLM base URL from `/api/health`.
- Strip upload filenames to basename; allowlist `csv json txt md tsv log`.
- Set POSIX history directory/file modes to `0700` / `0600`.
- Document the open-core threat model in `SECURITY.md`.
- Correct docs that still called this public repository private.

## 0.5.0 — 2026-07-13

Premium dark UI (Linear-inspired). See `docs/PRODUCT_APP_v0.5.md`.
