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

- Status: superseded by ADR-035 (owner decision, 2026-11-07). Accepted, owner decision (2026-11-06).
- Context: the brief requires JSON5, with flat Windows paths and multi-line text.
- Decision: JSON5 stays because it is clearer for a user who reads or edits the file (unquoted keys,
  trailing commas, arrays of lines, flat paths). Alternatives (plain JSON, SQLite) are rejected.
- Known limits, handled without changing the format: hand-written comments are lost at the next
  save (a header comment says so); the `json5` package is pure Python, so it is slower than the
  `json` module; task history makes the file grow.
- Safeguards: codec isolated behind `Json5Codec` and `UserDataFilePort`; history capped
  (`todo.max_history_events`); throughput measured in phase 1 and startup time in phase 8. If a
  target is missed, the remedy is a faster JSON5 decoder behind `Json5Codec`, never another format.
- Measurement (phase 1, `scripts/bench_storage.py`, 5.06 MB task-shaped document, `json5` 0.17.3):
  `json5.loads` 30.6 s (0.17 MB/s), `json5.dumps` 0.63 s (8.0 MB/s); the same data as plain JSON
  loads with `json.loads` at about 290 MB/s. Reading is the bottleneck; the choice of a faster JSON5
  decoder is a phase 1 review question.

## ADR-003 — Pydantic only for persistence and config DTOs

- Status: accepted.
- Decision: domain entities are frozen dataclasses validated by `*Rules`; pydantic models live in
  `infrastructure/persistence/schemas` and `infrastructure/config` only, `strict=True`,
  `extra="forbid"`. Pipeline: JSON5 text -> `json5.loads` -> `json.dumps` -> `model_validate_json`
  (since ADR-035: TOML text -> `tomllib.loads` -> `json.dumps` -> `model_validate_json`).
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
  `storage.save_debounce_ms` of changes can be lost on a hard crash (superseded by the amendment).
- Amendment (phase 1, owner decision 2026-11-06): the debounce is trailing with a maximum delay
  (ADR-029). At most `storage.save_max_delay_ms` of changes can be lost on a hard crash. Startup
  writes also run on the writer thread (ADR-028).

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
- Amendment (phase 1): the open item of unguarded mode is closed by ADR-031 (visible warning) and
  ADR-033 (external modification check).

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

## ADR-026 — Two-stage logging startup

- Status: accepted (phase 0), owner decision (2026-11-06).
- Context: the spec configured logging (step 3) before the single-instance decision (step 4), so a
  second launch opened the same rotating log file as the running instance. Rotation renames the file;
  on Windows that fails while another process holds it open, and with `sys.stderr = None` in the
  frozen exe the failure would be lost.
- Decision: logging starts in two stages. `configure_logging` installs the root level, the journal
  ring buffer, the optional stream handler, `captureWarnings` and a `logging.handlers.MemoryHandler`
  without target; it creates no folder and opens no file. Once this process holds the lock,
  `LoggingRuntime.attach_log_file()` creates the `RotatingFileHandler`, flushes the buffered startup
  records into it (oldest first), attaches it and opens the `faulthandler` file. A second launch that
  hands over to the running instance exits without ever opening the log file; its few records live
  only in its memory (and on the console when there is one). In unguarded mode (the lock cannot be
  created) the file is attached as before; phase 1 adds a visible warning for that case. The
  self-check attaches the file right after step 3.
- Consequences: the running instance is the only writer of the log file, so rotation works; the
  diagnostics of a second launch are not kept.

## ADR-027 — Data file startup resolution and recovery

- Status: accepted (phase 1), owner decisions (2026-11-06).
- Context: the phase 1 spec names the startup steps (`READY`, `NEEDS_LOCATION`, `NEEDS_RECOVERY`,
  `FATAL`) without the full matrix. Three cases had no fitting action: a valid main file with a newer
  `.tmp` ("start empty" would be wrong), a remembered file that is missing (a removable or network
  drive may not be connected yet), and a file that is locked or written by a newer version (it must
  never be quarantined).
