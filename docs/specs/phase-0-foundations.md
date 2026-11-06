# Phase 0 — Foundations and walking skeleton

Depends on: nothing. Branch: `phase-0-foundations`.

## Goal

A Windows 11 executable that starts without a console, refuses a second instance, shows the main
window shell (module bar, three empty pages, status bar with a live FRA/ENG switch), and contains
every cross-cutting mechanism later phases rely on: results and error codes, enums, configuration,
logging, i18n, render coordination, action gating, scheduling, build and quality gates.

## In scope

- Repository files: `README.md`, `CONTRIBUTING.md`, `USAGE.md` skeletons, `.python-version` (3.14),
  `.vscode/` (`settings.json`, `extensions.json`, `launch.json`), `tests/conftest.py`.
- `scripts/`: `check.py`, `coverage_gate.py`, `clean.py`, `build.py`.
- Domain kernel (`domain/common/`), application kernel (ports, `EventBus`, `AppConfig`, `AppTicker`),
  infrastructure kernel (paths, config, logging, i18n, clock, ids, Windows shell, Qt kernel adapters),
  presentation kernel, shell UI, bootstrap.

## Out of scope

User data file and persistence (phase 1), any feature content in the pages, sounds.

## Deliverables

### Domain (`concentrator/domain/common/`)

| Module | Content |
|---|---|
| `base_int_enum.py` | `BaseIntEnum(IntEnum)` with `parse(value) -> Self` (unknown value -> `UNKNOWN`), `is_set` property (not `UNSET`/`UNKNOWN`) |
| `severity_enum.py` | `SeverityEnum`: `UNKNOWN=-1, UNSET=0, SKIPPED=1, SUCCESS=2, WARNING=3, ERROR=4, CRITICAL=5` |
| `error_code_enum.py` | `ErrorCodeEnum` with the phase 0 codes below; `category` property derived from the range |
| `validation_issue.py` | frozen `ValidationIssue(code, severity, field="", params=())` |
| `validation_result.py` | `ValidationResult` (API in `AGENTS.md` §5.3) |
| `data_result.py` | `DataResult[T]` |
| `identified.py` | `Identified` Protocol: `id: str`, `created_at: datetime`, `updated_at: datetime` |
| `time_rules.py` | `TimeRules.validate_utc(value, field)` (aware, UTC offset 0) |

### Application (`concentrator/application/`)

- `ports/`: `clock_port.py`, `id_generator_port.py`, `scheduler_port.py` (`call_soon`, `call_later`,
  `ScheduledCallPort.cancel()`), `main_thread_dispatcher_port.py`, `translator_port.py`
  (`tr`, `tr_plural`, `language`, `set_language`), `log_feed_port.py` (`entries_since(sequence)`),
  `view_preferences_port.py` (`get_text`, `set_text`, `remove`).
- `common/event_bus.py`: synchronous `EventBus` (`subscribe(event_type, handler)`, `publish(event)`);
  handler failures are logged and do not stop other handlers.
- `common/app_config.py`: frozen dataclasses `AppConfig`, `AppSection`, `PathsSection`, `UiSection`,
  `TimerSection`, `LoggingSection`, `I18nSection` (plain Python types, no pydantic).
- `common/app_ticker.py`: `AppTicker.tick()` fans out to registered tick handlers (empty in phase 0).

Also in the domain: `domain/settings/language_enum.py` with `LanguageEnum`
(`UNKNOWN=-1, UNSET=0, ENGLISH=1, FRENCH=2`) and its ISO codes `en`, `fr`.

### Infrastructure (`concentrator/infrastructure/`)

