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
