# SMF Swarm 2.0 — Phase 1 Status

**Last updated:** 2026-07-13  
**Package version:** 0.1.0  
**Branch:** `main`

## Summary

Phase 1 foundation is **implemented, tested, dogfooded, and dual-path validated**.

| Area | State |
|------|--------|
| Governance hooks | Done — identity, hash-chained audit, permissions |
| Capability diagnostic | Done — mock + LLM backends |
| Phase1Pipeline | Done — permission-gated diagnosis |
| Offline tests | Green — `pytest -q` → 6 passed |
| GitHub | https://github.com/smfworks/smf-swarm-2.0 (private) |

## Notable commits

| Commit | Description |
|--------|-------------|
| `3e95364` | Phase 1 foundation (governance, diagnostic, pipeline, tests, DoD, ADR) |
| `36c75ba` | Mock vs LLM comparison script + `failure_coverage` coercion |

*(Doc lockstep commit follows this status file.)*

## Dogfood

- Fixture: `fixtures/skillopt_edit_planning_trajectories.json`
- Result: 4 mock gaps; audit chain valid  
- Details: [`DOGFOOD.md`](DOGFOOD.md)

## Mock vs LLM

- Endpoint: DGX Spark `spark-56bc:8888` / `unsloth/Qwen3.6-35B-A3B-NVFP4`
- Theme overlap: prioritization, executable plan, risk  
- Policy: mock = CI; LLM = production insight  
- Details: [`MOCK_VS_LLM.md`](MOCK_VS_LLM.md)

## Explicitly deferred

- HBHC cryptographic revocation  
- Topology engine / Council / multi-tenant RBAC  
- Public PyPI / replace smf-swarm v1 product surface  

## First consumer (2026-07-13)

**SkillOpt** (`skillopt-prototype` v0.14) calls `Phase1Pipeline` via `swarm_diagnostic_adapter.py`.

- Design: [`CONSUMER_SKILLOPT.md`](CONSUMER_SKILLOPT.md)
- Default: `diagnostic_backend=swarm`, `swarm_diagnostic_mode=mock`
- Legacy in-tree diagnostic remains available

## Next options (not started)

1. Export a **real** SkillOpt epoch trajectory dump and re-run comparison  
2. Phase 2 design spike: durable identity store → crypto credentials  
3. Vertical demo pipeline that *consumes* Phase1Pipeline  

Prefer starting only when there is a clear consumer for the next layer.
