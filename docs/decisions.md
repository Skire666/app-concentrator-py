# Architecture and technical decisions

Each entry: status, context, decision, alternatives considered, consequences. Add an entry for every
new dependency, thread, file format change or deviation from a spec. Never delete an entry: mark it
superseded.

---

## ADR-001 — Hexagonal layers with a Qt-free presentation layer

- Status: accepted (phase 0).
- Context: widgets must stay dumb and display logic must be testable without opening a window;
  presentation coverage must reach 80 %.
- Decision: `domain` <- `application` <- `presentation` (presenters, snapshots, forms, gating,
  render coordination, no Qt) <- `ui` (Qt widgets: window, panel, widget). Driven adapters in
  `infrastructure`, wiring in `bootstrap`. Enforced by `furryp.json` contracts.
- Alternatives: MVVM with Qt properties in view models (ties logic to Qt); presenters inside `ui`
  (untestable without Qt).
- Consequences: one extra layer and snapshot types per panel; nearly all display logic runs in plain
  pytest.

## ADR-002 — JSON5 for the user data file

- Status: accepted, owner decision (2026-11-06). Not to be reopened.
- Context: the brief requires JSON5, with flat Windows paths and multi-line text.
- Decision: JSON5 stays because it is clearer for a user who reads or edits the file (unquoted keys,
  trailing commas, arrays of lines, flat paths). Alternatives (plain JSON, SQLite) are rejected.
- Known limits, handled without changing the format: hand-written comments are lost at the next
  save (a header comment says so); the `json5` package is pure Python, so it is slower than the
  `json` module; task history makes the file grow.
- Safeguards: codec isolated behind `Json5Codec` and `UserDataFilePort`; history capped
  (`todo.max_history_events`); throughput measured in phase 1 and startup time in phase 8. If a
  target is missed, the remedy is a faster JSON5 decoder behind `Json5Codec`, never another format.

## ADR-003 — Pydantic only for persistence and config DTOs

- Status: accepted.
- Decision: domain entities are frozen dataclasses validated by `*Rules`; pydantic models live in
  `infrastructure/persistence/schemas` and `infrastructure/config` only, `strict=True`,
  `extra="forbid"`. Pipeline: JSON5 text -> `json5.loads` -> `json.dumps` -> `model_validate_json`.
- Consequences: structure/syntax errors (pydantic) and business errors (rules) are reported
  separately, both as error codes; the domain has no third-party dependency.
- Amendment (phase 0): `concentrator.ini` values are all text, so `AppConfigSchema` is validated
  with `model_validate_strings` (`strict=True`, `extra="forbid"`): `"100"` is an int, `"1.5"` is
  not; `missing` maps to `CONFIG_KEY_MISSING`, `extra_forbidden` to `CONFIG_KEY_UNEXPECTED` (3005),
  any other error to `CONFIG_VALUE_INVALID`.

## ADR-004 — MP3 playback with QtMultimedia

- Status: accepted (phase 2).
- Context: play MP3 of any size, in a loop or N times, with volume, while the app is in the
  background.
- Decision: `QMediaPlayer` + `QAudioOutput` from PySide6 (`PySide6-Addons`, already installed by the
  `pyside6` package). It streams files, supports `setLoops` and an infinite loop constant, and runs
  on Qt's event loop. No extra dependency.
- Alternatives: `pygame-ce` mixer (SDL, large, own event loop), `just_playback`/miniaudio (small,
  less known), `playsound` (unmaintained, no volume or loop control).
- Consequences: the audio adapter lives in `infrastructure/qt/`; the frozen build must include the
  multimedia plugins (verified in phase 2 acceptance).

## ADR-005 — Atomic save procedure

- Status: accepted (phase 1).
- Brief: temporary file, rename the old file to backup, rename the new file.
- Decision: write and `fsync` the temporary file, verify its hash, copy the current file to `.bak`,
  then `os.replace(tmp, current)`. The main file therefore always exists and is either the old or
  the new complete version. `os.replace` is retried on `PermissionError` (antivirus, indexer, sync
  clients lock files on Windows).
- Consequences: one file copy per save (small files); recovery logic handles leftover `.tmp`.

## ADR-006 — Synchronous in-memory use cases, one writer thread