| Module | Content |
|---|---|
| `system/app_paths.py` | `AppPaths`: project root (dev) or exe folder (frozen, `sys.frozen`), bundle assets folder (`getattr(sys, "_MEIPASS", ...)`), ini location, token resolution `{appdata}`, `{localappdata}`, `{app_dir}` |
| `system/system_clock.py` | `SystemClock(ClockPort)`: `datetime.now(UTC)`, `datetime.now().astimezone()`, `time.monotonic()` |
| `system/uuid7_id_generator.py` | `Uuid7IdGenerator(IdGeneratorPort)` using `uuid.uuid7()` |
| `system/windows_shell.py` | `set_app_user_model_id(app_id) -> ValidationResult` (ctypes, `win32` only, no-op elsewhere) |
| `config/ini_config_loader.py` | `configparser` (interpolation off) -> pydantic `AppConfigSchema` (`extra="forbid"`) -> `AppConfig`; returns `DataResult[AppConfig]` |
| `i18n/json_catalog_translator.py` | loads `en.json`, `fr.json`; `tr`, `tr_plural` (FR: count <= 1 is singular), fallback chain, single WARNING per missing key |
| `logging/logging_setup.py` | two stages (ADR-026): `configure_logging` installs the root level, the ring buffer handler, the optional stream handler, `captureWarnings` and a `MemoryHandler` without target (no folder, no file); `LoggingRuntime.attach_log_file()` then creates the rotating file handler, flushes the buffered records into it and opens the `faulthandler` file |
| `logging/ring_buffer_handler.py` | thread-safe bounded buffer with sequence numbers; implements `LogFeedPort` |
| `logging/exception_hooks.py` | `sys.excepthook`, `threading.excepthook` -> CRITICAL log + registered callback (error dialog) |
| `qt/qt_scheduler.py` | `QtScheduler(SchedulerPort)` with single-shot `QTimer` handles |
| `qt/qt_main_thread_dispatcher.py` | `QObject` with a `Signal(object)` connected `Qt.QueuedConnection` |
| `qt/qt_single_instance_guard.py` | `QLockFile` in `{localappdata}/Concentrator/` + `QLocalServer` named `<app.single_instance_key>-<user hash>`; `acquire() -> DataResult[bool]` (False = another instance was notified) and `activation_requested` callback |
| `qt/qsettings_view_preferences.py` | `QSettings(path, IniFormat)` implementing `ViewPreferencesPort` |
| `qt/qt_log_bridge.py` | `qInstallMessageHandler` -> logger `qt` |

### Presentation (`concentrator/presentation/`)

- `common/action_id_enum.py` (`SHELL_SHOW_FOCUS`, `SHELL_SHOW_JOURNAL`, `SHELL_SHOW_SETTINGS`,
  `SHELL_TOGGLE_LANGUAGE`; later phases append values, never renumber).
- `common/render_section_enum.py` (`SHELL`, `STATUS_BAR`; later phases append).
- `common/render_coordinator.py`, `common/action_gate.py` (API in `AGENTS.md` §8.2-8.3).
- `common/button_snapshot.py`, `common/field_error_snapshot.py`, `common/form_state.py` (generic,
  tested with a test-only draft type).
- `ports/dialog_port.py`: `DialogPort` with `confirm(title, message, accept_text, reject_text) -> bool`,
  `inform(...)`, `error(...)`, `choose_open_file(...)`, `choose_save_file(...)`,
  `choose_folder(...)` returning `str | None`.
- `shell/shell_snapshot.py`: window title, module buttons (text, tooltip, checked, highlighted), active
  page index, status text, language button text and tooltip.
- `shell/shell_presenter.py`: page switching, language toggle (in-memory in phase 0), status text.

### UI (`concentrator/ui/`)

| Tier | Class | Notes |
|---|---|---|
| window | `MainWindow` (`QWidget` top level, not `QMainWindow`, so the module bar spans the full height) | layout: `QHBoxLayout[ModuleBarPanel, QVBoxLayout[QStackedWidget, StatusBarPanel]]`; restores geometry from `ui-state.ini`; registers panels; wires signals |
| panel | `ModuleBarPanel` | fixed width `ui.module_bar_width_px`; three checkable buttons, icons + text; emits `action_requested(int)` |
| panel | `StatusBarPanel` | one line: save state label (left), language button (right) |
| window (page) | `FocusPage` | composes zone 1 and zone 2 panels in a horizontal `QSplitter`, initial ratio `ui.zone1_ratio_percent`, sizes persisted; zone 2 is a vertical stack of panels; placeholders for now |
| window (page) | `JournalPage`, `SettingsPage` | placeholders |
| widget | `SnapshotButton` | `QPushButton` with `apply(ButtonSnapshot)` |
| support | `QtDialogService(DialogPort)` | `QMessageBox`/`QFileDialog` with catalog button texts |

### Bootstrap (`concentrator/bootstrap/`)

`app.py` `main() -> int` runs this exact sequence:

1. Load `AppConfig` (pure Python, no Qt needed yet).
2. If the config loaded: `windows_shell.set_app_user_model_id(app.app_user_model_id)`. Then
   `QApplication(sys.argv)` with organization and application names and the application icon.