- Decision:
  - The storage startup runs after the catalogs (phase 0 step 5), not right after step 4, because
    its dialogs are translated. Until the data file is loaded they use the language hint
    `shell/language_hint` of `ui-state.ini` (an ISO code written at every language change, outside
    the `layout/` prefix), else `i18n.default_language`. Once loaded, the data file is the source of
    truth and the hint follows it.
  - `resolve_startup` inspects the main file, `<file>.tmp` and `<file>.bak`:

    | Situation | Step | Actions |
    |---|---|---|
    | no remembered path | `NEEDS_LOCATION` | use the file found at the default location (only if it exists), create at the default location, create elsewhere, open existing, quit |
    | remembered file absent, no valid `.tmp`/`.bak` | `NEEDS_LOCATION` + "file not found" notice | the same, plus Retry; the file is never recreated silently |
    | main valid, valid `.tmp` with a newer `saved_at` | `NEEDS_RECOVERY` | restore the `.tmp`, keep the current file, quit |
    | main valid, otherwise | `READY` | — |
    | main damaged (encoding, syntax, structure or rule errors), or absent with a valid `.tmp`/`.bak` | `NEEDS_RECOVERY` | restore a candidate (newest `saved_at` first, `.tmp` first on a tie), choose another file, start with an empty file, quit; Retry too when the main file is absent |
    | main unreadable (2002) | `FATAL` | Retry, choose another file, quit |
    | main written by a newer version (2009) | `FATAL` | choose another file, quit |

  - Restore quarantines a damaged main first (`<file>.corrupt-YYYYMMDD-HHMMSS`), then writes the
    candidate as the new main through the atomic writer, so the `.bak` being restored is never
    overwritten by the damaged file. Restoring a newer `.tmp` over a valid main is a normal save
    (the main file goes to `.bak`).
  - "Keep the current file" renames the stale `.tmp` to `<file>.tmp.discarded-YYYYMMDD-HHMMSS`;
    otherwise the same question would come back at every start.
  - "Retry" runs the resolution again (a lock released, a drive connected, a file put back).
    Amendment (phase 1 review, 2026-11-07): Retry is also offered when the main file is absent
    but a `.tmp` or `.bak` remains (a file renamed, moved or being restored by a sync client);
    the manual test found it missing. Creating a data file puts aside a leftover `.tmp`/`.bak`, and
    restore refuses a main file that became `FATAL` (ADR-037).
  - Renamed files carry the local date and time. A `FATAL` file is never renamed or written.
  - The remembered path `storage/data_file_path` is written only after a successful open or create.
- Consequences: phase 4 "Use another file" reuses the same inspection for any path.

## ADR-028 — Every user-data write on the writer thread

- Status: accepted (phase 1).
- Context: rule 11 puts every user-data disk write on the single writer thread, and startup writes
  (create, restore, quarantine, discard the `.tmp`) happen before the event loop runs.
- Decision: every write, including the startup ones, is a job of the single writer thread
  (`ThreadPoolExecutor(max_workers=1, thread_name_prefix="writer")`). Debounced saves return through
  `MainThreadDispatcherPort`. Synchronous writes (startup, shutdown flush) block the main thread for at
  most `storage.blocking_write_timeout_ms` (new key) or `storage.shutdown_flush_timeout_ms`, then
  report `STORAGE_FLUSH_TIMEOUT`. A job that raises unexpectedly is read from `future.exception()`
  (no `except Exception`), logged CRITICAL with its traceback, forwarded to `ErrorReporterPort` and
  converted to `STORAGE_WRITE_FAILED`. Reads (load, probe) run on the main thread.
- Consequences: two writes never race on the same file, at startup as well. Amendment (ADR-037):
  shutting the writer down waits for its jobs, so the instance lock is released after the last write.

## ADR-029 — Save debounce with a maximum delay

- Status: accepted (phase 1), owner decision (2026-11-06).
- Decision: each change restarts a `storage.save_debounce_ms` timer; a second timer, started by the
  first unsaved change and never restarted, forces the save after `storage.save_max_delay_ms` even if
  changes keep coming. The configuration rejects `save_max_delay_ms < save_debounce_ms`
  (`CONFIG_VALUE_INVALID`). One save is in flight at a time; if the revision changed meanwhile,
  another save follows. A failed save keeps the data in memory, sets `FAILED` and retries every
  `storage.failed_save_retry_ms`, except for `STORAGE_FILE_CHANGED_EXTERNALLY` (ADR-033).
- Alternatives: a fixed window (one write per period: more writes for a burst of changes); a pure
  trailing debounce (no bound on the delay under continuous changes).
- Consequences: a burst of 20 toggles gives one to three writes; at most `save_max_delay_ms` of
  changes are lost on a hard crash (ADR-006 amendment).

## ADR-030 — Whole-second wall-clock timestamps

