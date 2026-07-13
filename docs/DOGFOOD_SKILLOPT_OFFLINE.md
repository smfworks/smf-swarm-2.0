# Offline SkillOpt → Swarm Dogfood

**Date:** 2026-07-13  
**Script:** `skillopt-prototype/scripts/dogfood_offline_swarm.py`  
**Result:** **PASS**

## Config

| Setting | Value |
|---------|--------|
| use_real_verifier | False (MockEvaluator) |
| diagnostic_backend | swarm |
| swarm_diagnostic_mode | mock |
| max_epochs | 2 |
| success threshold (dogfood) | 8.0 (to produce mixed pass/fail under mock scores) |

## Evidence

### Epoch 1
- Rollout scores: `[7.5, 7.9, 8.1]` → 1 success / 2 fail  
- `[Diagnostic] backend=swarm`  
- `[Diagnostic/Swarm] agent=skillopt-optimizer chain_valid=True`  
- Gaps: Executable Planning, Risk Assessment, Hypothesis Prioritization  
- Criteria merged: base + `swarm_executable_planning`, `swarm_risk_assessment`, `swarm_hypothesis_prioritization`  
- Validation: current=8.05 candidate=8.05 → reject (no score lift; expected for mock)

### Epoch 2
- Same diagnostic path; audit_events increased (8)  
- chain_valid remained True  

## Artifacts (local)

- `data/dogfood_offline_swarm_result.json`  
- `data/dogfood_offline_swarm_audit.jsonl`  
- `data/dogfood_offline_trajectories.json`  
- `data/dogfood_offline_swarm.log`  

## Verdict

**Swarm consumer path is exercised end-to-end offline:** rollout → Phase1Pipeline diagnose → criteria merge → validate.  
Not a full multi-epoch score-improvement experiment; that still needs real verifier + skill edits with lift.