3. If the config failed: logging is not available yet, so show a plain English `QMessageBox` with the
   error codes and the ini path, exit code 1. Otherwise configure logging stage 1 (ring buffer,
   in-memory startup buffer, no log file), exception hooks, Qt message bridge.
4. Single instance guard. If another instance answered: log INFO and exit 0 before any window,
   without ever opening the log file. Otherwise (lock held, or running unguarded after a lock error)
   attach the rotating log file, flush the buffered startup records into it, and enable
   `faulthandler` into its file (ADR-026).
5. Load catalogs; on failure fall back to English keys and log ERROR.
6. Build adapters, `EventBus`, `RenderCoordinator`, `ActionGate`, presenters, `MainWindow`.
7. Start the `QTimer` ticking `AppTicker.tick()` every `timer.tick_interval_ms`.
8. Show the window (restored geometry, default size from the ini on first run), `app.exec()`.
9. On `aboutToQuit`: stop the ticker, save UI state, release the instance guard, flush logging.

`CONCENTRATOR_SELF_CHECK=1` (environment variable, not a command-line option) runs steps 1-3 and 5
(no single instance guard; the log file is attached right after step 3) plus an asset presence check,
writes the result to the log and exits 0
or 1 without showing a window. `scripts/build.py` uses it to validate the frozen bundle.

## `concentrator.ini` (phase 0 keys)

```ini
[app]
name = Concentrator
organization = skire666
app_user_model_id = skire666.Concentrator
single_instance_key = concentrator

[paths]
default_data_file = {appdata}/Concentrator/concentrator.json5
ui_state_file = {appdata}/Concentrator/ui-state.ini
log_dir = {localappdata}/Concentrator/logs
backup_dir = {appdata}/Concentrator/backups

[ui]
module_bar_width_px = 100
zone1_ratio_percent = 70
default_window_width_px = 1400
default_window_height_px = 860
min_window_width_px = 1000
min_window_height_px = 640
action_cooldown_ms = 100
slow_action_threshold_ms = 200

[timer]
tick_interval_ms = 100

[logging]
level = INFO
file_name = concentrator.log
file_max_bytes = 2000000
file_backup_count = 5
journal_buffer_size = 5000

[i18n]
default_language = en
fallback_language = en
```

Every key is required; `AppConfigSchema` validates types and ranges (e.g. `module_bar_width_px` in
40..400, `zone1_ratio_percent` in 30..90, `action_cooldown_ms` >= 100).

## Error codes (phase 0)

| Code | Name | Meaning |
|---|---|---|
| 1001 | `REQUIRED_VALUE_MISSING` | value absent or blank |
| 1002 | `VALUE_OUT_OF_RANGE` | numeric value outside limits (`params`: `min`, `max`) |
| 1003 | `TEXT_TOO_LONG` | text longer than allowed (`params`: `max`) |
| 1004 | `FORMAT_INVALID` | value does not match the expected format |
| 1005 | `ENTITY_NOT_FOUND` | no entity with this id |
| 1006 | `ENTITY_DUPLICATE_ID` | id already used |
| 1007 | `ENUM_VALUE_UNSET` | enum left at `UNSET` where a value is required |
| 1008 | `ENUM_VALUE_UNKNOWN` | enum value not understood |
| 1009 | `DATETIME_NOT_UTC` | naive or non-UTC timestamp |
| 3001 | `CONFIG_FILE_NOT_FOUND` | `concentrator.ini` missing |
| 3002 | `CONFIG_SYNTAX_INVALID` | ini cannot be parsed |
| 3003 | `CONFIG_KEY_MISSING` | required key absent |
| 3004 | `CONFIG_VALUE_INVALID` | key present, value invalid |
| 3101 | `CATALOG_FILE_NOT_FOUND` | i18n file missing |
| 3102 | `CATALOG_SYNTAX_INVALID` | i18n file is not valid JSON |
| 3103 | `CATALOG_KEY_MISSING` | key missing in a catalog |
| 7201 | `INSTANCE_LOCK_FAILED` | lock file cannot be created or acquired |
| 7202 | `INSTANCE_SERVER_FAILED` | local server cannot listen |
| 7203 | `APP_USER_MODEL_ID_FAILED` | Windows shell call failed |

## i18n keys (families)

`app.title`, `shell.module.focus|journal|settings` (+ `.tooltip`), `shell.language.button.en|fr`,
`shell.language.tooltip.en|fr`, `status.save.none`, `dialog.button.ok|cancel|yes|no`,
`dialog.error.title`, `error.<code_name>` for every code above, `format.date|time|datetime`.

