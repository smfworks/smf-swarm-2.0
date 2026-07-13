# Install SMF Swarm (end users & agents)

## Requirements

- Python **3.10+**
- macOS / Linux / Windows

## Quick install (from Git)

```bash
git clone https://github.com/smfworks/smf-swarm-2.0.git
cd smf-swarm-2.0
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -U pip
pip install -e ".[app]"
```

## Launch the app

```bash
smf-swarm serve --host 127.0.0.1 --port 8787
```

Open **http://127.0.0.1:8787**

- Ask a question  
- Attach CSV/JSON/TXT/MD  
- Get predictive analysis + charts (CSV) + export/share  

## Headless (agents / automation)

```bash
smf-swarm analyze \
  -q "What is the near-term outlook?" \
  -d ./data.csv \
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
| `SMF_SWARM_SHARE_SECRET` | HMAC secret for signed `/r/{run_id}?s=` links |
| `SMF_SWARM_HISTORY` | Override path for local history JSONL |

## Auth & sharing

- **No token set** → open local use (default).  
- **Token set** → UI prompts once; agents send `X-API-Key: <token>`.  
- Every run gets a **public share link** `/share/{share_id}` (read-only report page).

## Verify install

```bash
pytest -q
smf-swarm analyze -q "Smoke test" -d fixtures/sample_growth.csv --mode mock
curl -s http://127.0.0.1:8787/api/health
```

## PyPI note

Private repo today. When publishing publicly:

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
| LLM mode fails | Check URL/model; app falls back to mock and labels it |
| Charts missing | Use CSV with ≥3 numeric rows |
| 401 Unauthorized | Set matching `SMF_SWARM_API_TOKEN` / UI prompt |
