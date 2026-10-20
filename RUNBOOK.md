# Runbook

Procedures for DataIntake. `README.md` describes what each command does; this file says when
to run it and in what order.

## On open

```bash
git status --short
git log -3 --oneline
```

## On close

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src/
uv run pytest -q
```

## Run

`uv run intake demo`, then `uv run intake audit demo_exports/shop` and open the report. For a
client's files, point `audit` at their folder with `--client` and `--as-of`; add
`--hide-examples` if the report will travel beyond them.

## Change a check

1. Add the case to the planted answer key in `src/data_intake/demo.py` if the demo exports
   should show it, or to the check's own test file otherwise.
2. `uv run pytest`. The recall test fails on any planted issue that is missed and on any
   clean column that is flagged.
3. `uv run intake site` and read the sample audit the change touches.

## Release

Follows `~/developer/hq/CONVENTIONS.md` §Versioning.

1. Bump `version` in `pyproject.toml` and `__version__` in `src/data_intake/__init__.py`,
   then `uv lock` (CI installs with `--locked`).
2. Commit `chore: Release vX.Y.Z`, tag `git tag -a vX.Y.Z`, push `main` and the tag.
3. `gh release create vX.Y.Z` with handwritten notes; mark it latest.

## Deploy

Nothing by hand. Every push to `main` runs CI (lint, tests, site build from synthetic data)
and deploys the site to GitHub Pages. `gh run list --limit 3` shows whether it landed.

## Restore on a new machine

1. Clone the repo, `uv sync`.
2. `uv run pytest`, then `uv run intake demo`. There are no keys and no downloads.

## Validate

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy src/
uv run pytest
uv run intake site
python3 ~/.claude/scripts/doc-check.py --repo .
```
