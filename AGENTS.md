# AGENTS.md — Concentrator

Operating manual for coding agents (Claude Code, Codex, …) and humans working on this repository.
Everything in this repository is **English**: code, comments, docstrings, docs, commit messages, log
messages. The only French content is the UI catalog `assets/i18n/fr.json`.

## 1. Project

Concentrator is a local, single-user, single-window desktop application for **Windows 11**, written in
**Python 3.14** with **PySide6 (>= 6.11)**. It combines a countdown **timer** with alarms, timer
**favorites**, an **hourly chime**, a **focus queue** (quick TODO) and a full **TODO list manager**.

- No network, no console window, no command-line options, one instance only.
- User data: one JSON5 file chosen by the user at first launch (default proposed).
- Qt-only UI state (geometry, splitters, column widths, sorts): QSettings `.ini`.
- Application constants: shipped `concentrator.ini` (editable without redeploying).
- UI languages: English and French, switchable live from the status bar.

```
┌────────┬───────────────────────────────────────────┬───────────────────────┐
│ Module │ Menu A "Focus" (default page)             │                       │
│ bar    │ Zone 1 (~70 %): TODO manager              │ Zone 2 (~30 %):       │
│ 100 px │ list tabs · toolbar · table · details     │ timer · focus queue · │
│ full   │                                           │ favorites · options   │
│ height │ Menu B "Journal" and Menu C "Settings" replace zones 1 + 2        │
│        ├───────────────────────────────────────────────────────────────────┤
│        │ Status bar (1 line): last save state · language button FRA/ENG    │
└────────┴───────────────────────────────────────────────────────────────────┘
```

Specifications are split into phases in `docs/specs/`. Decisions and their rationale are in
`docs/decisions.md`. When this file and a phase spec disagree, the phase spec wins for that phase and
this file must be updated in the same change.

## 2. Non-negotiable rules

1. Respect the dependency map (§4). `furryp check concentrator` enforces it. Never weaken
   `furryp.json`, `pyproject.toml` lint/type settings or coverage thresholds to make a gate pass.
2. No Qt (`PySide6`, `shiboken6`) in `domain/`, `application/`, `presentation/`.
3. Backend operations never return a bare entity and never raise for expected failures. They return
   `DataResult[T]` or `ValidationResult` carrying `ErrorCodeEnum` codes. No error strings.
4. No silent exception. Catch the narrowest type, log the technical detail, convert to an error code.
   `except Exception` is allowed in exactly two places: the global exception hooks and `EventBus`
   dispatch (handler isolation). Both log with the traceback and forward the error to the shared
   `ErrorReporterPort`, so the user sees the error dialog (ADR-021).
5. Every enum subclasses `BaseIntEnum` (an `IntEnum`), is named `*Enum`, lives in `*_enum.py`, and
   defines `UNKNOWN = -1` and `UNSET = 0`.
6. Business rules live in domain `*Rules` classes that return a `ValidationResult`.
7. Entities have `id`, `created_at`, `updated_at` (timezone-aware UTC). A group of entities is always
   wrapped in its dedicated `*Collection` class.
8. Widgets are dumb: they render a snapshot and emit signals. No business logic and no service calls
   in `ui/`.
9. One render entry point: `RenderCoordinator.request(...)`. Never call `render()` directly.
10. Every user action goes through `ActionGate` (>= 100 ms cooldown, control disabled while busy,
    INFO log when the operation takes > 200 ms).
11. Use cases are synchronous and in-memory. Every user-data disk write goes through the single
    writer thread.
12. No hard-coded tunables: read them from `AppConfig` (loaded from `concentrator.ini`). No
    user-visible literal strings: use i18n keys.
13. No `print()`. Use `logging.getLogger(__name__)`.
14. All gates green before every commit (§14). No `# ruff: ignore[...]`, `# type: ignore` or
    `# pyright: ignore` without a rule and a one-line justification (ruff >= 0.17 rejects `# noqa`).
15. Work phase by phase. Never implement a later phase's feature. Stop at the phase review gate.

## 3. Repository layout

```
app-concentrator-py/
├── AGENTS.md  CLAUDE.md  CONTRIBUTING.md  README.md  USAGE.md  LICENSE
├── pyproject.toml  uv.lock  furryp.json  .python-version  .gitignore
├── .vscode/                     settings.json, extensions.json, launch.json
├── assets/
│   ├── config/concentrator.ini  application constants (copied next to the exe at build)
│   ├── i18n/en.json  fr.json    flat UI catalogs (plain JSON, no compiled files)
│   ├── icons/                   concentrator.ico, module icons (.svg/.png)
│   └── sounds/                  built-in alarm and chime .mp3 files (CC0 or owned)
├── concentrator/                source package (see §4)
├── tests/                       unit/, integration/, ui/, architecture/, fakes/
├── scripts/                     check.py, coverage_gate.py, build.py, clean.py, bench_storage.py
└── docs/                        decisions.md, specs/phase-*.md
```

