# Phase 1 — User data persistence (TOML)

Depends on: phase 0. Branch: `phase-1-persistence`.

Revision of 2026-11-07, after the first review (owner decisions): the data file is TOML with literal
strings instead of JSON5 (ADR-035); every modal dialog dims and stays inside the main window (ADR-036);
the benchmark uses 1,000 tasks.

## Goal

The complete lifecycle of the user data file: locate or create it at first launch, load it through
the validation pipeline, keep it in memory, save it safely on the single writer thread, recover after
a crash or corruption, and show the save state in the status bar. The first persisted entity is
`UserSettings` (the language chosen with the status bar button).

## In scope

- First-launch flow and remembered data file path.
- Read and write pipelines (`AGENTS.md` §7.1), atomic save and recovery (§7.2).
- In-memory `UserDataStore`, generic collection reader/writer implementing the nine operations.
- `SaveCoordinator` (debounce, revisions, retries, flush on quit), status bar save state.
- Error-to-message mapping for storage errors, including field labels.
- Modal dialogs over the main window: dimming layer, centered, kept inside the window (ADR-036).
- Storage throughput benchmark.

## Out of scope

Timer, presets, tasks (their sections are added by later phases with defaults), moving or switching
the data file from the settings page (phase 4).

## Deliverables

### Domain

- `domain/settings/user_settings.py`: `UserSettings` (`id: UserSettingsId`, `created_at`,
  `updated_at`, `language: LanguageEnum`), `create(new_id, now, language)`, `with_language(...)`.
- `domain/settings/user_settings_rules.py`: language must be set and known.
- `domain/common/multiline_text.py`: `MultilineText` (`from_text` splits on `\r\n`, `\n`, `\r`,
  strips trailing spaces per line, trims leading and trailing blank lines; `as_text`, `first_line`,
  `is_blank`, `line_count`). Used by later phases.

### Application

- `storage/user_data.py`: `UserData` frozen dataclass (`schema_version`, `settings`; later phases add
  sections with defaults).
