# Product App v0.2 — Standalone Swarm Predictive Analysis

**Status:** Implemented (first shippable slice)  
**Date:** 2026-07-13  
**Package:** `smf-swarm` ≥ 0.2.0

## Vision

A **downloadable, agent-installable application** that end users open in a browser to:

1. Ask a predictive / decision question  
2. Attach data files (CSV, JSON, TXT, MD)  
3. Receive a structured **predictive analysis** produced by a governed multi-persona swarm  

AI agents (like Hermes) can install and run it the same way as SkillOpt-style packages:

```bash
pip install -e ".[app]"
smf-swarm serve --host 127.0.0.1 --port 8787
# or headless:
smf-swarm analyze --question "..." --data path/to/file.csv
```

## In scope (v0.2)

- FastAPI app + static stylish UI  
- Question + multi-file attach  
- Offline **mock swarm** analysis (always works)  
- Optional **LLM swarm** via OpenAI-compatible endpoint  
- Governance: identity + audit chain on analysis runs  
- CLI: `serve`, `analyze`, `diagnose`  

## Out of scope (later)

- Multi-tenant SaaS auth  
- HBHC crypto  
- Full Council of 18 personas  
- PDF/Office binary parse beyond text extraction  
- Mobile native apps  

## Architecture

```
UI / CLI
   ↓
FastAPI  POST /api/analyze
   ↓
PredictiveSwarmEngine
   ├─ Scout (evidence from attachments)
   ├─ Strategist (scenarios)
   ├─ Skeptic (risks / confounds)
   └─ Forecaster (prediction + confidence)
   ↓
Governance audit + JSON report
```

## Success criteria

- [x] `pip install -e ".[app]"` works  
- [x] UI loads; analyze without LLM returns structured report  
- [x] CLI analyze works offline  
- [x] Tests cover engine offline  
- [x] Docs updated in lockstep  
