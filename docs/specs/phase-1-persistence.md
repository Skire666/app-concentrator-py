# Phase 1 — User data persistence (JSON5)

Depends on: phase 0. Branch: `phase-1-persistence`.

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
  - `load(path) -> DataResult[UserData]`
  - `probe(path) -> DataResult[RecoveryReport]` (state of main, `.tmp`, `.bak`: absent / valid /
    invalid, `saved_at`, issues)
  - `restore(path, source: RecoverySourceEnum) -> DataResult[UserData]`
  - `create(path, data) -> ValidationResult` (fails with `STORAGE_FILE_ALREADY_EXISTS`)
  - `quarantine(path) -> DataResult[str]` (renames to `.corrupt-YYYYMMDD-HHMMSS`)
  - `save_async(path, data, revision, on_done)`; `flush(timeout_ms) -> ValidationResult`
- `ports/user_data_session_port.py`: `current() -> UserData`, `revision() -> int`, `reset(data)`.
- `ports/user_settings_reader_port.py`, `ports/user_settings_writer_port.py` (`read`, `update`).
- `storage/startup_commands.py`: `resolve_startup(...)` returns a `StartupStepEnum`
  (`READY`, `NEEDS_LOCATION`, `NEEDS_RECOVERY`, `FATAL`) with the data needed by the dialogs;
  `create_at(path)`, `open_existing(path)`, `restore(source)`, `start_empty()`.
- `storage/save_coordinator.py`: subscribes to `UserDataChangedEvent`; debounce
  `storage.save_debounce_ms`; one save in flight; if the revision changed meanwhile, saves again; on
  failure keeps data in memory and retries every `storage.failed_save_retry_ms`; publishes
  `SaveStatusChangedEvent(state: SaveStateEnum, saved_at, issues)`; `flush_for_shutdown()`.
- `SaveStateEnum`: `UNKNOWN=-1, UNSET=0, NO_FILE=1, SAVED=2, PENDING=3, SAVING=4, FAILED=5`.
- `settings/settings_commands.py`: `change_language(language)`; `settings/settings_queries.py`.

### Infrastructure (`infrastructure/persistence/`)

| Module | Responsibility |
|---|---|
| `json5_codec.py` | `decode(text) -> DataResult[object]` (`json5.loads`; `ValueError` -> `STORAGE_SYNTAX_INVALID`, line and column logged); `encode(obj) -> str` |
| `schemas/` | pydantic DTOs, `ConfigDict(strict=True, extra="forbid", frozen=True)`: `UserDataSchema`, `UserSettingsSchema` |
| `pydantic_error_mapper.py` | `ValidationError` -> `ValidationResult` (mapping in `AGENTS.md` §7.1) |
| `mappers/` | schema <-> domain, enums through `BaseIntEnum.parse`, then domain `*Rules` |
| `json5_user_data_file.py` | implements `UserDataFilePort`; read pipeline; write pipeline; header comment |
| `atomic_file_writer.py` | steps 1-4 of `AGENTS.md` §7.2, retries, error codes |
| `daily_backup.py` | one copy per day into `paths.backup_dir`, retention |
| `recovery_inspector.py` | builds `RecoveryReport` |
| `writer_thread.py` | `ThreadPoolExecutor(max_workers=1, thread_name_prefix="writer")`, results posted with `MainThreadDispatcherPort` |
| `user_data_store.py` | implements `UserDataSessionPort`; holds the current `UserData`; publishes `UserDataChangedEvent(revision)` |
| `store_collection.py` | generic `StoreCollectionReader[E, C]` and `StoreCollectionWriter[E, C]` implementing the nine operations over a section accessor (tested with a test-only entity and collection) |
| `store_user_settings.py` | singleton reader/writer for `UserSettings` |

### Presentation and UI

- `presentation/storage/first_run_presenter.py` + `FirstRunSnapshot`: default path shown, actions
  "Use the file found at the default location" (only if it exists), "Create at default location",
  "Create elsewhere...", "Open existing file...", "Quit".
- `presentation/storage/recovery_presenter.py` + `RecoverySnapshot`: translated problem description
  (first issues, field labels), candidates with their `saved_at`, actions "Restore", "Choose another
  file...", "Start with an empty file", "Quit".
- `presentation/storage/storage_messages.py`: `ValidationResult` -> translated lines
  (`error.<code>` + `field.<path without indexes>`).
- Status bar: `SaveStateEnum` -> text and tooltip (`Saved at 17:44:03`, `Saving...`,
  `Unsaved changes`, `Save failed: <reason>. Retrying.`, `No data file`).
- `ui/windows/first_run_dialog.py`, `ui/windows/recovery_dialog.py` (+ their panels).

### Bootstrap

Insert after the single instance guard (phase 0 step 4): resolve startup -> dialogs -> load ->
apply `UserSettings.language` to the translator. On quit, `SaveCoordinator.flush_for_shutdown()`
before anything else; on failure ask "Quit without saving?" / "Retry".