- `ports/user_data_file_port.py`:
  - `exists(path) -> bool`
  - `load(path) -> DataResult[StoredUserData]` (`StoredUserData` = the data and the file's `saved_at`; ADR-034)
  - `probe(path) -> DataResult[RecoveryReport]` (state of main, `.tmp`, `.bak`: absent / valid /
    invalid, `saved_at`, issues)
  - `restore(path, source: RecoverySourceEnum) -> DataResult[StoredUserData]`
  - `create(path, data) -> DataResult[StoredUserData]` (fails with `STORAGE_FILE_ALREADY_EXISTS`)
  - `quarantine(path) -> DataResult[str]` (renames to `.corrupt-YYYYMMDD-HHMMSS`)
  - `save(path, data, revision, *, timeout_ms, overwrite_external=False) -> SaveOutcome` (blocking,
    for the shutdown flush; ADR-032)
  - `save_async(path, data, revision, on_done, *, overwrite_external=False)` (the flag skips the
    external modification check once, ADR-033); `flush(timeout_ms) -> ValidationResult`
  - `discard_temporary(path) -> DataResult[str]` (renames the stale `.tmp`, ADR-027)
- `ports/user_data_session_port.py`: `current() -> UserData`, `revision() -> int`, `reset(data)`.
- `ports/user_settings_reader_port.py`, `ports/user_settings_writer_port.py` (`read`, `update`).
- `storage/startup_commands.py`: `resolve_startup(...)` returns a `StartupStepEnum`
  (`READY`, `NEEDS_LOCATION`, `NEEDS_RECOVERY`, `FATAL`) with the data needed by the dialogs (matrix
  in `docs/decisions.md`, ADR-027); `create_at(path)`, `open_existing(path)`, `restore(source)`,
  `keep_current()` (renames the stale `.tmp` to `<file>.tmp.discarded-YYYYMMDD-HHMMSS`),
  `start_empty()`, `retry()`. Creating a file puts aside a leftover `.tmp`/`.bak` (ADR-037).
- `storage/save_coordinator.py`: subscribes to `UserDataChangedEvent`; trailing debounce
  `storage.save_debounce_ms`, capped by `storage.save_max_delay_ms` after the first unsaved change
  (ADR-029); one save in flight; if the revision changed meanwhile, saves again; on failure keeps data
  in memory and retries every `storage.failed_save_retry_ms`, except after
  `STORAGE_FILE_CHANGED_EXTERNALLY` (no retry until the user chooses, ADR-033); publishes
  `SaveStatusChangedEvent(state: SaveStateEnum, saved_at, issues)`; `flush_for_shutdown()`.
- Language hint: `shell/language_hint` in `ui-state.ini`, written at every language change; the
  startup dialogs use it, else `i18n.default_language` (ADR-027).
- `SaveStateEnum`: `UNKNOWN=-1, UNSET=0, NO_FILE=1, SAVED=2, PENDING=3, SAVING=4, FAILED=5`.
- `settings/settings_commands.py`: `change_language(language)`; `settings/settings_queries.py`.

### Infrastructure (`infrastructure/persistence/`)

| Module | Responsibility |
|---|---|
| `toml_codec.py` | the only module that imports `tomllib`. `decode(text) -> DataResult[object]` (`tomllib.loads`; `TOMLDecodeError` -> `STORAGE_SYNTAX_INVALID` with `line` and `column`; native TOML dates and times turned into ISO text); `encode(obj) -> str` (our emitter: quoting and layout of ADR-035) |
| `schemas/` | pydantic DTOs, `ConfigDict(strict=True, extra="forbid", frozen=True)`: `UserDataSchema`, `UserSettingsSchema` |
| `pydantic_error_mapper.py` | `ValidationError` -> `ValidationResult` (mapping in `AGENTS.md` §7.1) |
| `mappers/` | schema <-> domain, enums through `BaseIntEnum.parse`, then domain `*Rules` |
| `toml_user_data_file.py` | implements `UserDataFilePort`; read pipeline; write pipeline; header comment; fingerprint of the main file (ADR-033) |
| `atomic_file_writer.py` | steps 1-5 of `AGENTS.md` §7.2 (including the external modification check), retries, error codes |
| `daily_backup.py` | one copy per day into `paths.backup_dir`, retention |
| `recovery_inspector.py` | builds `RecoveryReport` |
| `writer_thread.py` | `ThreadPoolExecutor(max_workers=1, thread_name_prefix="writer")`, results posted with `MainThreadDispatcherPort` |
| `user_data_store.py` | implements `UserDataSessionPort`; holds the current `UserData`; publishes `UserDataChangedEvent(revision)` |
| `store_collection.py` | generic `StoreCollectionReader[E]` and `StoreCollectionWriter[E]` implementing the nine operations over a `CollectionSlot[E]` (ADR-034: `[E, C]` cannot be typed; tested with a test-only entity and collection) |
| `store_user_settings.py` | singleton reader/writer for `UserSettings` |

### Presentation and UI

- `presentation/storage/first_run_presenter.py` + `FirstRunSnapshot`: default path shown, actions
  "Use the file found at the default location" (only if it exists), "Create at default location",
  "Create elsewhere...", "Open existing file...", "Quit"; with the "file not found" notice, also
  "Retry".
- `presentation/storage/recovery_presenter.py` + `RecoverySnapshot`: translated problem description
  (first issues, field labels), candidates with their `saved_at`, actions "Restore", "Keep the current
  file" (valid main with a newer `.tmp`), "Choose another file...", "Start with an empty file",
  "Retry" (`FATAL` caused by `STORAGE_FILE_UNREADABLE`, or a missing main file), "Quit".
- `presentation/storage/startup_flow_presenter.py`: loops resolve -> dialog -> action until the file
  is open or the user quits; `presentation/ports/startup_dialogs_port.py`.
- `presentation/storage/shutdown_presenter.py`: synchronous flush; on failure "Quit without saving" /
  "Retry" (ADR-032).
- External modification dialog: "Reload the file" / "Keep Concentrator's version" (ADR-033).
- Unguarded single-instance mode: modal warning before the data file is opened and a status bar
  indicator for the session (ADR-031).
- `presentation/storage/storage_messages.py`: `ValidationResult` -> translated lines
  (`error.<code>` + `field.<path without indexes>`).
- `presentation/shell/status_bar_presenter.py` (the status bar leaves `ShellPresenter`) and
  `presentation/shell/language_switcher.py` (settings, translator, startup hint, re-render).
- Status bar: `SaveStateEnum` -> text and tooltip (`Saved at 17:44:03`, `Saving...`,
  `Unsaved changes`, `Save failed: <reason>. Retrying.`, `No data file`).
- `ui/windows/first_run_dialog.py`, `ui/windows/recovery_dialog.py` (+ their panels),
  `ui/windows/startup_dialogs.py` (implements `StartupDialogsPort`).
- `ui/support/modal_host.py` (ADR-036): `ModalHost(window, opacity_percent)` runs every modal dialog
  of `QtDialogService` once the main window exists: dimming layer over the window's client area,
  dialog centered on the window, moves clamped to the window's frame (Windows `WM_WINDOWPOSCHANGING`
  in a native event filter; the main window moving or resizing moves the dialog back inside),
  minimized window restored first. The clamping
  geometry is a pure function, unit-tested without Qt windows. Dialogs shown before the main window
  exists open centered on the screen; the Windows file picker gets the dimming layer but Windows
  places it (ADR-036).

