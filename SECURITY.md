# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.5.x   | Yes       |

## Reporting a vulnerability

Email **security@smfworks.com** or open a [private GitHub security advisory](https://github.com/smfworks/smf-swarm-2.0/security/advisories/new).

Please include:

- Affected version / commit
- Reproduction steps
- Impact (data exposure, SSRF, auth bypass, etc.)

Do **not** open a public issue for unreleased vulnerabilities.

We aim to acknowledge reports within 5 business days.

## Operational guidance

- Bind the UI to loopback unless you intend remote access: `smf-swarm serve --host 127.0.0.1`.
- If the process is reachable beyond localhost, set `SMF_SWARM_API_TOKEN` and `SMF_SWARM_SHARE_SECRET`.
- Never commit API keys. Use environment variables. The Settings UI may store base URL/model in localStorage; the API key stays in sessionStorage only.
- LLM base URLs must be absolute `http`/`https` with no embedded credentials, query, or fragment. Cloud metadata hosts are rejected.
- Share pages (`/share/{id}`) are unguessable. If `SMF_SWARM_API_TOKEN` is set they also require `?s=` HMAC (same key as `/r/`). `/api/share/{id}` never returns `signed_url_path`.
- LLM API keys entered in the Settings UI are kept in **sessionStorage** only (cleared when the tab closes). Base URL and model may persist in localStorage. Prefer `SMF_SWARM_LLM_API_KEY` in the process environment.
- Signed `/r/{run_id}?s=` links use `SMF_SWARM_SHARE_SECRET` (or the API token). If neither is set, a process-ephemeral key is used and signed links die on restart.
- Eval harness (`scripts/compare_mock_vs_llm.py`) requires `SMF_SWARM_EVAL_BASE_URL`. There is no implicit `127.0.0.1:8888` default.

## Secrets in git history

If a credential is discovered in history, **do not rewrite commits**. Rotate the credential and open an incident note. History rewrite is reserved for the repository owner.