## Scripts

- `check.py`: runs the six gates of `AGENTS.md` §14 in order with `subprocess.run(check=False)`,
  prints a summary table, exit code 1 at the first failure.
- `coverage_gate.py`: reads `coverage.json`, aggregates covered/total lines and branches per prefix
  (`concentrator/domain/`, `concentrator/application/`, `concentrator/presentation/`, overall),
  compares with the thresholds of `AGENTS.md` §12, prints a table, exit code 1 on failure.
- `clean.py`: deletes `build/`, `dist/`, `.pytest_cache/`, `.ruff_cache/`, `htmlcov/`, `.coverage*`,
  `coverage.json`, every `__pycache__/`; `--all` also deletes `.venv/`; `--dry-run` lists only.
- `build.py`: `PyInstaller.__main__.run([...])` with `--onedir --windowed --noupx --noconfirm --clean
  --name Concentrator --icon assets/icons/concentrator.ico --specpath build --add-data
  assets/i18n<sep>assets/i18n ...` (separator `os.pathsep`), then copies `assets/config/concentrator.ini`
  next to `Concentrator.exe`, then runs the self-check and fails if it fails.

If `assets/icons/concentrator.ico` does not exist yet, add `scripts/make_placeholder_icon.py` that
draws a simple icon with `QImage`/`QPainter` and saves 16-256 px sizes as `.ico`.

## Tests

- Domain kernel: every factory and query of `ValidationResult`/`DataResult`, merge semantics, worst
  severity, `UNKNOWN` treated as failure, `BaseIntEnum.parse`.
- Architecture: every `BaseIntEnum` subclass in `concentrator` has `UNKNOWN=-1`, `UNSET=0`, a name
  ending in `Enum`, a module ending in `_enum`; no `print(` in `concentrator/`; every package has an
  `__init__.py`.
- Catalog parity: same keys and same placeholders in `en.json` and `fr.json`; every `ErrorCodeEnum`
  and `ActionIdEnum` member has its key.
- `RenderCoordinator`: three requests in one turn produce one render; equal snapshot skips render;
  `request_all` renders every section once.
- `ActionGate`: busy action ignored; cooldown releases after 100 ms (manual scheduler); slow action
  logged at INFO (caplog); interactive action not logged; token API.
- `IniConfigLoader`: valid file; missing file; syntax error; missing key; invalid value; tokens
  resolved.
- `JsonCatalogTranslator`: fallback chain, single warning, French plural for 0 and 1.
- `RingBufferHandler`: bounded size, sequence numbers, `entries_since`.
- UI (`pytest-qt`, marker `ui`): `MainWindow` builds; module bar width equals the ini value;
  rendering a shell snapshot switches the page and the language button text.

## Acceptance criteria

- [ ] `uv sync` then `uv run python scripts/check.py` is green; coverage thresholds met.
- [ ] `uv run concentrator` opens the window without any console window.
- [ ] Launching a second time brings the first window to the front (or flashes its taskbar button)
      and the second process exits.
- [ ] Module buttons switch pages; the active button is checked.
- [ ] The language button switches every visible text between English and French instantly.
- [ ] Window geometry and splitter position are restored after restart.
- [ ] Changing `module_bar_width_px` in the ini next to the built exe changes the bar width without
      rebuilding.
- [ ] Deleting a key from the ini shows an explicit error at startup.
- [ ] `uv run python scripts/build.py` produces `dist/Concentrator/Concentrator.exe`, the self-check
      passes, and the exe runs on a Windows account without Python installed.
- [ ] The log file exists in `%LOCALAPPDATA%\Concentrator\logs` and contains the startup sequence.
- [ ] The taskbar shows the Concentrator icon, not the Python icon.

## Manual test script

1. `uv run concentrator`; check the module bar (100 px, full height) and the status bar (one line).
2. Click the three module buttons; click the language button twice.
3. Run `uv run concentrator` again while the first is open.
4. Resize and move the window, drag the splitter, close, reopen.
5. Build, open `dist\Concentrator`, edit `concentrator.ini` (`module_bar_width_px = 140`), start.
6. Rename the ini, start: an error dialog must explain which file is missing.

## Review gate questions

1. Placeholder icon acceptable, or will you provide `concentrator.ico` before phase 2?
2. Should closing the window quit the app (default) or hide it to the tray?
3. Language button shows the current language (default: `ENG` while in English) or the target one?
