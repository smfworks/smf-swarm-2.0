# Phase 1 Dogfood Findings

**Date:** 2026-07-13  
**Owner:** Aiona Edge  

## What we ran

```bash
python -m smf_swarm.pipeline.phase1_run \
  --agent-name skillopt-dogfood-agent \
  --domain article_editing \
  --fixture fixtures/skillopt_edit_planning_trajectories.json \
  --audit data/dogfood-audit.jsonl   # local / gitignored
```

Fixture source: SkillOpt **edit planning** criteria + anonymized success/fail trajectory text aligned with known prototype failure modes (hypothesis prioritization, risk, executability).

## Results

| Check | Result |
|--------|--------|
| Pipeline completed | Yes |
| Audit hash chain valid | Yes |
| Gaps returned (mock) | 4 |
| Unauthorized path | Covered by unit tests (`PermissionDenied` without grant) |

**Top diagnosed gaps (mock backend):**

1. **Hypothesis Prioritization** (0.70)  
2. **Executable Planning** (0.70)  
3. **Risk Assessment** (0.70)  
4. **Evidence Grounding** (0.70)  

Suggested criteria mapped cleanly to SkillOpt triage/plan rubrics (T1, T2, P1-style questions).

**Audit trail actions observed:**  
`identity.register` → `permission.grant` → `permission.check` → `diagnostic.start` → `diagnostic.complete`

## Useful or not?

**Useful — with caveats.**

| What worked | What didn’t (yet) |
|-------------|-------------------|
| Governance path is real: no diagnose without grant; chain integrity | Mock backend is keyword-heuristic, not deep LLM contrastive analysis |
| Gaps align with known SkillOpt failure modes | Coverage scores clustered (0.7) — less discriminative than LLM diagnosis |
| Fixture + CLI is a reproducible dogfood path | Trajectories hand-authored from criteria (not a live SkillOpt rollout dump) |
| Criteria text immediately usable in SkillOpt validation | Live LLM quality covered in `MOCK_VS_LLM.md` |

**Verdict:** Phase 1 surface is good enough to build on. Mock diagnostic is valuable for CI and offline demos; production insight should use the LLM backend when available.

## Implications

1. Do not block on HBHC crypto until there is a durable identity need + consumer.  
2. Prefer exporting real SkillOpt epoch trajectories before a second major dogfood.  
3. Keep governance hooks mandatory on every diagnostic entrypoint.
