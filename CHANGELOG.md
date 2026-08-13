# Changelog

All notable changes to this project are documented here.

## 0.5.1 — 2026-08-13

### Security

- Removed hardcoded lab LLM host/model and placeholder API key from `PredictiveSwarmEngine`.
- Replaced the committed HMAC share-secret fallback with a process-ephemeral key (or `SMF_SWARM_SHARE_SECRET`).
- Validate LLM base URLs (HTTP(S) only, no credentials/query/fragment, block cloud metadata).
- HTTP clients now disable env-proxy trust and redirect following.
- Do not echo exception bodies or LLM probe response text to API clients.
- Sanitize upload filenames; skip corrupt audit-log lines instead of crashing.

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
