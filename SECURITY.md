# Security policy

## Supported versions

`smf-swarm` **0.5.x** on this repository is the supported line. Older Phase-1-only
snapshots are historical and do not receive backports.

## How to report a vulnerability

Please **do not** open a public GitHub issue for security bugs.

- Email **michael@smfworks.com** with a description, impact, and reproduction.
- Or use [GitHub private vulnerability reporting](https://github.com/smfworks/smf-swarm-2.0/security/advisories/new)
  if it is enabled on this repository.

We will acknowledge receipt and work with you on a fix and disclosure timeline.

## Product threat model (local-first)

SMF Swarm is a **single-user, local-first** analysis app. The default bind is
`127.0.0.1`. Treat `--host 0.0.0.0` (or any non-loopback address) as exposing an
HTTP service with file upload, optional LLM proxying, and shareable reports.

### LLM base URL (SSRF)

`/api/llm/test` and LLM-mode `/api/analyze` fetch a caller-supplied OpenAI-compatible
base URL. The server:

- Allows only `http` / `https`
- Rejects credentials in the URL, `file://`, and other schemes
- Always rejects cloud metadata hosts/IPs (`169.254.169.254`, `metadata.google.internal`)
- **Default-denies private and link-local targets** unless the destination is
  loopback (`127.0.0.1`, `::1`, `localhost`)
- Uses `httpx` with `trust_env=False` and `follow_redirects=False`

To reach a private LAN endpoint (for example a lab GPU box), set
`SMF_SWARM_LLM_ALLOW_PRIVATE=1` **and** keep the process bound to loopback or
protect it with `SMF_SWARM_API_TOKEN`.

### Share links and HMAC

- `/share/{share_id}` and `/api/share/{share_id}` are **intentionally public
  read-only report pages** (v0.4 product contract). Do not expose the UI on a
  shared network if reports contain sensitive attachments.
- Signed `/r/{run_id}?s=` links use `SMF_SWARM_SHARE_SECRET` (or the API token
  if that is the only secret set).
- A hardcoded development HMAC is **not** used. On loopback, a missing secret
  becomes a **per-process random** value (links die on restart).
- **Non-loopback bind requires `SMF_SWARM_SHARE_SECRET`.** The CLI refuses to
  start otherwise.

Do not expose the app without:

```bash
export SMF_SWARM_API_TOKEN=...
export SMF_SWARM_SHARE_SECRET=...
smf-swarm serve --host 127.0.0.1 --port 8787
```

### Secrets we will not log

API keys, bearer tokens, and URL userinfo must never appear in logs. History
JSONL must not store browser LLM API keys.

## Operational signals

Set `SMF_SWARM_LOG_LEVEL` (`DEBUG`, `INFO`, `WARNING`, …). Analyze start/end,
LLM fallback, and history persist failures are logged. The analyze JSON includes
`history_persisted` so a silent disk failure is visible to the client.

`SMF_SWARM_STRICT=1` turns a history write failure into HTTP 500.