- Status: accepted (phase 1), owner decision (2026-11-06).
- Context: the file stores `YYYY-MM-DDTHH:MM:SSZ`. With microseconds in memory, a save and reload
  would change every entity, and an `is_dirty` comparison against reloaded data would always fail.
- Decision: `SystemClock.now_utc()` and `now_local()` drop the microseconds; `monotonic()` keeps full
  precision (timer engine, action gate). `ClockPort.to_local(moment)` converts a UTC instant to local
  time, so presenters format "Saved at" through the port and stay deterministic in tests. The writer
  always writes whole seconds; the reader accepts any ISO 8601 instant and the rules require UTC.
- Consequences: timestamps created in the same second are equal; ordering ties fall back to ids
  (UUIDv7 ids are time-ordered).

## ADR-031 — Visible warning when single-instance protection is off

- Status: accepted (phase 1), owner decision (2026-11-06). Closes the ADR-024 open item.
- Decision: when the instance lock cannot be created (unguarded mode), the user sees a modal warning
  right after the catalogs load, before any data file is opened, and a status bar indicator with an
  explanatory tooltip for the whole session. Nothing is shown when only the local server fails: the
  lock still protects, and that case stays a WARNING in the log. The external modification check
  (ADR-033) also detects the saves of a second instance.

## ADR-032 — Flushing pending changes on close, quit and session end

- Status: accepted (phase 1), owner decisions (2026-11-06).
- Context: the spec asks for "Quit without saving?" / "Retry" when the shutdown flush fails, but
  `aboutToQuit` cannot cancel the quit. On Windows logoff or shutdown, `aboutToQuit` can arrive too
  late, and Qt 6 has no fallback session management that would close the windows first.
- Decision: `MainWindow.closeEvent` asks the shutdown presenter, which flushes synchronously
  (`storage.shutdown_flush_timeout_ms`); on failure it asks "Quit without saving" / "Retry", and
  Retry keeps the window open. `QGuiApplication.commitDataRequest` (session end) and `aboutToQuit`
  (fallback) run the same synchronous flush without dialog when changes are still pending.
- Consequences: a failed save on the normal quit path is never silent; on session end the result
  is only logged. Amendment (ADR-037): the session end flush keeps saving on, in case the session
  end is cancelled.

## ADR-033 — External modification of the data file

- Status: accepted (phase 1), owner decision (2026-11-06).
- Context: JSON5 was chosen so that users read and edit the file (ADR-002; TOML since ADR-035, same
  reason). A hand edit while the
  application runs is therefore an expected case, in guarded mode too; so is the save of a second,
  unguarded instance. A blind save would erase it silently.
- Decision:
  - The file adapter keeps a fingerprint of the main file (size, `mtime_ns`, SHA-256) after each load
    and each save.
  - On the writer thread, right before the `.bak` copy and the replace, it compares the fingerprint
    with the file on disk. Another size is a change. With the same size the SHA-256 decides:
    `mtime_ns` is never trusted to prove the file unchanged, because an edit made within the timestamp
    granularity of the previous save can keep the same value (found by a flaky test during phase 1).
    A sync client or antivirus touching the file without changing it is therefore not a conflict (the
    fingerprint is refreshed). The cost is one read and hash of the file per save, on the writer
    thread.
  - If the content changed, nothing is written (the verified `.tmp` is deleted) and the save fails
    with `STORAGE_FILE_CHANGED_EXTERNALLY` (2021). The save state is `FAILED` without automatic retry;
    later changes in Concentrator stay in memory and no save is attempted until the user decides.
  - A dialog asks: "Reload the file (changes made in Concentrator since the last save are lost)" or
    "Keep Concentrator's version (overwrite the file)". Reload runs the read pipeline; a damaged file
    shows the field-level errors and asks again. Keep saves once without the check; that save copies
    the externally changed file to `.bak` (step 3) before replacing it. Escape keeps Concentrator's
    version.
  - A main file deleted while the application runs is not a conflict: the next save recreates it and
    logs a WARNING.
- Accepted limit: a change made between the check and `os.replace` (milliseconds) is not detected.
- Amendment (ADR-037): "Keep Concentrator's version" holds until a save succeeds, and the close
  flush does not trigger this dialog on top of the shutdown question.

## ADR-034 — Phase 1 persistence details