Source package:

```
concentrator/
├── __main__.py           entry point: calls bootstrap.app.main()
├── domain/
│   ├── common/           BaseIntEnum, SeverityEnum, ErrorCodeEnum, ValidationIssue,
│   │                     ValidationResult, DataResult, ids, MultilineText, Identified protocol
│   ├── timer/            TimerConfig, TimerSession, TimerPreset(+Collection), HourlyChime, *Rules
│   ├── todo/             TaskList, Task, TaskEvent, Recurrence, LinkTarget, collections, *Rules
│   ├── focus/            FocusItem, FocusItemsCollection, FocusRules
│   └── settings/         UserSettings, LanguageEnum, UserSettingsRules
├── application/
│   ├── ports/            Protocols implemented by infrastructure (readers, writers, clock, ...)
│   ├── common/           EventBus, events, AppConfig (plain frozen dataclasses)
│   ├── storage/          load/recover/save coordination (SaveCoordinator, RecoveryService)
│   └── timer/ todo/ focus/ settings/ journal/   *_commands.py (writes), *_queries.py (reads)
├── infrastructure/
│   ├── persistence/      JSON5 codec, pydantic schemas, mappers, atomic writer, writer thread,
│   │                     in-memory UserDataStore, readers/writers
│   ├── config/           concentrator.ini loader -> AppConfig
│   ├── i18n/             JSON catalog loader, Translator
│   ├── logging/          setup, ring buffer handler, exception hooks
│   ├── system/           SystemClock, Uuid7IdGenerator, AppPaths, Windows shell helpers (ctypes)
│   └── qt/               Qt-backed driven adapters: sound, attention, single instance, scheduler,
│                         main-thread dispatcher, link opener, QSettings stores, Qt log bridge
├── presentation/         Qt-free view logic
│   ├── ports/            Protocols implemented by ui (DialogPort, ...)
│   ├── common/           RenderCoordinator, ActionGate, ActionIdEnum, RenderSectionEnum,
│   │                     FormState, ButtonSnapshot, formatters
│   └── shell/ storage/ timer/ todo/ focus/ journal/ settings/   *_presenter.py, *_snapshot.py, *_form.py
├── ui/                   Qt widgets only
│   ├── windows/          MainWindow, pages and dialogs: compose panels, wire signals
│   ├── panels/           compose widgets, expose signals, render(snapshot)
│   ├── widgets/          small reusable controls, SnapshotTableModel
│   └── support/          styles, icons, Qt helpers, QtDialogService (implements DialogPort)
└── bootstrap/            composition root: startup sequence, wiring, shutdown
```

## 4. Architecture

Hexagonal (ports and adapters). Dependencies point inward: `ui -> presentation -> application -> domain`,
and `infrastructure -> application -> domain`. `bootstrap` wires everything.

### 4.1 Layers and responsibilities

| Layer | Responsibility | Rules |
|---|---|---|
| `domain` | Entities, value objects, enums, `*Rules`, `*Collection`, results, error codes | Pure stdlib. Deterministic: time and ids are passed in. No I/O, no logging. |
| `application` | Use cases (`*Commands`, `*Queries`), ports, events, runtime engines (timer, chime), save coordination | Depends on domain and its own ports only. Synchronous. |
| `infrastructure` | Driven adapters: JSON5 persistence, ini config, i18n, logging, clock, ids, Qt-backed system services | Implements `application.ports`. Converts exceptions to error codes. |
| `presentation` | Presenters, snapshots, forms, render coordination, action gating, formatting | Qt-free, fully unit-testable. Builds translated, display-ready snapshots. |
| `ui` | Qt widgets in three tiers: window, panel, widget | Renders snapshots, emits signals. Implements `presentation.ports`. |
| `bootstrap` | Composition root, startup and shutdown sequences | The only place that instantiates adapters and knows every layer. |

### 4.2 Dependency map

