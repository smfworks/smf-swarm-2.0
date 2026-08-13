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
- Never commit API keys. Use environment variables or the Settings UI (browser localStorage — treat that machine as trusted).
- LLM base URLs must be absolute `http`/`https` with no embedded credentials, query, or fragment. Cloud metadata hosts are rejected.
- Share pages (`/share/{id}`) are unguessable but unauthenticated by design. Do not attach secrets in questions or files you later share.
- Signed `/r/{run_id}?s=` links use `SMF_SWARM_SHARE_SECRET` (or the API token). If neither is set, a process-ephemeral key is used and signed links die on restart.

## Secrets in git history

If a credential is discovered in history, **do not rewrite commits**. Rotate the credential and open an incident note. History rewrite is reserved for the repository owner.
