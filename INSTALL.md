# Install SMF Swarm (download & use)

## What you need

- Python **3.10+**
- macOS / Linux / Windows
- ~50MB free for a venv + package

## Download

```bash
git clone https://github.com/smfworks/smf-swarm-2.0.git
cd smf-swarm-2.0
```

This repository is public.

## Install

**Linux / macOS**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[app]"
```

**Windows** (cmd / PowerShell)

```bat
py -3 -m venv .venv
.venv\Scripts\activate
python -m pip install -U pip
pip install -e ".[app]"
```

## Use the product UI

```bash
smf-swarm serve --host 127.0.0.1 --port 8787
```

Open **http://127.0.0.1:8787**

1. Type a decision question
2. Optional: attach CSV / JSON / TXT / MD (try `fixtures/sample_growth.csv`)
3. Mode: **Offline swarm** first (no key); or **LLM swarm** after Settings
4. **Run swarm analysis**
5. Export / copy share link / reopen from Recent runs

### LLM Settings (in the browser)

Click **Settings** (top right):

1. Base URL (e.g. `http://127.0.0.1:8000/v1`)
2. Model id
3. Optional API key
4. **Save** or **Test connection**

Settings are stored in browser localStorage and override env vars for that browser.

Do **not** expose the UI on `0.0.0.0` (or any non-loopback address) without
`SMF_SWARM_API_TOKEN` **and** `SMF_SWARM_SHARE_SECRET`. The CLI refuses a
non-loopback bind when the share secret is missing. See [SECURITY.md](SECURITY.md).

## Use from the terminal (agents / scripts)

```bash
smf-swarm analyze \
  -q "What is the near-term outlook?" \
  -d fixtures/sample_growth.csv \
  --mode mock \
  -o report.json
```

## Optional environment

| Variable | Purpose |
|----------|---------|
| `SMF_SWARM_MODE` | Default mode hint (`mock` / `llm`) |
| `SMF_SWARM_LLM_BASE_URL` | OpenAI-compatible base URL |
| `SMF_SWARM_LLM_MODEL` | Model id |
| `SMF_SWARM_LLM_API_KEY` | API key if required |
| `SMF_SWARM_API_TOKEN` | If set, protect analyze/history with Bearer / `X-API-Key` |
| `SMF_SWARM_SHARE_SECRET` | HMAC secret for signed `/r/{run_id}?s=` links; **required** off-loopback |
| `SMF_SWARM_LLM_ALLOW_PRIVATE` | Set `1` to allow RFC1918 LLM endpoints |
| `SMF_SWARM_HISTORY` | Override path for local history JSONL |
| `SMF_SWARM_LOG_LEVEL` | Stdlib log level (`INFO` default) |
| `SMF_SWARM_STRICT` | If `1`, history write failures return HTTP 500 |
| `SMF_SWARM_FALLBACK` | Set `never` to fail instead of mock fallback on LLM errors |

## Auth & sharing

- **No token set** → open local use (default).
- **Token set** → UI prompts once; agents send `X-API-Key`.
- Every run gets a **public share link** `/share/{share_id}` (read-only report page).
- Signed `/r/` links use `SMF_SWARM_SHARE_SECRET` or a per-process random secret on loopback.

## Verify install

```bash
pip install -e ".[dev]"
ruff check src tests scripts
pytest -q
smf-swarm analyze -q "Smoke test" -d fixtures/sample_growth.csv --mode mock
curl -s http://127.0.0.1:8787/api/health
```

## PyPI note

Git clone install today. When publishing publicly:

```bash
pip install build twine
python -m build
# twine upload dist/*
```

Package name: **`smf-swarm`**. Entry point: **`smf-swarm`**.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `smf-swarm: command not found` | Activate venv; `pip install -e ".[app]"` |
| Port in use | `smf-swarm serve --port 8790` |
| LLM mode fails | Settings → Test connection; app can fall back to mock unless `fallback=never` |
| Charts missing | Use CSV with ≥3 numeric rows |
| 401 Unauthorized | Set matching `SMF_SWARM_API_TOKEN` / UI prompt |
| Non-loopback serve refused | Export `SMF_SWARM_SHARE_SECRET` first |
| LLM URL rejected | Private/link-local/metadata/`file://` blocked; use `127.0.0.1` or set `SMF_SWARM_LLM_ALLOW_PRIVATE=1` |