- Status: accepted (phase 1).
- Decisions:
  - Duplicate keys are rejected (`json5.loads(allow_duplicate_keys=False)`) with
    `STORAGE_DUPLICATE_KEY` (2020, parameter `key`): by default `json5` keeps the last value silently.
    Codes 2018 and 2019 stay reserved for phase 4. Superseded by ADR-035: TOML forbids duplicate keys,
    they are syntax errors (2004) and 2020 is retired.
  - The reader accepts a leading UTF-8 BOM (some editors add one); the writer never writes one.
  - `schema_version` is checked before pydantic runs, so a file written by a newer version reports
    `STORAGE_SCHEMA_VERSION_UNSUPPORTED` rather than a list of unexpected fields.
  - `domain/common/entity_collection.py` provides `EntityCollection[E]` (tuple plus id index and the
    shared operations); every `*Collection` subclasses it. Entities that support `copy_business`
    implement the `BusinessCopyable` protocol (`business_copy(new_id, now)`).
  - `DialogPort.warn(title, message, button_text)` shows a warning message.
  - The self-check also round-trips an in-memory `UserData` through codec, schemas and mappers (no
    file written), so a bundle missing `json5` or `pydantic` pieces fails the build (`tomllib` since
    ADR-035).
  - Daily backups are named `<stem>-YYYY-MM-DD.json5` (`.toml` since ADR-035; local date of the save). Retention deletes only
    files of the backup folder whose name matches that pattern exactly for the current file's stem;
    any other file is left alone.
  - New `[storage]` keys beyond the spec: `save_max_delay_ms` (ADR-029) and
    `blocking_write_timeout_ms` (ADR-028).
- Decided during the build (approved at the phase 1 review, 2026-11-07):
  - `UserDataFilePort.load`, `create` and `restore` return `StoredUserData` (the data and the file's
    `saved_at`) instead of a bare `UserData`, so the status bar shows when the file was last saved.
    The port also has a blocking `save(...)` (the shutdown flush needs the outcome while the main
    thread waits, ADR-032) and `discard_temporary(path)` (ADR-027).
  - The generic store is `StoreCollectionReader[E]` / `StoreCollectionWriter[E]` (one type parameter,
    as `AGENTS.md` section 6.2 writes it), working on `EntityCollection[E]` through a
    `CollectionSlot[E]`. The spec's `[E, C]` cannot be typed: a type parameter bound cannot refer to
    another one ("TypeVar bound type cannot be generic"). `EntityCollection` operations return
    `Self`, so the concrete collection survives, and an aggregate port may narrow `all_items()`.
  - The status bar has its own `StatusBarPresenter`; `ShellPresenter` keeps the module bar and title.
    `LanguageSwitcher` is the single place that changes the UI language (settings, translator,
    startup hint, full re-render).
  - The shutdown questions use a dialog service without parent: the shutdown presenter is built
    before the main window it guards. Superseded by ADR-036: the presenter receives a dialog service
    parented to the main window once the window exists.
  - The catalog key scan accepts the base of a plural key (`storage.issue.more`) when both
    `<base>.one` and `<base>.other` exist.

## ADR-035 — TOML with literal strings for the user data file

- Status: accepted, owner decisions (2026-11-07), including the quoting fallback and the
  `furryp.json` change. Supersedes ADR-002.
- Context: the phase 1 benchmark measured the `json5` decoder at 0.13 to 0.17 MB/s: 20.7 s to read
  1,000 tasks with 20 history events each (2.68 MB). ADR-002 allowed only a faster JSON5 decoder; the
  owner chose another format. TOML literal strings (`'...'`) have no escape sequences, so paths, URLs,
  backslashes and double quotes in user text are written exactly as typed.