- Status: accepted.
- Decision: all use cases run on the UI thread against an in-memory `UserDataStore` (fast); saves
  are debounced and executed by a single `ThreadPoolExecutor(max_workers=1)` on immutable snapshots;
  results return through a queued Qt signal. Flush on quit with a timeout.
- Consequences: no locks in business code; the UI never waits for the disk; at most
  `storage.save_debounce_ms` of changes can be lost on a hard crash.

## ADR-007 — Single instance with QLockFile and QLocalServer

- Status: accepted (phase 0).
- Context: a `QLocalServer` alone is racy on Windows (two processes started together can both
  listen).
- Decision: `QLockFile` (per user, stale-lock aware) decides exclusivity; `QLocalServer` only carries
  the "show yourself" request from the second process. Windows may refuse to steal focus: the first
  instance then flashes its taskbar button.

## ADR-008 — pytest instead of unittest

- Status: accepted.
- Context: the brief lists pytest as a dependency but the pre-commit command used
  `python -m unittest discover`, which cannot run pytest-style tests, fixtures or `pytest-qt`.
- Decision: pytest + pytest-cov + pytest-qt; per-layer thresholds enforced by
  `scripts/coverage_gate.py` because coverage.py only supports one global `fail_under`.

## ADR-009 — Two ini files with distinct roles

- Status: accepted.
- Decision: `concentrator.ini` holds application constants (shipped, next to the exe, read-only at
  runtime, validated into `AppConfig`, missing key = explicit startup error); `ui-state.ini`
  (`QSettings`, `IniFormat`, `%APPDATA%`) holds Qt-only state and the remembered data file path.
- Consequences: tunables change without redeploying; there is no hidden code default that silently
  diverges from the ini.

## ADR-010 — Integer enums with UNKNOWN and UNSET

- Status: accepted.
- Decision: `BaseIntEnum(IntEnum)` with `UNKNOWN=-1`, `UNSET=0`; values explicit, never renumbered
  or reused; `parse()` maps unrecognized integers to `UNKNOWN` so a file written by a newer version
  degrades into a rules error instead of a crash.
- Trade-off: integers make the JSON5 file less self-explanatory than names; accepted for
  stability.

## ADR-011 — Timer state machine clarifications

- Status: proposed (confirm at phase 2 review).
- Decisions on gaps in the brief: a PAUSED state exists (Edit, Reset enabled, Resume); the
  "finished" state shows three buttons (Restart, OK, Snooze 5 min); a duration edited while running
  applies at the next start; favorites start the timer only from IDLE; remaining time is computed
  from the monotonic clock (behaviour after Windows sleep checked manually in phase 2); a running
  countdown is not restored after an app restart.

## ADR-012 — Business copy and technical copy

- Status: accepted.
- Decision: `copy_business` = duplicate with new id, new timestamps, history restarted with a
  `COPIED_FROM` event, stored. `copy_technical` = exact clone (same id, timestamps, history), never
  inserted in the store; used for export, backup and as an undo or `is_dirty` baseline. With
  immutable entities, a technical copy is cheap.

## ADR-013 — Focus queue items always reference tasks

- Status: accepted (phase 7).
- Decision: the quick TODO list holds references to tasks; quick-add creates a real task in the
  quick-add list (Inbox by default). One completion path, one history, recurring tasks handled.

## ADR-014 — Links detected in task text, clickable, never checked

- Status: accepted, owner decision (2026-11-06).
- Decision: URLs (schemes from `links.url_schemes`) and Windows paths on any drive (`C:`, `D:`,
  `E:` ...) or UNC are detected in the text (whole-line rule for paths with spaces), normalized with
  `/` when the task is saved, and rendered as hyperlinks. A click hands the target straight to
  `QDesktopServices.openUrl`, like a double-click in Explorer. No existence, reachability or
  file-type check, no confirmation: if the target does not exist or fails, the user is responsible.
- Only Qt's refusal is reported (`LINK_OPEN_FAILED`, WARNING in the log, no dialog), to respect the
  "no silent failure" rule. Logs never contain the link.
- Accepted consequences: a link to an executable runs it; an unreachable network path can make the
  opening slow.
- Alternative kept for the phase 6 review: a dedicated "Links" field in the editor.

## ADR-015 — Packaging with PyInstaller onedir

