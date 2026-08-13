# Contributing to SMF Swarm

Thanks for helping harden the platform core.

## Setup

```bash
git clone https://github.com/smfworks/smf-swarm-2.0.git
cd smf-swarm-2.0
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -U pip
pip install -e ".[dev]"
```

## Checks (same as CI)

```bash
ruff check src tests scripts
pytest -q
```

Use **mock** mode in tests and CI. Do not call live LLM endpoints from unit tests.

## Pull requests

1. Branch from `main`. Prefer `fix/…`, `docs/…`, `test/…`, `ci/…`, `chore/…`.
2. Conventional commits (`fix:`, `docs:`, `test:`, `ci:`, `chore:`).
3. Keep docs in lockstep with CLI / API / UI changes (`README.md`, `INSTALL.md`, `AGENTS.md`).
4. Do not add product features in a hardening PR. Do not commit secrets, `.env`, or history JSONL.
5. Do not force-push `main` or rewrite published history.

## Scope

This repo is the **public platform core**. Commercial verticals live in private repos. Do not claim HBHC, multi-tenant SaaS, or later platform phases for the 0.5 line.

## License

By contributing you agree your work is licensed under the MIT License in `LICENSE`.
