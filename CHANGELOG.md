# Changelog

All notable changes to this project are documented here.

## 0.5.2 — 2026-08-14

### Security

- Share HMAC is fail-closed. If neither `SMF_SWARM_SHARE_SECRET` nor `SMF_SWARM_API_TOKEN` is set, the process does not mint a usable `/r/` signature.
- `/api/health` reports booleans only (`has_llm_base_url`, `has_model`, `has_env_api_key`).
- LLM URL allowlist covers the app, engine, CLI, eval harness, and capability diagnostic backend.
- Uploads are basename-only with an extension allowlist; POSIX history uses `0700` / `0600`.

### Added

- CI now runs `mypy src` and a mock CLI smoke beside ruff + pytest on Python 3.10–3.12.
- `mypy` is part of the `dev` extra.

### Changed

- Docs match the fail-closed share contract. `SECURITY.md` no longer claims a process-ephemeral signer.
- `docs/PHASE1_STATUS.md` is labeled as Phase 1 history; current product is public 0.5.2.

## 0.5.1 — 2026-08-13

### Security

- Removed hardcoded lab LLM host/model and placeholder API key from `PredictiveSwarmEngine`.
- Replaced the committed HMAC share-secret fallback with a process-ephemeral key (or `SMF_SWARM_SHARE_SECRET`).
- Validate LLM base URLs (HTTP(S) only, no credentials/query/fragment, block cloud metadata).
- HTTP clients now disable env-proxy trust and redirect following.
- Do not echo exception bodies or LLM probe response text to API clients.
- Sanitize upload filenames; skip corrupt audit-log lines instead of crashing.
- Block IPv4-mapped and other link-local aliases of cloud metadata (`http://[::ffff:169.254.169.254]/`).
- When API auth is enabled, `/share/{id}` and `/api/share/{id}` require `?s=` HMAC; share JSON redacts `signed_url_path`.
- History JSONL append/trim uses exclusive `fcntl` locking (POSIX).
- Settings UI no longer writes LLM API keys to `localStorage` (sessionStorage only; migrates old keys).
- Eval harness requires `SMF_SWARM_EVAL_BASE_URL` — `DEFAULT_EVAL_BASE_URL` is empty.

### Added

- GitHub Actions CI: ruff + pytest on Python 3.10–3.12 for push/PR to `main`.
- Dependabot for Actions and pip.
- `SECURITY.md`, `CONTRIBUTING.md`, this changelog, `.env.example`.
- Shared `smf_swarm.config` validation used by app, engine, CLI, and eval harness.
- Hardening tests for CLI, config, audit reload, and engine defaults.

### Changed

- CLI `analyze` validates data files, enforces the 5MB cap, and passes `SMF_SWARM_LLM_API_KEY`.
- Public docs no longer describe the repo as private or use an internal lab hostname as the default example.
- Package version 0.5.1.

## 0.5.0

Governance-first predictive analysis app (UI, charts, share links, CLI). See `docs/PRODUCT_APP_v0.5.md`.