| Importing layer | May import from | Must NEVER import from |
|---|---|---|
| `domain` | stdlib, `domain` | `application`, `infrastructure`, `presentation`, `ui`, `bootstrap`, `PySide6`, `shiboken6`, `pydantic`, `json5` |
| `application` | stdlib, `domain`, `application` | `infrastructure`, `presentation`, `ui`, `bootstrap`, `PySide6`, `shiboken6`, `pydantic`, `json5` |
| `presentation` | stdlib, `domain`, `application` | `infrastructure`, `ui`, `bootstrap`, `PySide6`, `shiboken6`, `pydantic`, `json5` |
| `infrastructure` (except `qt`) | stdlib, `domain`, `application`, `pydantic` (persistence, config), `json5` (persistence only) | `presentation`, `ui`, `bootstrap`, `PySide6`, `shiboken6` |
| `infrastructure.qt` | stdlib, `domain`, `application`, `PySide6` | `presentation`, `ui`, `bootstrap`, `pydantic`, `json5` |
| `ui` | stdlib, `presentation`, `PySide6` | `domain`, `application`, `infrastructure`, `bootstrap`, `pydantic`, `json5` |
| `ui.widgets` | + `ui.support` | `ui.panels`, `ui.windows` |
| `ui.panels` | + `ui.widgets`, `ui.support` | `ui.windows` |
| `bootstrap` | everything | — (only `__main__` imports it) |

Feature isolation in the domain: `domain.timer` and `domain.todo` never import each other;
`domain.focus` may import `domain.todo` identifiers. `domain.common` imports no other feature.

Ports live in the layer that consumes them. Adapters explicitly subclass the Protocol they implement
(so basedpyright checks conformance at definition) and mark methods with `@override`.

### 4.3 Runtime flow

```
click ─► Panel signal ─► (wired by Window) ─► Presenter.on_xxx()
      ─► ActionGate.run(ActionIdEnum.X, op) ─► *Commands use case ─► domain Rules + entity
      ─► Writer (in-memory UserDataStore) ─► EventBus.publish(event) ─► SaveCoordinator (debounce)
      │                                                               └► writer thread ─► JSON5 file
      └► Presenter handles event ─► RenderCoordinator.request(section)
         ─► next event-loop turn: build snapshot once, compare with last, Panel.render(snapshot)
```

A `QTimer` created in bootstrap ticks `AppTicker.tick()` every `timer.tick_interval_ms`; the timer
engine, chime service and journal polling run from that tick. Nothing in `ui/` owns business timers.

## 5. Domain conventions

### 5.1 Entities and value objects

- `@dataclass(frozen=True, slots=True, kw_only=True)`. Immutable: changes return a new instance via
  `with_*` methods that also set `updated_at`.
- First three fields: `id` (a `NewType` over `str`, e.g. `TaskId`), `created_at`, `updated_at`.
  Ids are UUIDv7 strings (`uuid.uuid7()`, Python 3.14) produced by `IdGeneratorPort`.
- Factories `create(...)` take `new_id` and `now` as arguments. The domain never reads the clock.
- Never name a parameter `id`, `type`, `list`, `format` (ruff `A002`): use `task_id`, `kind`, ...
- Value objects (`Duration`, `Volume`, `MultilineText`, `LinkTarget`, `SoundRef`, `Recurrence`)
  normalize in their factory and are validated by `*Rules`.
