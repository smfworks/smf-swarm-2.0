# Product App v0.4

**Date:** 2026-07-13  

## Sequence delivered

1. **Charts** — CSV numeric columns → sparklines (SVG) in report UI/API  
2. **Auth + share links** — optional `SMF_SWARM_API_TOKEN`; public `/share/{id}` + signed `/r/{run_id}?s=`  
3. **Install polish** — `INSTALL.md`, `LICENSE`, `MANIFEST.in`, PyPI classifiers/URLs, version **0.4.0**

## Verify

```bash
pip install -e ".[dev]"
pytest -q
smf-swarm analyze -q "Outlook?" -d fixtures/sample_growth.csv --mode mock
smf-swarm serve --port 8790
```
