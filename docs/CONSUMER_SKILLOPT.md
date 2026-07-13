# Consumer Design: SkillOpt → SMF Swarm Phase1Pipeline

**Status:** Accepted / implemented (2026-07-13)  
**Owner:** Aiona Edge  
**Phase-2 impact:** None blocking — SkillOpt is a client of stable Swarm APIs only.

---

## Goal

Make **SkillOpt** the first real consumer of `smf_swarm.pipeline.Phase1Pipeline`:

```
SkillOpt epoch rollout
  → split success / fail trajectories
  → Phase1Pipeline (identity + permission + diagnose + audit)
  → CapabilityGap.suggested_criterion
  → merge into validation criteria
  → next validate/reflect uses merged criteria
```

## Non-goals

- HBHC, topology, Council  
- Replacing SkillOpt’s optimization loop  
- Deleting in-tree `capability_diagnostic.py` (kept as fallback)  
- Changing public SkillOpt paper claims  

## Interfaces

### Trajectory shape (Swarm input)

Each trajectory is a `dict` with at least a text field Swarm can format:

```json
{
  "content": "<human-readable trajectory summary>",
  "article_id": "...",
  "rubric_score": 7.2,
  "success": true
}
```

SkillOpt maps rollout rows via `swarm_diagnostic_adapter.trajectories_to_swarm_format`.

### Swarm entrypoint

- Package: `smf_swarm` (`/home/mikesai1/workspace/smf-swarm-2.0`)  
- API: `Phase1Pipeline.bootstrap_agent` + `run_diagnosis`  
- Capability grant: `capability.diagnose`  
- Domain: `article_editing` (configurable)

### Criteria merge

- Take top N gaps with non-empty `suggested_criterion`  
- Keys: `swarm_<slug>` in the criteria dict  
- List form also returned for `reflect()`  

## Config (SkillOpt)

| Key | Default | Meaning |
|-----|---------|---------|
| `use_capability_diagnostic` | `True` | Master switch |
| `diagnostic_backend` | `"swarm"` | `"swarm"` \| `"legacy"` |
| `swarm_diagnostic_mode` | `"mock"` | `"mock"` \| `"llm"` |
| `diagnostic_max_gaps` | `3` | Cap gaps/criteria |
| `swarm_package_root` | path to smf-swarm-2.0 | For `sys.path` if not installed |

## Success criteria (consumer slice)

- [x] Design doc in Swarm repo  
- [x] Adapter module in SkillOpt  
- [x] Config flag; default path uses Swarm  
- [x] Legacy diagnostic still selectable  
- [x] Offline smoke: mock Swarm diagnose from SkillOpt trajectories  
- [x] Docs updated both repos  

## Phase-2 safety rules

1. SkillOpt must not reimplement audit/identity.  
2. No SkillOpt-specific types inside `smf_swarm.governance`.  
3. Prefer `pip install -e` of `smf-swarm` long-term; path insert is OK for prototype.

## Files

| Repo | File |
|------|------|
| smf-swarm-2.0 | `docs/CONSUMER_SKILLOPT.md` (this file) |
| skillopt-prototype | `swarm_diagnostic_adapter.py` |
| skillopt-prototype | `skillopt_loop.py` (wire) |
| skillopt-prototype | `test_swarm_adapter.py` |
