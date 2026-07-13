# SMF Swarm 2.0

**Governance-first agent swarm platform** — Phase 1 foundation.

| | |
|--|--|
| Version | 0.1.0 |
| Phase | 1 — Capability Diagnostic + Governance Hooks |
| Owner | Aiona Edge (SMF Works) |
| Status | First implementation run |

## Phase 1 scope

See [`docs/PHASE1_DOD.md`](docs/PHASE1_DOD.md).

In short:

1. **Capability Diagnostic** (TRACE-inspired) — mock + optional LLM backend  
2. **Governance hooks** — identity registry, hash-chained audit log, permission engine  
3. **Minimal pipeline** — register agent → grant diagnose → run diagnosis → audit  

**Not in Phase 1:** HBHC crypto revocation, topology engine, Council deliberation, multi-tenant RBAC.

## Install

```bash
cd smf-swarm-2.0
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

## Quick start

```bash
# Offline mock diagnosis (no network)
python -m smf_swarm.pipeline.phase1_run --domain article_editing

# Or API
from smf_swarm.pipeline import Phase1Pipeline

pipe = Phase1Pipeline()
agent_id = pipe.bootstrap_agent("research-agent")
result = pipe.run_diagnosis(
    agent_id,
    successful=[{"content": "…good trajectory…"}],
    failed=[{"content": "…failed trajectory…"}],
    domain="article_editing",
)
print(result.to_dict())
```

## Layout

```
src/smf_swarm/
  governance/   identity, audit, permissions
  capability/   diagnostic engine
  pipeline/     phase1_run entrypoint
docs/
  PHASE1_DOD.md
  adr/
tests/
```

## Architecture

Full platform vision: vault `SMF-Swarm-2.0-Architecture-Specification-v1.0.md`  
ADR: `docs/adr/0001-governance-first-foundation.md`

## License

MIT — SMF Works