- Decision:
  - The data file is TOML 1.0, UTF-8 without BOM, LF, extension `.toml`; the default is
    `%APPDATA%/Concentrator/concentrator.toml`. Side files keep their patterns: `<file>.tmp`,
    `<file>.bak`, `<file>.corrupt-YYYYMMDD-HHMMSS`, `<file>.tmp.discarded-YYYYMMDD-HHMMSS`, daily copies
    `<stem>-YYYY-MM-DD.toml`.
  - Reading uses the standard library `tomllib` (TOML 1.0). Writing uses our own emitter in
    `toml_codec.py`, the only module that imports `tomllib`. No dependency is added and `json5` is
    removed. `tomli-w` writes only `"..."` strings; `tomlkit` is a style-preserving document model, a
    dependency, and leaves the choice of quotes to the caller.
  - Quoting (TOML 1.0 literal strings cannot contain `'`, a newline or a control character):
    1. `'...'` by default;
    2. `'''...'''` when the value contains `'` (`'''Voir l'arborescence'''`): still one line, still no
       escapes;
    3. `"..."` with escapes only when the value contains `'''` or a control character other than tab.
       Multi-line text is stored as arrays of lines and paths and URLs are single-line, so this case
       is rare.
    The owner asked for single quotes everywhere and approved cases 2 and 3: they are the only ways to
    keep such values intact.
  - Layout written by the emitter: the header comment; the root keys whose values are scalars or empty
    arrays (TOML puts them before any table header); then, in schema order, one `[section]` per object
    and one `[[section]]` per element of a collection. Inside a table, a nested object is an inline
    table `{ key = value }` on one line (its arrays too); other arrays have one element per line and a
    trailing comma. Keys are bare snake_case words. Enums are integers, booleans `true`/`false`,
    timestamps and dates quoted strings (`'2026-11-06T16:44:03Z'`, `'2026-11-10'`).
  - TOML has no `null`: an optional value that is not set is an absent key (the writer omits `None`,
    the schemas give optional fields the default `None`). An empty collection is `key = []`.
  - Read pipeline: text -> leading BOM removed (`tomllib` rejects it) -> `tomllib.loads` -> schema
    version check -> native TOML dates and times, typed by hand (`due_date = 2026-11-10`), turned into
    ISO text -> `json.dumps` -> `model_validate_json` (strict JSON mode, unchanged) -> mapper -> rules.
    The next save writes those values quoted.
  - Errors: `tomllib.TOMLDecodeError` -> `STORAGE_SYNTAX_INVALID` (2004) with `line` and `column`
    (`lineno` and `colno`, Python 3.14). TOML forbids duplicate keys and `tomllib` reports them as
    syntax errors without naming the key, so `STORAGE_DUPLICATE_KEY` (2020) is retired; 2020 is never
    reused.
  - Tests round-trip every quoting case through `tomllib`: apostrophes at either end, `''`, `'''`,
    tab, newline, CR, NUL, DEL, backslashes, double quotes, non-ASCII text, emoji, a BOM inside a value.
  - No migration and `schema_version` stays 1: Concentrator is not released, and no JSON5 data file
    exists outside development.
  - `furryp.json` (change approved by the owner): the six contracts that forbid `json5` forbid
    `tomllib` instead, and `json5-only-in-persistence` becomes
    `tomllib-only-in-persistence`. `tomllib` is in the standard library, so without these contracts
    any layer could import it.
- Measurement (`scripts/bench_storage.py`, 1,000 tasks x 20 history events, 4 lines of text each):
  the TOML file is 1.74 MB; `TomlCodec.decode` takes 0.34 s (5.1 MB/s), the whole read pipeline with
  pydantic 0.39 s, `TomlCodec.encode` 0.13 s and the whole write pipeline 0.15 s. The same data as
  JSON5 (2.68 MB) takes 20.7 s to read with `json5.loads`. The phase 8 startup target (2 s) is within
  reach.
- Benchmark volume (owner decision): 1,000 tasks are enough. `scripts/bench_storage.py --tasks 1000`
  (20 history events per task) replaces the 5 MB document, and the phase 5 and phase 8 checks use
  1,000 tasks.
- Alternatives: a compiled JSON5 decoder (the ADR-002 remedy: one more dependency, quotes and
  escapes unchanged); plain JSON (escaped quotes and backslashes, no comments); SQLite (not readable
  by hand).
- Consequences: no dependency for the file format; hand-written comments are still lost at the next
  save (the header says so); the file is about a third smaller than the JSON5 one; specs, `AGENTS.md`,
  `concentrator.ini`, the catalogs (file dialog filter), `.gitignore` and `USAGE.md` follow the new
  extension.

## ADR-036 — Modal dialogs over the main window

- Status: accepted, owner decisions (2026-11-07). Supersedes the "dialogs without parent" item of
  ADR-034.
- Context: the shutdown questions opened centered on the screen, without parent. The owner set one
  rule for every dialog.
