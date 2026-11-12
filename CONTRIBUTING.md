# Contributing

[AGENTS.md](AGENTS.md) is the operating manual for humans and coding agents: architecture, dependency
map, conventions, gates. This file summarizes the workflow and the recurring recipes.

## Setup

Prerequisites: Windows 11, Git, [uv](https://docs.astral.sh/uv/) (`winget install --id astral-sh.uv -e`),
VS Code, and the `furryp` CLI on `PATH`.

```powershell
uv python install 3.14
uv sync
```

VS Code: install the recommended extensions (`.vscode/extensions.json`); Pylance stays disabled, the
type checker is basedpyright. The interpreter is `.venv\Scripts\python.exe`.

## Gates

Run them before every commit, and never commit when one fails:

```powershell
uv run python scripts/check.py
```

It runs, in order and stopping at the first failure: `ruff format`, `ruff check`, `basedpyright`,
`furryp check concentrator`, `pytest` with coverage, and `scripts/coverage_gate.py` (branch coverage per
layer: domain 80 %, application 75 %, presentation 70 %, overall 70 %). Never weaken `furryp.json`, the
lint/type settings or the coverage thresholds to make a gate pass. Check the exit code: piping the
output through another command hides it.

## Workflow

1. Work phase by phase ([docs/specs/README.md](docs/specs/README.md)) on a branch
   `phase-<n>-<slug>`. Never implement a later phase's feature.
2. Start a phase with a written plan; wait for approval before editing files.
3. Write tests with the code. Every bug fix starts with a failing test.
4. Small commits in Conventional Commits style (`feat(timer): ...`, `fix(storage): ...`, `test(...)`,
   `docs(...)`, `refactor(...)`, `perf(...)`, `chore(...)`).
5. Update [USAGE.md](USAGE.md) for user-visible behavior and [docs/decisions.md](docs/decisions.md) for
   every decision or deviation from a spec.
6. At the end of a phase, write the review report in `docs/reviews/phase-<n>.md` and stop until the
   phase is accepted (tag `phase-<n>-accepted`).

## Recipes

### Add an error code

1. Add the member to `concentrator/domain/common/error_code_enum.py` in the range of its family (`1xxx`
   common, `2xxx` storage, `3xxx` config and i18n, `4xxx` timer, `5xxx` todo, `6xxx` focus, `7xxx` system).
   Never renumber or reuse a value.
2. Add `error.<name_lowercase>` to `assets/i18n/en.json` and `fr.json`, with the same placeholders: say
   what happened and what to do.
3. Return it from a `*Rules` class or an adapter in a `ValidationResult` / `DataResult`; never raise it.
4. Write a test that produces it (`tests/architecture/test_error_code_tests.py` fails otherwise). A field
   of the data file also needs a `field.<path>` label for the recovery dialog.

### Add an enum

Create `<name>_enum.py` with `class <Name>Enum(BaseIntEnum)`, `UNKNOWN = -1`, `UNSET = 0` and explicit
values from 1; never renumber. Read stored values with `<Name>Enum.parse(value)`, which gives `UNKNOWN`
for a value it does not know, and reject `UNKNOWN` and `UNSET` in the rules where a real value is
needed. `tests/architecture/test_enum_conventions.py` checks the conventions.

### Add a user-visible text

1. Add the key to both catalogs (`assets/i18n/en.json`, `fr.json`): dotted, flat, same placeholders. The
   label of a button or menu item bound to an action is `action.<action_name_lowercase>` (optional
   `.tooltip`).
2. Translate it in the presentation layer (`TranslatorPort.tr` / `tr_plural`) and pass the text in a
   snapshot; widgets never translate.
3. A field caption or a dialog button may mark an Alt letter with `&`: add its key to the right window in
   `tests/architecture/test_mnemonics.py` and choose a letter unused in that window, in both languages.
   Bind the caption with `bind_caption` and show it with `set_caption` (`ui/support/mnemonics.py`).

### Add a setting of concentrator.ini

1. Add the key, with a comment giving its meaning and allowed values, to `assets/config/concentrator.ini`.
2. Add the field to the section dataclass of `concentrator/application/common/app_config.py`, to the
   pydantic schema of `concentrator/infrastructure/config/app_config_schema.py` with its bounds (`Field`),
   and to the section mapping of `ini_config_loader.py` when the section has one.
3. Give the test fakes a value (`tests/fakes/app_config_factory.py`) and document the key in the phase
   spec and, if users may change it, in `USAGE.md`. There are no code-level defaults: a missing key stops
   the start with a message.

### Change the data file format

Additive fields need defaults. A breaking change bumps `CURRENT_SCHEMA_VERSION`, appends a
`SchemaMigration` to the `MigrationChain` of `concentrator/infrastructure/persistence/migrations/`, adds
a reference file for the new version next to `tests/data/schema-v1.toml`, and gets an entry in
`docs/decisions.md`.

## Release

1. Set the version in `pyproject.toml`, run `uv lock`, and add the release to `CHANGELOG.md`.
2. Run the gates, then `uv run python scripts/build.py --release`: it builds `dist/Concentrator/`, checks
   it with the frozen self-check and writes `dist/Concentrator-<version>-win64.zip`.
3. Optionally measure with `uv run python scripts/bench_app.py --startup --exe dist/Concentrator/Concentrator.exe`.
4. Run the smoke test of the phase 8 spec on a Windows 11 account without Python, then tag `v<version>`.

## Useful scripts

| Command | Purpose |
|---|---|
| `uv run python scripts/check.py` | All gates |
| `uv run python scripts/build.py [--release]` | PyInstaller build in `dist/Concentrator/`, frozen self-check, release zip |
| `uv run python scripts/bench_app.py [--startup [--exe <path>]]` | Save, read, table, search and startup times on 1,000 tasks |
| `uv run python scripts/bench_storage.py` | TOML and pipeline throughput; `--seed-tasks N --into <copy>` adds tasks to a data file |
| `uv run python scripts/clean.py [--dry-run]` | Delete `build/`, `dist/`, caches, coverage files |
| `python scripts/clean.py --all` | Also delete `.venv/` (run it with a Python from outside `.venv`) |

The application accepts no command-line option. `CONCENTRATOR_SELF_CHECK=1` (environment variable)
validates an installation and exits with 0 or 1 without showing a window.