## File format (version 1, phase 1 content)

```json5
// Concentrator user data. Schema version 1.
// Close Concentrator before editing this file by hand. Comments are not preserved.
{
  schema_version: 1,
  saved_at: "2026-11-06T16:44:03Z",
  app_version: "0.1.0",
  settings: {
    id: "019a5c1e-7a40-7c3e-9d5a-1f2b3c4d5e6f",
    created_at: "2026-11-06T16:40:00Z",
    updated_at: "2026-11-06T16:44:03Z",
    language: 2,
  },
}
```

Rules for all later sections: snake_case keys, stable order, arrays for collections, multi-line text
as arrays of lines, paths and URLs as one flat string with `/`, no `null` for collections (empty
array), every new field has a default so older development files still load.

## `concentrator.ini` (new keys)

```ini
[storage]
save_debounce_ms = 500
replace_retry_count = 5
replace_retry_delay_ms = 200
failed_save_retry_ms = 10000
shutdown_flush_timeout_ms = 5000
daily_backup_enabled = true
daily_backup_retention_days = 7
```

The remembered data file path is stored in `ui-state.ini` under `storage/data_file_path`.

## Error codes (2xxx)

| Code | Name | Severity | Meaning |
|---|---|---|---|
| 2001 | `STORAGE_FILE_NOT_FOUND` | ERROR | file absent |
| 2002 | `STORAGE_FILE_UNREADABLE` | ERROR | `OSError` while reading (permission, lock) |
| 2003 | `STORAGE_ENCODING_INVALID` | ERROR | not UTF-8 |
| 2004 | `STORAGE_SYNTAX_INVALID` | ERROR | not valid JSON5 (`params`: `line`, `column`) |
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

## Tests

- Codec: valid JSON5 (comments, trailing commas, unquoted keys); syntax error with line/column.
- Pydantic mapper: each pydantic error family maps to the right code and dotted field.
- Mappers: round trip domain -> file -> domain is identical; unknown enum int -> `UNKNOWN` ->
  `ENUM_VALUE_UNKNOWN` from the rules.
- Atomic writer (real files in `tmp_path`): nominal; `os.replace` raising `PermissionError` twice then
  succeeding; always failing -> `STORAGE_REPLACE_FAILED` and the main file untouched; hash mismatch.
- Recovery matrix (parametrized): main valid/invalid/absent x tmp valid/invalid/absent x bak
  valid/invalid/absent -> expected `StartupStepEnum` and candidate order.
- `SaveCoordinator` with `ManualScheduler`, `FakeClock`, fake file port: debounce coalesces 10 changes
  into 1 save; change during save triggers a second save; failure -> `FAILED` then retry; flush.
- Generic store reader/writer: all nine operations, including `copy_business` (new id and timestamps)
  and `copy_technical` (equal object, store unchanged).
- Storage messages: translated text contains the field label in both languages.
- UI smoke: first-run and recovery dialogs render their snapshots.

## Benchmark

`scripts/bench_storage.py` builds a synthetic 5 MB JSON5 document shaped like task data (arrays of
objects with string arrays), times `json5.loads`, `json5.dumps` and the full pydantic pipeline, and
prints MB/s. Report the numbers at the review: they decide whether a faster JSON5 decoder is needed
before phase 5 (see `docs/decisions.md`, ADR-002). The JSON5 format itself is not in question.

## Acceptance criteria

- [ ] With no `ui-state.ini`, the first-run dialog appears; each of its actions works.
- [ ] Toggling the language writes the file within about 1 s; the status bar shows `Saved at ...`.
- [ ] 20 fast toggles produce at most 2-3 writes (debounce) and the final state is saved.
- [ ] Killing the process from Task Manager during toggles never leaves an unreadable main file.
- [ ] A hand-corrupted file shows a translated, field-level message and offers the backup.
- [ ] A read-only or locked file shows `Save failed` in the status bar, data stays in memory, and the
      save succeeds automatically once the lock is released.
- [ ] Quitting flushes pending changes.
- [ ] Gates green, coverage thresholds met; benchmark numbers reported.

## Manual test script

1. Delete `%APPDATA%\Concentrator\ui-state.ini`, start, choose "Create at default location".
2. Toggle FRA/ENG, open the file in Notepad: language value changes, `saved_at` updates.
3. Close the app, edit `language: "x"`, start: read the message, restore the backup.
4. Lock the file from PowerShell:
   `$f=[IO.File]::Open("$env:APPDATA\Concentrator\concentrator.json5",'Open','Read','None')`, toggle
   the language, watch the status bar, then `$f.Close()` and wait for the automatic retry.
5. Toggle repeatedly and kill `Concentrator.exe` from Task Manager; restart.

## Review gate questions

1. Default location `%APPDATA%\Concentrator\` (outside OneDrive-synced Documents) acceptable?
2. Keep daily backups (7 days) on by default?
3. Benchmark result: stay on the `json5` package or evaluate a faster JSON5 decoder now?
