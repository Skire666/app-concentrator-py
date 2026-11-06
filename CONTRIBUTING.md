# Contributing

[AGENTS.md](AGENTS.md) is the operating manual for humans and coding agents: architecture, dependency
map, conventions, gates. This file only summarizes the workflow.

## Setup

```powershell
uv python install 3.14
uv sync
```

VS Code: install the recommended extensions (`.vscode/extensions.json`); Pylance stays disabled, the
type checker is basedpyright.

## Workflow

1. Work phase by phase ([docs/specs/README.md](docs/specs/README.md)) on a branch
   `phase-<n>-<slug>`. Never implement a later phase's feature.
2. Start a phase with a written plan; wait for approval before editing files.
3. Write tests with the code. Every bug fix starts with a failing test.
4. Run the gates before every commit:

   ```powershell
   uv run python scripts/check.py
   ```

   It runs, in order and stopping at the first failure: `ruff format`, `ruff check`, `basedpyright`,
   `furryp check concentrator`, `pytest` with coverage, and `scripts/coverage_gate.py` (per-layer
   thresholds). Never weaken `furryp.json`, the lint/type settings or the coverage thresholds to make
   a gate pass.
5. Small commits in Conventional Commits style (`feat(timer): ...`, `fix(storage): ...`, `test(...)`,
   `docs(...)`, `refactor(...)`).
6. Update [USAGE.md](USAGE.md) for user-visible behavior and [docs/decisions.md](docs/decisions.md) for
   every decision or deviation from a spec.
7. At the end of a phase, write the review report in `docs/reviews/phase-<n>.md` and stop until the
   phase is accepted (tag `phase-<n>-accepted`).

## Useful scripts

| Command | Purpose |
|---|---|
| `uv run python scripts/check.py` | All gates |
| `uv run python scripts/build.py` | PyInstaller build in `dist/Concentrator/` and frozen self-check |
| `uv run python scripts/clean.py [--dry-run]` | Delete `build/`, `dist/`, caches, coverage files |
| `python scripts/clean.py --all` | Also delete `.venv/` (run it with a Python from outside `.venv`) |

The application accepts no command-line option. `CONCENTRATOR_SELF_CHECK=1` (environment variable)
validates an installation and exits with 0 or 1 without showing a window.
