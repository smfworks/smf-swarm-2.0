# SMF Swarm 2.0

**Governance-first agent swarm platform** — Phase 1 foundation (complete for first run).

| | |
|--|--|
| Version | 0.1.0 |
| Phase | **1 complete** — Capability Diagnostic + Governance Hooks |
| Owner | Aiona Edge (SMF Works) |
| Repo | https://github.com/smfworks/smf-swarm-2.0 (private) |
| Status | Dual-path diagnostic locked (mock = CI, LLM = production insight) |

## What Phase 1 delivered

1. **Capability Diagnostic** (TRACE-inspired) — mock backend + optional OpenAI-compatible LLM backend  
2. **Governance hooks** — identity registry, hash-chained audit log, permission engine (deny-by-default)  
3. **Minimal pipeline** — register agent → grant `capability.diagnose` → run diagnosis → audit  
4. **Dogfood** — SkillOpt-style edit-planning trajectories  
5. **Mock vs LLM comparison** on DGX Spark (`Qwen3.6-35B-A3B-NVFP4`)

**Not in Phase 1:** HBHC crypto revocation, topology engine, Council deliberation, multi-tenant RBAC.

## Docs (keep in lockstep with code)

| Document | Purpose |
|----------|---------|
| [`docs/PHASE1_DOD.md`](docs/PHASE1_DOD.md) | Locked scope + success criteria (checked) |
| [`docs/PHASE1_STATUS.md`](docs/PHASE1_STATUS.md) | Living status, commits, next options |
| [`docs/DOGFOOD.md`](docs/DOGFOOD.md) | First dogfood run findings |
| [`docs/MOCK_VS_LLM.md`](docs/MOCK_VS_LLM.md) | Mock vs LLM diagnostic comparison |
| [`docs/CONSUMER_SKILLOPT.md`](docs/CONSUMER_SKILLOPT.md) | First consumer: SkillOpt → Phase1Pipeline |
| [`docs/adr/0001-governance-first-foundation.md`](docs/adr/0001-governance-first-foundation.md) | Architecture decision |

Full platform vision (seven layers) lives in the internal architecture specification; this repo is the **Phase 1 implementation**.

## Install

```bash
cd smf-swarm-2.0
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
# optional LLM client
pip install -e ".[llm]"
pytest -q
```

## Quick start

```bash
# Offline mock diagnosis (no network)
python -m smf_swarm.pipeline.phase1_run --domain article_editing

# SkillOpt-style fixture
python -m smf_swarm.pipeline.phase1_run \
  --fixture fixtures/skillopt_edit_planning_trajectories.json \
  --domain article_editing \
  --audit /tmp/smf-swarm-audit.jsonl
```

```python
from smf_swarm.pipeline import Phase1Pipeline

pipe = Phase1Pipeline()
agent_id = pipe.bootstrap_agent("research-agent")
result = pipe.run_diagnosis(
    agent_id,
    successful=[{"content": "…good trajectory…"}],
    failed=[{"content": "…failed trajectory…"}],
    domain="article_editing",
)
assert result.chain_valid
print(result.to_dict())
```

### Mock vs LLM comparison (requires DGX / OpenAI-compatible endpoint)

```bash
# Default script targets spark-56bc:8888 — edit BASE_URL/MODEL if needed
python scripts/compare_mock_vs_llm.py
# Writes data/mock_vs_llm_comparison.json (gitignored)
```

## Layout

```
src/smf_swarm/
  governance/   identity, audit, permissions
  capability/   diagnostic engine (mock + LLM)
  pipeline/     phase1_run entrypoint
docs/           DoD, status, dogfood, mock-vs-llm, ADRs
fixtures/       SkillOpt-style trajectories
scripts/        comparison runner
tests/
```

## Diagnostic policy (locked)

| Context | Backend |
|---------|---------|
| CI / unit tests | `MockCapabilityBackend` (deterministic) |
| Production diagnosis | `LLMCapabilityBackend` when endpoint available |
| SkillOpt criteria generation | Prefer LLM `suggested_criterion` text |

## Verification

```bash
pytest -q   # expect 6 passed (offline)
```

## License

MIT — SMF Works