### Bootstrap

Insert after the catalogs (phase 0 step 5; the dialogs are translated, ADR-027): unguarded warning
if needed -> resolve startup -> dialogs -> load -> apply `UserSettings.language` to the translator.
On close, `MainWindow.closeEvent` flushes through the shutdown presenter; on failure ask "Quit
without saving" / "Retry" (the presenter gets its dialog service, parented to the window, through
`attach` once the window exists; ADR-036). `QGuiApplication.commitDataRequest` (Windows session
end) and `aboutToQuit` (fallback) flush synchronously without dialog (ADR-032). The self-check also
round-trips an in-memory `UserData` through codec, schemas and mappers (ADR-034).

## File format (version 1, phase 1 content)

```toml
# Concentrator user data. Schema version 1.
# Close Concentrator before editing this file by hand. Comments are not preserved.
schema_version = 1
saved_at = '2026-11-06T16:44:03Z'
app_version = '0.1.0'

[settings]
id = '019a5c1e-7a40-7c3e-9d5a-1f2b3c4d5e6f'
created_at = '2026-11-06T16:40:00Z'
updated_at = '2026-11-06T16:44:03Z'
language = 2
```

Rules for all later sections (ADR-035): TOML 1.0, snake_case bare keys, stable order (root scalar keys
first, then `[section]` and `[[section]]` in schema order), nested objects as one-line inline tables,
other arrays one element per line with a trailing comma, multi-line text as arrays of lines, paths and
URLs as one flat string with `/`, timestamps and dates as quoted strings. Strings are `'...'`,
`'''...'''` when they contain `'`, `"..."` with escapes only when they contain `'''` or a control
character other than tab. No `null`: an unset optional value is an absent key, an empty collection is
`key = []`. Every new field has a default so older development files still load.

## `concentrator.ini` (new keys)

```ini
[paths]
default_data_file = {appdata}/Concentrator/concentrator.toml

[ui]
dialog_overlay_opacity_percent = 10
startup_dialog_min_width_px = 560
dialog_spacing_px = 10

[storage]
save_debounce_ms = 500
save_max_delay_ms = 1500
replace_retry_count = 5
replace_retry_delay_ms = 200
failed_save_retry_ms = 10000
shutdown_flush_timeout_ms = 5000
blocking_write_timeout_ms = 5000
daily_backup_enabled = true
daily_backup_retention_days = 7
```

