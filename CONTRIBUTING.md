# Contributing

Work in this public platform core only. Do not change private vertical repos from here.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
ruff check src tests
mypy src
pytest -q
smf-swarm analyze -q "Will demand grow?" --mode mock
```

- Conventional commits.
- Keep unit tests offline / mock.
- Update docs when CLI, API, or UI behavior changes.
- Do not flip optional auth to required in this repo.
