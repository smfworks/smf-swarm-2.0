# Security Policy

## Model

The public `smf-swarm` core is an **optional-auth** local/LAN app. That is intentional. Binding past loopback without `SMF_SWARM_API_TOKEN` is an operator choice, not a default we recommend.

## Before exposing the UI

1. Set `SMF_SWARM_API_TOKEN`.
2. Set `SMF_SWARM_SHARE_SECRET` if you want signed `/r/{run_id}?s=` links. Without it, signed URLs are not issued and `/r/` returns 403.
3. Do not put LLM API keys in the repo. Use env vars or the Settings form.

## Residual risks

- `/share/{share_id}` is an unguessable-id public read of a stored report. Treat share IDs as secrets.
- LLM base URLs are fetched by the server. `file:`, credentialed URLs, metadata hosts, and link-local addresses are rejected. Localhost is allowed for local models.
- Uploads are limited to csv/json/txt/md/tsv/log, 5MB, basename only. This is not a sandbox.
- History JSONL is mode 0600 on POSIX. It still lives on the operator disk.

## Reporting

Email `dev@smfworks.com` or open a private GitHub advisory.
