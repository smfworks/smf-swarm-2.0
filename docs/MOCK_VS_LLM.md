# Mock vs LLM Diagnostic Comparison

**Date:** 2026-07-13  
**Owner:** Aiona Edge  
**Fixture:** `fixtures/skillopt_edit_planning_trajectories.json`  
**LLM:** `unsloth/Qwen3.6-35B-A3B-NVFP4` @ `http://spark-56bc:8888/v1`  
**Runner:** `scripts/compare_mock_vs_llm.py`  
**Local artifact (gitignored):** `data/mock_vs_llm_comparison.json`

---

## Setup

| Backend | Role |
|---------|------|
| **Mock** | Keyword-heuristic offline backend (CI) |
| **LLM** | DGX Spark vLLM, compact prompt |

Early LLM attempts failed due to:

1. Truncation (`finish_reason=length`) on long reasoning + verbose JSON  
2. Brittle JSON parse  

**Fix that worked:** shorter trajectories in prompt, exactly 3 gaps, higher token budget, robust array / `raw_decode` parsing, coerce `failure_coverage` when models return prose.

---

## Side-by-side results

### Mock (4 gaps, coverage ~0.7 each)

| Gap | Suggested criterion |
|-----|---------------------|
| Hypothesis Prioritization | At most 3 ranked hypotheses? |
| Executable Planning | Steps concrete and ordered? |
| Risk Assessment | Explicit risk analysis section? |
| Evidence Grounding | Claims tied to cited evidence? |

### LLM (3 gaps; stronger criteria text)

| Gap | Suggested criterion |
|-----|---------------------|
| Impact Prioritization | Limit to top 3 highest-impact changes; reject low-impact with rationale |
| Executable Edit Specification | Every step: section anchors + original text + replacement |
| Risk & Dependency Analysis | Dependency map; structural changes before content refinements |

### Theme overlap

| Mock themes | LLM themes | Overlap |
|-------------|------------|---------|
| prioritization, executable_plan, risk, evidence | prioritization, executable_plan, risk, dependencies, ordering, specificity | **prioritization, executable_plan, risk** |

Names do not match string-for-string; **themes strongly align**. LLM adds dependency ordering and specificity.

---

## Quality judgment

| Dimension | Winner | Notes |
|-----------|--------|-------|
| Offline/CI reliability | **Mock** | Deterministic, no network |
| Criterion actionability | **LLM** | Longer, SkillOpt-ready questions |
| Coverage discrimination | Mixed | Mock flat 0.7; LLM may emit prose coverage (now coerced when possible) |
| Directional usefulness | **Both** | Same core failure modes as SkillOpt T1/T2/P1 |

---

## Recommendation (locked)

1. **CI / unit tests:** always `MockCapabilityBackend`  
2. **Production diagnosis:** `LLMCapabilityBackend` when Spark/OpenAI-compatible endpoint is up  
3. **SkillOpt criteria generation:** prefer **LLM `suggested_criterion`** text  
4. **Ops:** keep compact prompts for reasoning models; prefer complete JSON finishes (`finish_reason=stop`)  
5. **Phase 2 crypto** is not blocked on perfect coverage scores — dual path is good enough

## How to re-run

```bash
pip install -e ".[llm]"
# The runner auto-discovers the endpoint's sole served model.
python scripts/compare_mock_vs_llm.py
# For another endpoint or one that serves multiple models, set explicit overrides:
SMF_SWARM_EVAL_BASE_URL=http://127.0.0.1:8000/v1 \
  SMF_SWARM_EVAL_MODEL=your-model python scripts/compare_mock_vs_llm.py
```

The runner accepts only absolute HTTP(S) endpoint URLs and rejects username/password
userinfo, query strings, fragments, surrounding whitespace, and control characters so
credentials and terminal-control sequences cannot reach requests, JSON artifacts, or
console output. Explicit and discovered model IDs are limited to 256 characters and
reject control or formatting characters. A live run succeeds only when the endpoint
returns exactly three distinct, structurally valid gaps; every other cardinality or
malformed result is recorded and exits nonzero.

**Verdict:** Dual-path diagnostic strategy confirmed. Mock for gates; LLM for insight.
