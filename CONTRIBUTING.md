# Contributing

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Gates (run before you push)

```bash
ruff check src tests
mypy src
pytest -q
smf-swarm analyze -q "Smoke test" -d fixtures/sample_growth.csv --mode mock
```

Unit tests stay **offline / mock**. Do not add network-required tests.

## Docs

Change CLI, API, or UI behavior in the same commit as README / `docs/` / CHANGELOG. `docs/PHASE1_DOD.md` is a historical lock — do not rewrite its original 6-test checkbox as today's count.

## Git

- Branch from `main` as `harden/<topic>` or `feat/<topic>`.
- Conventional commits. Professional language only.
- This repo is the **public platform core**. Do not commit commercial vertical code here.

## Security

Do not weaken allowlists, share-secret fail-closed behavior, or URL validation to make a test pass. See `SECURITY.md`.