`save_max_delay_ms` (500..60000) must not be lower than `save_debounce_ms` (`CONFIG_VALUE_INVALID`).
`blocking_write_timeout_ms` (500..60000) bounds the synchronous startup writes (ADR-028).
`dialog_overlay_opacity_percent` (0..50) is the darkening of the main window behind a dialog (ADR-036).
`default_data_file` changes extension (phase 0 key).

The remembered data file path is stored in `ui-state.ini` under `storage/data_file_path`, the
language hint under `shell/language_hint`.

## Error codes (2xxx)

| Code | Name | Severity | Meaning |
|---|---|---|---|
| 2001 | `STORAGE_FILE_NOT_FOUND` | ERROR | file absent |
| 2002 | `STORAGE_FILE_UNREADABLE` | ERROR | `OSError` while reading (permission, lock) |
| 2003 | `STORAGE_ENCODING_INVALID` | ERROR | not UTF-8 |
| 2004 | `STORAGE_SYNTAX_INVALID` | ERROR | not valid TOML, duplicate keys included (`params`: `line`, `column`) |
| 2005 | `STORAGE_FIELD_MISSING` | ERROR | pydantic `missing` |
| 2006 | `STORAGE_FIELD_UNEXPECTED` | ERROR | pydantic `extra_forbidden` |
| 2007 | `STORAGE_FIELD_INVALID_TYPE` | ERROR | pydantic `*_type`, `*_parsing` |
| 2008 | `STORAGE_FIELD_INVALID_VALUE` | ERROR | other pydantic errors |
| 2009 | `STORAGE_SCHEMA_VERSION_UNSUPPORTED` | CRITICAL | file newer than the app |
| 2010 | `STORAGE_WRITE_FAILED` | ERROR | writing the temporary file failed |
| 2011 | `STORAGE_VERIFY_FAILED` | ERROR | re-read hash differs |
| 2012 | `STORAGE_REPLACE_FAILED` | ERROR | `os.replace` still failing after retries |
| 2013 | `STORAGE_BACKUP_FAILED` | WARNING | `.bak` or daily copy failed (save still succeeded) |
| 2014 | `STORAGE_FLUSH_TIMEOUT` | ERROR | shutdown flush exceeded its timeout |
| 2015 | `STORAGE_FILE_ALREADY_EXISTS` | ERROR | create on an existing path |
| 2016 | `STORAGE_DIRECTORY_NOT_WRITABLE` | ERROR | cannot create the folder or the file |
| 2017 | `STORAGE_DISK_FULL` | ERROR | `errno.ENOSPC` |
| 2021 | `STORAGE_FILE_CHANGED_EXTERNALLY` | ERROR | the file changed on disk since the last load or save (ADR-033) |

2018 and 2019 are reserved for phase 4. 2020 (`STORAGE_DUPLICATE_KEY`, JSON5 only) is retired and never
reused (ADR-035).

## Tests

- Codec: valid TOML (comments, CRLF, native dates turned into text); syntax error and duplicate key
  with line/column; every quoting case round-trips through `tomllib` (apostrophes at either end, `''`,
  `'''`, tab, newline, CR, NUL, DEL, backslashes, double quotes, non-ASCII, emoji); emitter layout
  (root keys before tables, empty collection `key = []`, unset optional value omitted).
- Pydantic mapper: each pydantic error family maps to the right code and dotted field.
- Mappers: round trip domain -> file -> domain is identical; unknown enum int -> `UNKNOWN` ->
  `ENUM_VALUE_UNKNOWN` from the rules.
- Atomic writer (real files in `tmp_path`): nominal; `os.replace` raising `PermissionError` twice then
  succeeding; always failing -> `STORAGE_REPLACE_FAILED` and the main file untouched; hash mismatch.
- Recovery matrix (parametrized): main valid/invalid/absent x tmp valid/invalid/absent x bak
  valid/invalid/absent -> expected `StartupStepEnum` and candidate order.
- `SaveCoordinator` with `ManualScheduler`, `FakeClock`, fake file port: debounce coalesces 10 changes
  into 1 save; continuous changes still save after `save_max_delay_ms`; change during save triggers a
  second save; failure -> `FAILED` then retry; external change -> `FAILED` without retry; flush.
