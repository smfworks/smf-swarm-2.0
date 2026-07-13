# Product App v0.3 — Quality Sprint

**Status:** Implemented  
**Date:** 2026-07-13  

## Delivered

1. **Result UX** — prediction headline + full detail; scenario %; loading bar; run meta; copy JSON/MD; download MD  
2. **Evidence binding** — `evidence[]` with source/excerpt/claim from attachments + derived insights  
3. **Methodology strip** — personas, pipeline, model, limitations, fallback flag  
4. **Run history** — local JSONL (`SMF_SWARM_HISTORY` or `~/.local/share/smf-swarm/history.jsonl`)  
5. **Hardening** — robust LLM JSON parse; mock fallback on LLM failure with UI warning  

## Verify

```bash
pip install -e ".[dev]"
pytest -q
smf-swarm serve --port 8790
```

Restart the server after upgrade so static assets reload.
