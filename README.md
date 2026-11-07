# Concentrator

A local, single-window desktop application for Windows 11 that combines a countdown timer with alarms,
timer favorites, an hourly chime, a focus queue and a TODO list manager. Python 3.14, PySide6.

Status: phase 1 (user data persistence). On top of the phase 0 shell (configuration, logging, English
and French, single instance, packaging), the TOML data file is chosen at first launch, saved
atomically, recovered after a crash or damage, and watched for outside edits; the features arrive
phase by phase (see [docs/specs/README.md](docs/specs/README.md)).

## Quick start

Prerequisites: Git, [uv](https://docs.astral.sh/uv/) (`winget install --id astral-sh.uv -e`), the
`furryp` CLI on `PATH` (quality gate).

```powershell
uv python install 3.14
uv sync
uv run concentrator                 # the application, without a console window
uv run python -m concentrator       # the same, from a terminal (debugging)
uv run python scripts/check.py      # every quality gate
uv run python scripts/build.py      # dist/Concentrator/Concentrator.exe + self-check
```

## Documentation

| File | Content |
|---|---|
| [USAGE.md](USAGE.md) | What the application does today and where it keeps its files |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Workflow, gates, commits |
| [AGENTS.md](AGENTS.md) | Architecture and coding rules (single source of truth) |
| [docs/decisions.md](docs/decisions.md) | Architecture decision records |
| [docs/specs/](docs/specs/) | Phase specifications |
| [docs/reviews/](docs/reviews/) | Phase review reports |

## License

[The Unlicense](LICENSE).
