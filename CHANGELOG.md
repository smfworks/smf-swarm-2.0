# Changelog

## 0.5.1 — 2026-08-13

Production-hardening of the public platform core.

- Fail-closed share HMAC: no public default secret
- LLM base URLs validated (http/https only; no file:, userinfo, metadata, link-local)
- `/api/health` no longer echoes the LLM base URL
- Uploads: basename + extension allowlist
- POSIX history perms 0700/0600
- CI: ruff + mypy + pytest + mock CLI smoke on 3.10 and 3.12
- Docs match public 0.5.1

## 0.5.0

Product UI, charts, share links, mock-first analysis.
