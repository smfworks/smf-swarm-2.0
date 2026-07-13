# AGENTS.md — SMF Swarm

**Package:** `smf-swarm`  
**Version:** 0.4.0  
**Role:** Standalone predictive analysis app + governance-first swarm library  

## For AI agents installing / operating this package

### Install

```bash
cd smf-swarm-2.0   # or clone smfworks/smf-swarm-2.0
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[app]"
```

### Run UI for end users

```bash
smf-swarm serve --host 127.0.0.1 --port 8787
```

Open `http://127.0.0.1:8787` — question + file attach → predictive report.

### Headless (preferred for automation)

```bash
smf-swarm analyze -q "Your predictive question" -d data.csv --mode mock -o report.json
```

### Verify

```bash
pytest -q
curl -s http://127.0.0.1:8787/api/health
```

## Do / Don't

- **Do** use mock mode in CI and offline environments.  
- **Do** keep analysis results clearly labeled as decision support.  
- **Don't** claim HBHC, multi-tenant SaaS, or certified compliance for v0.2.  
- **Don't** skip updating `docs/` when changing CLI/API/UI behavior.  

## Key modules

| Path | Purpose |
|------|---------|
| `smf_swarm/app/` | FastAPI + static UI |
| `smf_swarm/analysis/` | Predictive multi-persona engine |
| `smf_swarm/governance/` | Identity, audit, permissions |
| `smf_swarm/capability/` | TRACE-style diagnostic |
| `smf_swarm/cli.py` | `smf-swarm` entrypoint |
