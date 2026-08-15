# AGENTS.md — SMF Swarm

**Package:** `smf-swarm`  
**Version:** 0.5.2  
**Role:** Standalone predictive analysis app + governance-first swarm library  
**Repo:** https://github.com/smfworks/smf-swarm-2.0 (public, MIT)

## For AI agents installing / operating this package

### Install

```bash
git clone https://github.com/smfworks/smf-swarm-2.0.git
cd smf-swarm-2.0
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[app]"
```

### Run UI for end users

```bash
smf-swarm serve --host 127.0.0.1 --port 8787
```

Open `http://127.0.0.1:8787` — question + file attach → predictive report.

Human-facing install guide: [INSTALL.md](INSTALL.md)  
GitHub homepage assets: logo then UI screenshot under `docs/assets/`.

### Headless (preferred for automation)

```bash
smf-swarm analyze -q "Your predictive question" -d data.csv --mode mock -o report.json
```

### Verify (same as CI)

```bash
pip install -e ".[dev]"
ruff check src tests scripts
mypy src
pytest -q
smf-swarm analyze -q "Smoke test" -d fixtures/sample_growth.csv --mode mock
```

CI runs ruff, mypy, pytest, and the mock CLI smoke on Python 3.10, 3.11, and 3.12 for every push and pull request to `main`.

## Do / Don't

- **Do** use mock mode in CI and offline environments.  
- **Do** keep analysis results clearly labeled as decision support.  
- **Don't** claim HBHC, multi-tenant SaaS, or full Phase 2–6 platform for v0.5.  
- **Don't** skip updating `docs/` when changing CLI/API/UI behavior.  

## Key modules

| Path | Purpose |
|------|---------|
| `smf_swarm/app/` | FastAPI + static UI |
| `smf_swarm/analysis/` | Predictive multi-persona engine + charts |
| `smf_swarm/governance/` | Identity, audit, permissions |
| `smf_swarm/capability/` | TRACE-style diagnostic |
| `smf_swarm/cli.py` | `smf-swarm` entrypoint |