- Decision:
  - Every modal dialog opened while the main window exists (messages, questions, file pickers, the
    unexpected error dialog, the forms of later phases) goes through one `ModalHost` in `ui/support/`:
    1. A dimming layer covers the whole client area of the main window (module bar, pages, status
       bar) while the dialog is open: the palette's shadow color (black) at
       `ui.dialog_overlay_opacity_percent` (new ini key, 0..50, default 10, i.e. 10 % darker). It
       follows the window's resizes.
    2. The dialog opens centered on the main window (Qt centers a dialog on its parent; the host never
       moves a dialog before it is visible, which would cancel that).
    3. The dialog cannot leave the main window's frame. On Windows, every move of the dialog (title
       bar drag, keyboard, another monitor) is clamped before it happens, in `WM_WINDOWPOSCHANGING`,
       seen by a native event filter (`ctypes`, `ui/support/`); Qt does not hand `WM_MOVING` to the
       filters. The rectangles are the native ones (`GetWindowRect`, physical pixels), so mixed
       display scaling stays consistent. When the main window moves or is resized, the dialog is
       moved back inside. Along an axis where the dialog is larger than the window, it stays
       centered. Off Windows (the `offscreen` tests), a dialog is moved back right after its `Move`
       event.
    4. A minimized main window is restored before the dialog opens.
  - The shutdown presenter receives its dialog service after the main window is built (`attach`), as
    the error and external change presenters already do.
  - Limit: the title bar of the main window is drawn by Windows and is not dimmed.
  - Dialogs shown before the main window exists (configuration error, unguarded instance
    warning, first-run and recovery dialogs and their messages and pickers) have no window to dim or
    to stay in; they open centered on the screen.
  - The Windows file picker (native `IFileDialog`) stays. It is its own window: it gets the dimming
    layer, but Windows places it and lets it move freely. Qt's own file dialog (`DontUseNativeDialog`)
    would obey the rule but loses the Explorer navigation pane (Quick access, OneDrive, network
    locations), so it was rejected.
- Consequences: one code path for every dialog; a Windows-specific native event filter with a
  portable fallback; manual checks at each phase review (dimming, centering, dragging to the edges,
  display scaling).

## ADR-037 — Fixes from the phase 1 code review

- Status: accepted (2026-11-07), owner approval of the review recommendations. Amends ADR-027,
  ADR-028, ADR-032 and ADR-033.
- Context: a code review of the accepted phase 1 (`phase-0-accepted..phase-1-accepted`) found 14
  defects, three of them silent losses of changes. Each fix started with a failing test.
- Decisions:
  - Session end (ADR-032): the `commitDataRequest` flush no longer stops saving, because another
    application can cancel the session end and Concentrator then keeps running. `aboutToQuit` still
    flushes and stops saving.
  - Overwrite choice (ADR-033): "Keep Concentrator's version", from the conflict dialog or from the
    shutdown question, clears the conflict and holds until a save succeeds; a transient failure is
    retried with the overwrite, never asked again. A failed save with a change waiting keeps the
    `storage.failed_save_retry_ms` delay.
  - Close flush: the statuses it publishes carry `interactive_shutdown`, and the external
    modification dialog leaves them to the shutdown question (no stacked questions). A conflict found
    by the session end flush is still asked if the session goes on.
  - Creating a data file (first launch, "Start with an empty file"; ADR-027) puts aside a `.tmp` or
    `.bak` left at that path (`<file>.tmp.discarded-YYYYMMDD-HHMMSS`,
    `<file>.bak.discarded-YYYYMMDD-HHMMSS`); if one cannot be renamed, nothing is written.
  - Restore never renames a main file that became unreadable or newer-version after the probe
    (ADR-027: a `FATAL` file is never renamed or written).
  - A valid `.tmp` with the same `saved_at` as the main file (whole seconds, ADR-030) is offered when
    its data differs.
  - Startup reads the `.bak` only when the main file is not valid (`FileStateEnum.NOT_INSPECTED`, new
    value 4), so a normal start parses the data once.
  - TOML keys (ADR-035) are bare, `'...'` or `"..."`; never `'''...'''`, which TOML forbids for keys.
  - `WriterThread.shutdown` waits for the queued jobs, so the instance lock is released after the
    last write (ADR-028); the interpreter waited for the thread at exit anyway.
  - A second launch while a startup dialog is open brings that dialog to the front.
  - The save picker no longer asks whether to replace an existing file; creating the data file
    refuses an existing path with its own message.
  - The minimum width and the spacing of the first-run and recovery dialogs come from
    `ui.startup_dialog_min_width_px` (560) and `ui.dialog_spacing_px` (10).
- Not changed: errors raised during the startup dialogs are still only logged (ADR-024).