- Multi-line text is `MultilineText(lines: tuple[str, ...])`. Paths and URLs are single-line and
  normalized (`\` replaced by `/`) by the domain, so the UI shows the stored form after saving.
- Paths (`C:/`, `D:/`, UNC) and URLs detected in task text are only made clickable like hyperlinks
  and opened as-is: never checked for existence or type before opening.

### 5.2 Enums

```python
class TaskStateEnum(BaseIntEnum):
    UNKNOWN = -1
    UNSET = 0
    OPEN = 1
    DONE = 2
    ARCHIVED = 3
```

- `BaseIntEnum.parse(value: int) -> Self` returns `UNKNOWN` for unrecognized values (forward
  compatibility when reading files). Values are explicit and never renumbered or reused.
- `UNSET` means "not chosen yet"; `UNKNOWN` means "value not understood". Rules reject both where a
  real value is required.

### 5.3 Results and error codes

```python
@dataclass(frozen=True, slots=True)
class ValidationIssue:
    code: ErrorCodeEnum
    severity: SeverityEnum
    field: str = ""                                  # dotted path, "" for global
    params: tuple[tuple[str, str], ...] = ()         # message interpolation values

class ValidationResult:  # frozen; always present, even on success
    issues: tuple[ValidationIssue, ...]
    # factories: success(), skipped(), failure(code, field=..., **params), warning(...), of(*issues)
    # queries: is_success, is_failure, has_warnings, is_success_with_warnings, is_skipped,
    #          severity (worst), error_codes, issues_for(field), first_failure, merge(*others)

@dataclass(frozen=True, slots=True)
class DataResult[T]:
    data: T | None
    validation: ValidationResult
    # factories: ok(data, validation=success), fail(validation); queries: is_success, value_or(x)
```

- `SeverityEnum`: `UNKNOWN=-1, UNSET=0, SKIPPED=1, SUCCESS=2, WARNING=3, ERROR=4, CRITICAL=5`.
  Worst severity = highest value; `UNKNOWN` is treated as `ERROR` by `is_failure`.
- `ErrorCodeEnum` uses numeric ranges: `1xxx` common validation, `2xxx` storage, `3xxx` config and
  i18n, `4xxx` timer, `5xxx` todo, `6xxx` focus, `7xxx` system (links, audio, instance).
- Every code has a UI message key `error.<code_name_lowercase>` in both catalogs (tested).
- Never discard a returned `ValidationResult` or `DataResult`: handle it, propagate it, or log it.

### 5.4 Rules and collections

- `TaskRules.validate(task) -> ValidationResult`, plus focused methods (`validate_text`, ...) used by
  forms for inline errors. Rules are stateless; limits come from arguments built from `AppConfig`.
- `TasksCollection`, `TaskListsCollection`, `TimerPresetsCollection`, `FocusItemsCollection`: immutable
  wrappers (tuple + id index) with `get(id) -> DataResult[T]`, `contains`, `with_added`,
  `with_replaced`, `without`, `filtered(query)`, `sorted_by(...)`, `__len__`, `__iter__`.
  Group-level business logic (ordering, uniqueness, "next position") lives here.

## 6. Application conventions

### 6.1 Ports (Protocols in `application/ports/`, suffix `Port`)

`ClockPort` (`now_utc()`, `now_local()`, `monotonic()`), `IdGeneratorPort`, `SchedulerPort`
(`call_soon`, `call_later` returning a cancellable handle), `MainThreadDispatcherPort`,
`TranslatorPort`, `LogFeedPort`, `SoundPlayerPort`, `AttentionPort`, `LinkOpenerPort`,
`ViewPreferencesPort` (string key-value), `UserDataFilePort`, and one `*ReaderPort` / `*WriterPort`
pair per aggregate.

### 6.2 Data operations (reads separated from writes)

| Operation | Port | Signature | Notes |
|---|---|---|---|
| exist | Reader | `exists(entity_id) -> DataResult[bool]` | |
| read item | Reader | `read_item(entity_id) -> DataResult[T]` | `ENTITY_NOT_FOUND` |
| all items | Reader | `all_items() -> DataResult[TCollection]` | |
| find | Reader | `find(query) -> DataResult[TCollection]` | query = frozen dataclass |
| create | Writer | `create(entity) -> DataResult[T]` | `ENTITY_DUPLICATE_ID` |
| update | Writer | `update(entity) -> DataResult[T]` | `ENTITY_NOT_FOUND` |
| delete | Writer | `delete(entity_id) -> DataResult[T]` | returns the removed entity |
| cp business | Writer | `copy_business(entity_id, new_id, now) -> DataResult[T]` | duplicate: new id, new timestamps, history restarted with a `COPIED_FROM` event, stored |
| cp technical | Writer | `copy_technical(entity_id) -> DataResult[T]` | exact copy (same id, timestamps, history), NOT stored; for export, backup, undo baseline |

Singleton aggregates (`UserSettings`, `TimerConfig`, `HourlyChime`) expose only `read()` and
`update(entity)`. A generic `StoreCollectionReader[E]` / `StoreCollectionWriter[E]` in
`infrastructure/persistence/` implements the table once; aggregates specialize it.

### 6.3 Use cases

- One `*_commands.py` (writes) and one `*_queries.py` (reads) per feature; split a class before it
  exceeds about 10 public methods. Each method is a use case returning `ValidationResult` or
  `DataResult[T]`.
- A command: build or change the entity with `now` and ids from ports, validate with `*Rules`, call
  the writer, publish an event on success. Nothing else.
- Cross-feature reactions use the synchronous `EventBus` (e.g. focus removes an item when
  `TaskStateChangedEvent` says the task is done). Features never call each other's writers.

### 6.4 Threads

- Main thread: Qt event loop, use cases, in-memory store, presenters. Use cases must stay fast
  (in-memory only).
- One writer thread (`concurrent.futures.ThreadPoolExecutor(max_workers=1)`): serialization and file
  I/O of immutable `UserData` snapshots. Results come back through `MainThreadDispatcherPort`.
- No other threads without an approved decision in `docs/decisions.md`.

## 7. Infrastructure

### 7.1 User data file (JSON5)

- JSON5 is a deliberate choice: the file must stay clear for a user who reads or edits it.
- Location chosen at first launch: open an existing file, create at the default location
  (`paths.default_data_file`, i.e. `%APPDATA%/Concentrator/concentrator.json5`), or create elsewhere.
  The chosen path is stored in the UI state `.ini`.
- Content: user settings, timer config, presets, chime, lists, tasks, focus queue, `schema_version`.
  Running timer state is not persisted.
- Read pipeline: text -> `json5.loads` -> `json.dumps` -> `Schema.model_validate_json` (pydantic,
  `strict=True`, `extra="forbid"`) -> mapper -> domain `*Rules` -> `UserData`. Pydantic only runs on
  JSON, after the JSON5 transformation.
- Write pipeline (writer thread): `UserData` -> mapper -> schema -> `model_dump(mode="json")` ->
  `json5.dumps(indent=2, quote_keys=False, trailing_commas=True, ensure_ascii=False)` -> header
  comment -> atomic write.
- Format: UTF-8 without BOM, LF, stable key order, enums as ints, UTC timestamps
  `YYYY-MM-DDTHH:MM:SSZ`, local dates `YYYY-MM-DD`, multi-line text as arrays of lines, paths and URLs
  as one flat string with `/` separators. Comments written by hand are ignored and lost on next save.
- Pydantic models are persistence DTOs only (`infrastructure/persistence/schemas/`); never pass them
  outside the adapter. `ValidationError` is caught immediately and converted: one `ValidationIssue`
  per error, `field` = joined `loc`, code from the pydantic error type (`missing` ->
  `STORAGE_FIELD_MISSING`, `extra_forbidden` -> `STORAGE_FIELD_UNEXPECTED`, `*_type`/`*_parsing` ->
  `STORAGE_FIELD_INVALID_TYPE`, others -> `STORAGE_FIELD_INVALID_VALUE`). Details go to the log.
- Schema evolution: additive fields need defaults. After the first release, any breaking change bumps
  `schema_version` and adds a dict-to-dict migration step that runs before validation.

### 7.2 Atomic save and recovery

1. Write the full content to `<file>.tmp`, `flush()`, `os.fsync()`.
2. Re-read the temporary file and compare its SHA-256 with the bytes written.
3. If `<file>` exists, copy it to `<file>.bak` (`shutil.copy2`).
4. `os.replace(<file>.tmp, <file>)` (atomic on NTFS). Retry `storage.replace_retry_count` times with
   `storage.replace_retry_delay_ms` on `PermissionError` (antivirus, indexer, sync clients).
5. Optional daily copy into `paths.backup_dir`, keeping `storage.daily_backup_retention_days`.

Startup recovery: load `<file>`; if a valid `<file>.tmp` newer than `<file>` exists, offer to restore
it; if `<file>` is invalid, show the translated error and offer the newest valid of `.tmp`/`.bak`;
otherwise offer: choose another file, start empty (the damaged file is renamed
`<file>.corrupt-YYYYMMDD-HHMMSS`), or quit. Never overwrite a damaged file silently.

Saves are debounced (`storage.save_debounce_ms`), carry a revision number, and are flushed
synchronously on quit (`storage.shutdown_flush_timeout_ms`). The status bar shows the save state.

### 7.3 Configuration files

| File | Owner | Content | Access |
|---|---|---|---|
| `concentrator.ini` | application (next to the exe; `assets/config/` in dev) | constants and defaults | read-only, validated by pydantic into `AppConfig` at startup |
| `ui-state.ini` | Qt (`QSettings`, `IniFormat`, `paths.ui_state_file`) | geometry, splitters, header states, sorts, filters, active page, data file path | read-write via `ViewPreferencesPort` and `ui.support` |
| user JSON5 file | user | business data and personal settings | `UserDataFilePort` only |

`AppConfig` values support the tokens `{appdata}`, `{localappdata}` and `{app_dir}`, resolved by
`AppPaths`. A missing or invalid key is a fatal startup error with an explicit message; there are no
silent code-level defaults for ini keys.

### 7.4 Qt-backed adapters (`infrastructure/qt/`)

- `QtSoundPlayer`: `QMediaPlayer` + `QAudioOutput` (QtMultimedia, FFmpeg backend). Streams files of
  any size, `setLoops(n)` or `QMediaPlayer.Loops.Infinite`. Volume 0-100 converted with
  `QAudio.convertVolume` (logarithmic to linear). Separate instances for alarm and chime.
- `QtAttention`: `QSystemTrayIcon.showMessage` (Windows toast) and `QApplication.alert(window, 0)`
  (taskbar button flashes until activated). Notifies only when the window is not active.
- `QtSingleInstanceGuard`: `QLockFile` (per user) for exclusivity plus `QLocalServer`/`QLocalSocket`
  so a second launch asks the first instance to show itself, then exits with code 0.
- `QtScheduler`, `QtMainThreadDispatcher` (signal with queued connection), `QtLinkOpener`
  (`QDesktopServices.openUrl`), `QSettingsViewPreferences`, Qt message handler bridge to logging.
- `infrastructure/system/windows_shell.py` sets the AppUserModelID (ctypes) before the
  `QApplication` exists, so the taskbar and toasts show Concentrator, not Python.

### 7.5 Logging

- Standard `logging`. Root level from `logging.level`. Format:
  `%(asctime)s | %(levelname)-8s | %(threadName)s | %(name)s | %(message)s`.
- Handlers: `RotatingFileHandler` in `paths.log_dir` (UTF-8) and a thread-safe in-memory ring buffer
  (`logging.journal_buffer_size`) read by the journal page through `LogFeedPort`. No stream handler
  when frozen (`sys.stderr` is `None` in windowed builds).
- `sys.excepthook` and `threading.excepthook` log CRITICAL with traceback and show an error dialog.
  `logging.captureWarnings(True)`, Qt messages routed to the `qt` logger, `faulthandler` to a file.
- Log messages are English, technical, and never contain the content of user tasks.

## 8. Presentation and UI

### 8.1 Snapshots

- A snapshot is a frozen dataclass describing everything a panel shows at one instant: translated
  texts, formatted values, enabled/visible flags, rows, inline errors. Views never read models,
  services or files; they receive a snapshot.
- Snapshot fields use builtins, tuples and presentation types only (no domain types), so `ui/` never
  imports the domain. Keep them shallow (furryp Demeter depth 3).
- `ButtonSnapshot(text, tooltip, enabled, visible, action)` where `action` is an `ActionIdEnum`.
  Panels emit `action_requested(int)`; presenters dispatch.

### 8.2 Render coordination

- `RenderCoordinator.register(section, build_snapshot, render)` once per panel (`RenderSectionEnum`).
- `request(*sections)` / `request_all()` collect sections and schedule one flush on the next
  event-loop turn (`SchedulerPort.call_soon`). The flush builds each snapshot once, skips it if equal
  to the last rendered one, then calls `render` once. Language changes call `request_all()`.
- Panels implement `render(snapshot)` idempotently, wrapped in `setUpdatesEnabled(False/True)` and
  `QSignalBlocker` for programmatic value changes.
- Tables use `SnapshotTableModel` (`QAbstractTableModel`) fed with snapshot rows: append-only changes
  insert rows, other changes reset the model. Sorting and filtering happen in presenters (testable),
  not in `QSortFilterProxyModel`.

### 8.3 Action gate

`ActionGate.run(action, operation, *, interactive=False)`:
- ignores the call while `action` is busy (log DEBUG);
- marks it busy and requests a render (bound controls become disabled);
- runs the operation and measures it with `ClockPort.monotonic()`;
- logs INFO `Action <NAME> took <ms> ms` when above `ui.slow_action_threshold_ms` (not for
  `interactive=True`, e.g. modal dialogs);
- releases it after `max(0, ui.action_cooldown_ms - elapsed)` and requests a render.
Long asynchronous actions use `begin(action) -> ActionToken` and `token.finish()`.

### 8.4 Forms

- `FormState[TDraft]`: `baseline`, `draft`, `errors: ValidationResult`, `is_dirty` (draft differs
  from baseline), `can_submit` (dirty and no failure), `set_field(...)`, `reset()`, `commit()`.
- Validation runs on every change through the domain `*Rules`; inline errors appear under the field
  (`FieldErrorSnapshot(field, message)`) with an `invalid` dynamic property for styling.
- Closing a dirty form asks for confirmation through `DialogPort`.

### 8.5 Window / panel / widget

| Tier | Folder | Does | Never does |
|---|---|---|---|
| Window | `ui/windows/` | `MainWindow`, pages (`FocusPage`, `JournalPage`, `SettingsPage`) and dialogs: build layout from panels, connect panel signals to presenter methods, register panels with `RenderCoordinator`, save/restore geometry | Branching logic, formatting, service calls |
| Panel | `ui/panels/` | Composes widgets, exposes intent signals (`*_requested`), `render(snapshot)` | Talks to other panels directly, decides enabled states |
| Widget | `ui/widgets/` | Small reusable control (`DurationDisplayWidget`, `SnapshotButton`, `FieldErrorLabel`, `SnapshotTableModel`) | Knows any feature |

- Presenters ask for confirmations, file pickers and forms through `presentation.ports.DialogPort`;
  `ui.support.QtDialogService` implements it. Dialog buttons use catalog texts.
- Qt rules: new-style signals only; `@override` on overridden Qt methods; parents set for every
  `QObject`; no `processEvents()`; no `QTimer` in ui except purely visual effects.
- Sizes and timings come from `AppConfig` (`ui.module_bar_width_px`, `ui.timer_font_size_px`, ...).
- Rich text: always `html.escape` user content before building HTML for a `QLabel`/`QTextBrowser`.

## 9. Localization

- Catalogs: `assets/i18n/en.json` and `fr.json`, flat objects with dotted keys
  (`"timer.button.start": "Start"`). Placeholders `{name}`. Plain JSON, loaded at startup.
- `TranslatorPort.tr(key, **params)` and `tr_plural(key, count, **params)` (keys `<key>.one` and
  `<key>.other`; French uses "one" for 0 and 1, English only for 1). Missing key: fall back to English,
  then to the key itself, and log a WARNING once.
- Date/time formats and month/day names are catalog entries (`format.date`, ...). Do not use the
  `locale` module.
- Switching language updates the user settings, the translator, then `RenderCoordinator.request_all()`.
  No restart, no widget recreation. Window title and tray tooltip are part of the shell snapshot.
- Tests: both catalogs have identical key sets and placeholders; every `ErrorCodeEnum` member, every
  `ActionIdEnum` label and every key referenced in code exists.

## 10. Error handling

Example (damaged data file):
1. Pydantic raises `ValidationError` inside the JSON5 adapter.
2. The adapter logs the technical detail (WARNING, with file path and error list).
3. It returns `DataResult.fail(...)` with one issue per field, e.g.
   `ValidationIssue(STORAGE_FIELD_INVALID_TYPE, ERROR, field="task_lists.0.name")`.
4. The presenter maps it to a translated message: "The data file is damaged: list name invalid.
   Restore the last backup?" (`error.storage_field_invalid_type`, field label `field.task_lists.name`).

Programming errors (violated invariants, impossible states) may raise; global hooks log them as
CRITICAL and show a dialog. Never use exceptions for control flow.

## 11. Coding rules

- PEP 8 via `ruff format` (line length 120, double quotes, spaces, LF). Google-style docstrings on
  every public module, class and function (`Args:`, `Returns:`, `Raises:`).
- Imports at the top of the file in three groups: standard library, third party, first party
  (`concentrator`), enforced by ruff isort. Absolute imports only.
- Typing: basedpyright `strict`, full annotations, PEP 695 generics (`class DataResult[T]`), `Self`,
  `@override`, `Final` for module constants. No `Any` unless a third-party API forces it, isolated in
  an adapter.
- Interfaces are `typing.Protocol` classes. Adapters subclass them explicitly.
- Naming: modules `snake_case.py`; classes `PascalCase`; enums `*Enum` in `*_enum.py`; rules `*Rules`
  in `*_rules.py`; collections `*Collection` in `*_collection.py`; ports `*Port` in `*_port.py`;
  snapshots `*Snapshot`; presenters `*Presenter`; forms `*Form`; ui files `*_window.py`, `*_dialog.py`,
  `*_panel.py`, `*_widget.py`; tests `test_<module>.py`.
- OOP and SOLID: small classes, single responsibility, private state with `_` prefix, behavior next
  to data, composition over inheritance, dependency injection through constructors.
- Size limits (furryp/ruff): function <= 26 lines, file <= 1000 lines, cyclomatic complexity <= 9,
  cognitive complexity <= 16, class complexity <= 80, <= 8 arguments, <= 12 locals, <= 35 statements,
  <= 4 nested blocks, <= 20 instance attributes, attribute chains <= 3 (roots `self`/`cls` ignored).
  Qt build code: split into `_build_*` helpers.
- No magic numbers or strings in logic: `AppConfig`, enums, or named `Final` constants.
- `pathlib.Path` for paths; timezone-aware datetimes (ruff `DTZ`).

## 12. Testing

- Framework: `pytest` with `pytest-cov`; `pytest-qt` for `tests/ui` (offscreen, set in
  `tests/conftest.py`: `QT_QPA_PLATFORM=offscreen` before any Qt import).
- Layout mirrors the source: `tests/unit/<layer>/...`, `tests/integration/` (real files in
  `tmp_path`, ini, catalogs), `tests/ui/` (marker `ui`), `tests/architecture/` (enum conventions,
  naming, no `print`, catalog parity), `tests/fakes/` (typed fakes implementing ports: `FakeClock`
  with `advance()`, `FakeIdGenerator`, `ManualScheduler`, `ImmediateDispatcher`, `FakeSoundPlayer`,
  `FakeAttention`, `FakeDialogs`, in-memory readers/writers).
- Prefer fakes over `unittest.mock`. Tests are deterministic: no sleeps, no real clock, no network.
- Name tests `test_<unit>_<scenario>_<expected>`; Arrange / Act / Assert.
- Coverage thresholds (branch coverage, enforced by `scripts/coverage_gate.py`):

| Scope | Minimum |
|---|---|
| `concentrator/domain` | 90 % |
| `concentrator/application` | 85 % |
| `concentrator/presentation` | 80 % |
| overall `concentrator` | 75 % |

- Every bug fix starts with a failing test. Every error code has at least one test producing it.

## 13. Environment (Windows 11)

Prerequisites: Git, uv (`winget install --id astral-sh.uv -e`), VS Code, the `furryp` CLI on `PATH`.

```powershell
uv python install 3.14
uv sync                              # creates .venv and uv.lock from pyproject.toml
uv run concentrator                  # gui-script entry point, no console window
uv run python -m concentrator        # same app, launched from a terminal (debugging)
```

VS Code: extensions `ms-python.python`, `charliermarsh.ruff`, `detachhead.basedpyright`; disable
Pylance (`"python.languageServer": "None"`) to avoid two type checkers; interpreter
`.venv\Scripts\python.exe`; ruff as formatter on save; pytest enabled. Keep `.vscode/` committed.

Dependencies: runtime `pyside6`, `pydantic`, `json5`; dev `ruff`, `basedpyright`, `pytest`,
`pytest-cov`, `pytest-qt`, `pyinstaller`. Add a dependency only with an entry in `docs/decisions.md`.

## 14. Commands and gates

Before every commit, in this order (or `uv run python scripts/check.py`, which runs the same steps
and stops at the first failure):

```powershell
uv run ruff format
uv run ruff check
uv run basedpyright
furryp check concentrator
uv run pytest --cov --cov-report=term-missing --cov-report=json
uv run python scripts/coverage_gate.py
```

Build and clean:

```powershell
uv run python scripts/build.py        # PyInstaller --onedir --windowed --noupx -> dist/Concentrator/
uv run python scripts/clean.py        # removes build/, dist/, caches, coverage files, __pycache__
uv run python scripts/clean.py --all  # also removes .venv
```

`build.py` bundles `assets/` (icons, sounds, i18n) inside the bundle, copies `concentrator.ini` next
to `Concentrator.exe`, uses `assets/icons/concentrator.ico`, writes the spec file into `build/`, and
fails if the frozen app cannot locate its ini, catalogs and sounds (smoke run with the environment
variable `CONCENTRATOR_SELF_CHECK=1`; the app itself accepts no command-line option).

## 15. Workflow for agents

1. Read this file, `docs/decisions.md` and the current phase spec before writing code.
2. Start with a short plan (files to create or change, tests, risks) and wait for approval.
3. Work on branch `phase-<n>-<slug>`. Small commits, Conventional Commits
   (`feat(timer): add snooze`, `fix(storage): ...`, `test(...)`, `docs(...)`, `refactor(...)`).
4. Write tests with the code. Run the gates. Update `USAGE.md` for user-visible behavior and
   `docs/decisions.md` for any decision.
5. At the end of a phase, stop and produce the review report: what was done, deviations from the
   spec, gate output, coverage per layer, manual test script results you could not run (the GUI is
   checked by the human), open questions.
6. Do not start the next phase until the human approves and tags `phase-<n>-accepted`.

Definition of done for any change: gates green, coverage thresholds met, no new warnings, docs
updated, no TODO comments left without an issue reference.

## 16. Anti-patterns (reject in review)

- A widget computing an enabled state, formatting a date, or calling a service.
- A presenter importing PySide6, or a domain object importing logging.
- `except Exception: pass`, `except: ...`, returning `None` to signal an error, error strings.
- Pydantic models or JSON5 dicts leaking out of `infrastructure/persistence/`.
- Reading `concentrator.ini` or `QSettings` from anywhere other than their adapters.
- Several `render()` calls for one user action; timers polling from widgets.
- Mutable entities, public mutable attributes, lists of entities passed around without a
  `*Collection`.
- Writing user data from the main thread, or from more than one thread.
- Hard-coded sizes, durations, paths, colors or UI strings.

## 17. Glossary

| Term | Meaning |
|---|---|
| Module bar | Left vertical bar (100 px) with the buttons for menus A, B, C |
| Menu A / Focus page | Zone 1 (TODO manager) + Zone 2 (timer, focus queue, favorites, options) |
| Menu B / Journal | Application log viewer with level filter |
| Menu C / Settings | Editable user settings |
| Focus queue | Quick TODO list in zone 2, made of references to existing tasks |
| Preset / favorite | Saved timer duration (default 15, 30, 45 min) |
| Ringing | Timer reached zero; alarm playing until OK, restart, snooze or auto-stop |
| Snapshot | Immutable description of what a panel shows |
| Business copy | Duplicate with a new identity; technical copy: exact clone, not stored |
