# SMF Swarm

**Governance-first predictive analysis application** — downloadable package for humans and AI agents.

| | |
|--|--|
| Version | **0.3.0** |
| Product | Standalone app (UI + CLI + history/export) + Phase 1 library |
| Repo | https://github.com/smfworks/smf-swarm-2.0 (private) |

## What you get

1. **Stylish web UI** — ask a question, attach CSV/JSON/TXT/MD, get a predictive analysis report  
2. **Multi-persona swarm** — Scout · Strategist · Skeptic · Forecaster  
3. **Governance** — identity + hash-chained audit on every analysis run  
4. **Agent-friendly CLI** — install and run like SkillOpt-style tool packages  
5. **Phase 1 library** — capability diagnostic + hooks (SkillOpt consumer, etc.)

## Install (humans or agents)

```bash
git clone https://github.com/smfworks/smf-swarm-2.0.git
cd smf-swarm-2.0
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[app]"
```

### Start the UI

```bash
smf-swarm serve --host 127.0.0.1 --port 8787
# open http://127.0.0.1:8787
```

### Headless analysis (agent / automation)

```bash
smf-swarm analyze \
  --question "What is the base-case outlook and top risks?" \
  --data ./sample.csv \
  --mode mock \
  --output report.json
```

### Capability diagnostic (Phase 1 library)

```bash
smf-swarm diagnose --fixture fixtures/skillopt_edit_planning_trajectories.json
```

## Analysis modes

| Mode | When | Needs |
|------|------|--------|
| `mock` (default) | Offline demos, CI, air-gapped | Nothing |
| `llm` | Richer synthesis | `SMF_SWARM_LLM_BASE_URL`, model; optional `SMF_SWARM_LLM_API_KEY` |

```bash
export SMF_SWARM_LLM_BASE_URL=http://spark-56bc:8888/v1
export SMF_SWARM_LLM_MODEL=unsloth/Qwen3.6-35B-A3B-NVFP4
smf-swarm analyze -q "..." --mode llm
```

## UI flow

1. Enter a predictive / decision question  
2. Optional: drop data files  
3. Choose Offline swarm or LLM swarm  
4. Read report: prediction, confidence, scenarios, risks, actions, persona views, audit status  

## Library (still available)

Phase 1 platform APIs remain under `smf_swarm.governance`, `smf_swarm.capability`, `smf_swarm.pipeline`.  
See `docs/PHASE1_STATUS.md`, `docs/CONSUMER_SKILLOPT.md`.

## Docs

| Doc | Purpose |
|-----|---------|
| [`docs/PRODUCT_APP_v0.2.md`](docs/PRODUCT_APP_v0.2.md) | Product scope for standalone app |
| [`docs/PHASE1_DOD.md`](docs/PHASE1_DOD.md) | Phase 1 foundation DoD |
| [`docs/PHASE1_STATUS.md`](docs/PHASE1_STATUS.md) | Living status |
| [`docs/CONSUMER_SKILLOPT.md`](docs/CONSUMER_SKILLOPT.md) | SkillOpt consumer |
| [`docs/MOCK_VS_LLM.md`](docs/MOCK_VS_LLM.md) | Diagnostic dual-path policy |

## Tests

```bash
pip install -e ".[dev]"
pytest -q
```

## Agent notes

- Prefer `smf-swarm serve` for interactive demos; `smf-swarm analyze` for automation.  
- Default mode is **mock** (deterministic structure, no network).  
- Treat outputs as **decision support**, not certified professional advice.  
- Keep docs in lockstep with code when changing the app surface.

## License

MIT — SMF Works
