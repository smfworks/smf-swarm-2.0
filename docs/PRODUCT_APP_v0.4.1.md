# Product App v0.4.1 — LLM Settings UI

**Date:** 2026-07-13

## What shipped

- **Settings** button in the web UI
- Fields: Base URL, Model, API key (browser `localStorage`)
- **Test connection** → `POST /api/llm/test`
- Analyze accepts `llm_base_url` / `llm_model` / `llm_api_key` (UI overrides env)
- LLM mode without base URL returns a clear 400 + opens Settings

Env `SMF_SWARM_LLM_*` still works as defaults.