- External modification: unchanged file saves; changed file -> 2021 and nothing written; "Reload"
  and "Keep Concentrator's version" both tested; touched but identical file is not a conflict.
- "Keep the current file" renames the `.tmp`; "Retry" re-resolves; config rejects
  `save_max_delay_ms < save_debounce_ms`.
- Clock: `now_utc()`/`now_local()` in whole seconds, `monotonic()` at full precision.
- Daily backup retention deletes only `<stem>-YYYY-MM-DD.toml` files (other files in the folder
  stay).
- Generic store reader/writer: all nine operations, including `copy_business` (new id and timestamps)
  and `copy_technical` (equal object, store unchanged).
- Storage messages: translated text contains the field label in both languages.
- UI smoke: first-run and recovery dialogs render their snapshots.
- Modal host: the clamping function (inside, past each edge, dialog larger than the window, offset
  window); the dimming layer is shown while a dialog runs and hidden after, and covers the window
  after a resize; the dialog opens centered; the shutdown questions are parented to the window.

## Benchmark

`scripts/bench_storage.py [--tasks 1000] [--events 20] [--repeat 3]` builds a synthetic document
shaped like task data (4 lines of text per task, some with apostrophes, a path and a URL; 20 history
events per task), times `TomlCodec.decode`, `TomlCodec.encode` and the full read and write pipelines,
and prints the size and MB/s. 1,000 tasks are enough (owner decision). Report the numbers at the
review; the phase 8 startup target (2 s) depends on them.

## Acceptance criteria

- [ ] With no `ui-state.ini`, the first-run dialog appears; each of its actions works.
- [ ] Toggling the language writes the file within about 1 s; the status bar shows `Saved at ...`.
- [ ] 20 fast toggles produce at most 2-3 writes (debounce) and the final state is saved.
- [ ] Killing the process from Task Manager during toggles never leaves an unreadable main file.
- [ ] A hand-corrupted file shows a translated, field-level message and offers the backup.
- [ ] A read-only or locked file shows `Save failed` in the status bar, data stays in memory, and the
      save succeeds automatically once the lock is released.
- [ ] Quitting flushes pending changes.
- [ ] Editing the file by hand while the app runs, then toggling the language, shows the
      "Reload / Keep Concentrator's version" choice; both choices behave as described.
- [ ] When the instance lock cannot be created, a warning appears before the data file is opened
      and the status bar keeps a warning indicator.
- [ ] Every dialog shown while the main window is open dims the window by 10 %, opens centered on it
      and cannot be dragged outside it.
- [ ] Gates green, coverage thresholds met; benchmark numbers reported.

## Manual test script

1. Delete `%APPDATA%\Concentrator\ui-state.ini`, start, choose "Create at default location".
2. Toggle FRA/ENG, open the file in Notepad: language value changes, `saved_at` updates.
3. Close the app, edit `language = 'x'`, start: read the message, restore the backup.
4. Lock the file from PowerShell:
   `$f=[IO.File]::Open("$env:APPDATA\Concentrator\concentrator.toml",'Open','Read','None')`, toggle
   the language, watch the status bar, then `$f.Close()` and wait for the automatic retry.
5. Toggle repeatedly and kill `Concentrator.exe` from Task Manager; restart.
6. While the app runs, change `language` in Notepad and save; toggle the language in the app: choose
   "Reload", then repeat and choose "Keep Concentrator's version".
7. With the external change question open (step 6): the window behind is 10 % darker, module bar and
   status bar included; the question is centered on the window; dragging it by its title bar stops at
   each edge of the window; with the window maximized, then small, then on a second screen. Repeat
   with the shutdown question (lock the file as in step 4, then close the window).

## Review gate questions

1. Default location `%APPDATA%\Concentrator\` (outside OneDrive-synced Documents) acceptable?
2. Keep daily backups (7 days) on by default?
3. Benchmark result with TOML: is the read time for 1,000 tasks acceptable?