- Status: accepted.
- Decision: `--onedir --windowed --noupx`; assets bundled; `concentrator.ini` copied next to the exe
  to stay editable; a self-check run (`CONCENTRATOR_SELF_CHECK=1`) validates the bundle; the
  AppUserModelID is set at startup so the taskbar and notifications show Concentrator.
- Alternatives: `--onefile` (slower start, more antivirus false positives), Nuitka /
  `pyside6-deploy` (compiled, faster start, much longer builds) — possible later.

## ADR-016 — CLAUDE.md imports AGENTS.md

- Status: accepted.
- Context: Claude Code reads `CLAUDE.md`, not `AGENTS.md`.
- Decision: `AGENTS.md` is the single source of truth; `CLAUDE.md` starts with `@AGENTS.md` and only
  adds Claude Code specifics.

## ADR-017 — Tooling adjustments to the initial pyproject

- Status: accepted.
- Changes: project name `concentrato` -> `concentrator` (the build backend looks for a module named
  after the project); `requires-python = ">=3.14,<3.15"` (PySide6 wheels declare `<3.15`); `LICENSE`
  file added (`license-files` requires it); invalid `TODO :: TODO` classifier replaced; ruff also
  lints `tests/` and `scripts/`; rule families added: `ARG`, `DOC`, `DTZ`, `INP`, `PGH`, `PT`,
  `SLF`, `T20`; absolute imports only; basedpyright `pythonPlatform = "Windows"`,
  `reportImplicitOverride`, ignore-comment hygiene; pytest `filterwarnings = ["error"]`;
  `[project.gui-scripts]` entry point without console.
- Amendment (phase 0, owner decision 2026-11-06): ruff 0.17 (preview) adds `rule-codes-in-selectors`,
  which rejects rule codes in `per-file-ignores`, and `noqa-comments`, which replaces `# noqa` with
  `# ruff: ignore[...]`. `pyproject.toml` is removed from ruff's `include` (the codes stay as
  written); `AGENTS.md` rule 14 now names `# ruff: ignore[...]`.
- Amendment (phase 0): `.gitattributes` forces LF on checkout (`* text=auto eol=lf`, binary assets
  excluded), because Git for Windows defaults to `core.autocrlf=true` and ruff formats with LF.

## ADR-018 — Localization details

- Status: accepted.
- Decisions: plain JSON catalogs with dotted keys; dialog buttons use catalog texts so Qt's compiled
  `.qm` translations are not needed; French plural rule (0 and 1 singular); date formats in the
  catalogs, no `locale` module; log messages stay English.

## ADR-019 — Sorting and filtering in presenters

- Status: accepted.
- Decision: presenters filter and sort the in-memory collections and send ready rows to a generic
  `SnapshotTableModel`; no `QSortFilterProxyModel`. Testable without Qt, fast enough for thousands
  of rows.

## ADR-020 — Main window without QMainWindow

- Status: accepted.
- Context: the module bar must span the full height, while the status bar sits under the content.
  `QMainWindow`'s status bar always spans the full width.
- Decision: a top-level `QWidget` with `QHBoxLayout[module bar, QVBoxLayout[pages, status bar]]`.

## ADR-021 — EventBus isolates failing handlers

- Status: accepted (phase 0), owner decision (2026-11-06).
- Context: the phase 0 spec requires that a failing event handler does not stop the other
  handlers, while `AGENTS.md` rule 4 allowed `except Exception` only in the global exception hooks.
- Decision: `EventBus` dispatch catches `Exception` around each handler call, logs it with
  `logger.exception` (ERROR with traceback) and forwards it to `ErrorReporterPort`, the same
  reporter the global hooks use, so the user sees the error dialog. Rule 4 lists exactly two
  places allowed to catch `Exception`: the global exception hooks and `EventBus` dispatch.
- Consequences: a buggy subscriber cannot break unrelated features and its failure is never
  silent. `BaseException` subclasses (`KeyboardInterrupt`, `SystemExit`) still propagate.

## ADR-022 — Layout state through LayoutStateKeeper

- Status: accepted (phase 0), owner decision (2026-11-06).
- Context: Qt layout blobs (window geometry, splitter and header states) must be persisted in
  `ui-state.ini`, but `ui` may not import `application.ports.ViewPreferencesPort`, and the layout is
  not the business of `ShellPresenter`.
