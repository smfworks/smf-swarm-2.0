# Security

SMF Swarm 2.0 is an **open platform core**. Optional auth is intentional. It is not a multi-tenant SaaS.

## Intended deployment

- Bind the UI to loopback (`127.0.0.1`) for local use.
- Default analysis mode is **mock** (no network).
- Outputs are decision support, not professional advice.

## Environment checklist (before binding past loopback)

| Variable | Purpose |
|----------|---------|
| `SMF_SWARM_API_TOKEN` | If set, `/api/analyze` and history require Bearer or `X-API-Key` |
| `SMF_SWARM_SHARE_SECRET` | HMAC key for signed `/r/{run_id}?s=` links |
| `SMF_SWARM_LLM_BASE_URL` | OpenAI-compatible endpoint (validated before fetch) |
| `SMF_SWARM_LLM_API_KEY` | Optional; never echoed in `/api/health` |

If neither `SMF_SWARM_SHARE_SECRET` nor `SMF_SWARM_API_TOKEN` is set, signed `/r/` links are **not** issued. Public `/share/{id}` remains (local share pages).

## Controls in 0.5.1

- Share HMAC has no public default string.
- LLM base URLs must be `http`/`https` without userinfo. Link-local and cloud-metadata hosts are rejected.
- `/api/health` reports booleans (`has_llm_base_url`, `has_env_api_key`), not raw URLs or keys.
- Uploads are basename-only with an extension allowlist (`csv`, `json`, `txt`, `md`, `tsv`, `log`).
- History directory/file modes are `0700` / `0600` on POSIX.

## Residual risks (honest)

- Optional auth: with no token, the local API is open to anyone who can reach the bind address.
- `/share/{id}` is an unauthenticated read of a run if the attacker knows the share id.
- User-supplied LLM URLs that pass the allowlist are still fetched by the server (SSRF to permitted hosts, including RFC1918 and loopback). That is required for local-first DGX/Ollama use.
- Mock mode does not contact a model; LLM mode sends question text and attachments to the configured endpoint.

## Reporting

Open a private security advisory on [smfworks/smf-swarm-2.0](https://github.com/smfworks/smf-swarm-2.0) or email `dev@smfworks.com`. Do not file a public issue that includes secrets or exploit steps.
