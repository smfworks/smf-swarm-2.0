# Operator path — GitHub Actions workflow

The hardening PAT cannot push `.github/workflows/` (no `workflow` scope).

The CI file is committed locally on `harden/smf-swarm-2.0`:

`.github/workflows/ci.yml`

## How to land it

1. Open the PR from this branch (code, tests, docs push normally).
2. Either:
   - Add the `workflow` scope to the PAT and push the file, or
   - Paste `.github/workflows/ci.yml` via the GitHub web editor on the same branch, or
   - Merge the branch and add the workflow on `main` via the Actions UI / web editor.
3. Do not force-push. Do not rewrite history.

After the workflow exists on GitHub, Actions should run ruff, mypy, pytest, and the mock CLI smoke on Python 3.10 and 3.12.