- Decision: a reusable presentation component, `presentation/common/layout_state_keeper.py`
  (`load(key) -> str | None`, `save(key, value)`), backed by `ViewPreferencesPort`. Keys are `Final`
  constants in `presentation/common/layout_keys.py`, all prefixed `layout/`; phase 4 "Reset layout"
  removes `layout/*` only, and other UI state (`storage/data_file_path`) never uses that prefix. Qt
  blobs cross the presentation layer as opaque base64 strings: the window encodes them, exports them
  on close (not on every resize) and restores them once before `show()`. A base64 decoding failure or
  a `restoreGeometry` / `restoreState` returning `False` falls back to the ini defaults and logs a
  WARNING. `ui-state.ini` is accessed only through `ViewPreferencesPort` (`AGENTS.md` §7.3, §8.5).
- Consequences: one layout mechanism for every window, page and table (phase 5 header state uses
  it); layout reset is a prefix removal.

## ADR-023 — Action-scoped rendering and action label keys

- Status: accepted (phase 0), owner decision (2026-11-06).
- Context: snapshot equality skips the render, not the build. Rebuilding every section on each
  busy/release transition would rebuild, from phase 5 on, a 2,000-row table snapshot (up to 100 ms)
  twice on every click anywhere. Separately, the phase 0 spec listed `shell.module.*` keys for the
  module buttons, which would duplicate the action labels.
- Decision: `ActionGate` requests only the sections bound to the action, from an explicit mapping in
  `presentation/common/action_sections.py`; a test checks that every `ActionIdEnum` member is mapped.
  `RenderCoordinator.request_all()` is reserved for language changes and data file switches. The key
  `action.<name_lowercase>` (optional `.tooltip`) is the single source of labels for controls bound to
  an action; the module buttons therefore use `action.shell_show_*` instead of `shell.module.*`.
  State-specific texts that are not action labels keep their own keys. `TranslatorPort.has(key)`
  supports the optional tooltip.
- Consequences: a new action must be added to the mapping (enforced by test); the catalog test checks
  one label per action.

## ADR-024 — Startup failure modes and self-check

- Status: accepted (phase 0).
- Decisions:
  - A broken `concentrator.ini` is reported before logging and catalogs exist, in a plain English
    `QMessageBox` naming the file, the error codes and the keys; exit code 1. Its texts are `Final`
    constants in `bootstrap/startup_errors.py` and are the only literal UI texts of the application.
  - The global hooks are installed at step 3 with a `ForwardingErrorReporter`; it forwards to the
    error dialog presenter once the window exists (errors before that are only logged).
  - Single instance: another instance running gives exit code 0 before any window; a lock that cannot
    be created is logged at ERROR and the application runs unguarded (open item for phase 1: two
    instances could then write the same data file).
  - Catalogs that cannot be loaded are logged at ERROR; every text then falls back to its key.
  - `CONCENTRATOR_SELF_CHECK=1` runs steps 1-3 and 5, checks the required assets (ini, catalogs,
    application and module icons), the Qt SVG image plugin and the rendering of the module icons,
    logs the outcome and exits 0 or 1 without a window. With a broken ini it exits 1 without dialog
    (logging is not configured yet).
- Consequences: `scripts/build.py` validates the frozen bundle with the exit code only; the details
  are in the log.

## ADR-025 — Phase 0 naming and tooling details

- Status: accepted (phase 0).
- Decisions:
  - Panels render with `render_snapshot(snapshot)`: `QWidget.render(target, ...)` already exists for
    painting, and overriding it with another signature breaks type checking and Liskov substitution.
  - Pages live in `ui/windows/*_page.py` (window tier); `*_page.py` is added to the ui naming list.
  - The ui cannot import `AppConfig`: the window receives `presentation.shell.ShellLayout`, built by
    bootstrap from the `[ui]` section.
  - `scripts/build.py` runs `python -m PyInstaller` in a subprocess instead of calling
    `PyInstaller.__main__.run`: PyInstaller ships no type information, and strict type checking would
    need suppressions.
  - The catalog test checks every plain string literal of `presentation/` and `ui/` that looks like a
    key of a catalog family; keys built from enums (`error.<code>`, `action.<action>`) are checked
    member by member.
  - `ValidationResult` carries a `baseline` (`SUCCESS` or `SKIPPED`) so that `skipped()` needs no
    issue and merging follows the worst-severity rule.
