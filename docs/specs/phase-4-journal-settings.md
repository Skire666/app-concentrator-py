# Phase 4 — Journal (Menu B) and settings (Menu C)

Depends on: phase 1 (phase 3 for the chime section of the settings). Branch:
`phase-4-journal-settings`.

## Goal

Menu B shows the application log live with level filters and search. Menu C exposes the editable
user settings with real-time validation, `is_dirty`, Save and Revert, plus read-only information
(paths, version).

## Journal (Menu B)

- Source: the in-memory ring buffer (`LogFeedPort`), i.e. every record since the app started, up to
  `logging.journal_buffer_size`. Older history stays in the log files ("Open log folder").
- `JournalPresenter` polls `entries_since(last_sequence)` on `AppTicker` ticks only while the
  journal page is visible; renders only when something changed.
- Table columns: time (local, `HH:MM:SS.mmm`), level, source (logger name), thread, message (first
  line). A detail pane shows the selected entry in full (multi-line message, traceback), selectable.
- Filters: one checkable toggle per level (Debug, Info, Warning, Error, Critical) with counts; text
  search over message and source (case- and accent-insensitive); filters persisted in
  `ui-state.ini`.
- Toolbar: Follow (auto-scroll to newest, on by default), Pause (freeze the view; a counter shows
  hidden new entries), Copy (selected rows as text), Clear view (hides entries up to now; never
  deletes files), Open log folder.
- While the journal page is hidden, the Journal module button shows a badge when new ERROR or
  CRITICAL entries arrived; it clears when the page is shown.
- Performance: append-only updates insert rows (`SnapshotTableModel`), the UI stays fluid while 50
  entries per second are logged.

## Settings (Menu C)

One form, sections in this order:

| Section | Fields | Storage |
|---|---|---|
| General | language (combo); journal detail level (`LogLevelEnum`); notifications when the window is inactive (checkbox) | `UserSettings` (data file) |
| Hourly chime | enabled, sound, volume + preview, start hour, end hour | `HourlyChime` (data file) |
| Data file | current path (read-only), Open folder, Use another file..., Move file... | `ui-state.ini` + file operations |
| Interface | Reset layout (window geometry, splitters, column widths, sorts, filters) | `ui-state.ini` |
| About | version, paths of the app ini, UI state ini, log folder, backups folder (read-only, each with Open folder; a missing app folder is created before opening) | — |

- `SettingsForm` (`FormState`) covers the fields stored in the data file: inline errors, `is_dirty`, Save and
  Revert enabled only when dirty; leaving the page with a dirty form asks Save / Discard / Cancel.
- Data file actions are immediate commands (not part of the form), each with confirmation:
  - Use another file: flush the current save, pick a file (open existing or create new), run the
    phase 1 load and recovery flow on it, switch the session, remember the path, `request_all()`.
  - Move file: write the current data to the new path with the atomic writer, verify it loads,
    switch to it, remember the path; the old file is kept and its path is shown in the message.
- Reset layout: clears the layout keys of `ui-state.ini` (not the data file path) and applies
  defaults immediately.
- Changing the journal detail level calls `LoggingControlPort.set_level(...)` at once.

## Deliverables

- Domain: `domain/settings/log_level_enum.py` (`UNKNOWN=-1, UNSET=0, DEBUG=1, INFO=2, WARNING=3,
  ERROR=4, CRITICAL=5`); `UserSettings` gains `log_level`, `notify_when_inactive` (defaults from the
  ini); rules updated.
- Application: `ports/logging_control_port.py`, `ports/link_opener_port.py` with
  `open_folder(path) -> ValidationResult` (phase 6 extends it), `storage/data_file_commands.py`
  (`switch_to`, `move_to`), `settings/settings_commands.py` (`save_settings(draft)`),
  `journal/journal_queries.py`.
- Infrastructure: `logging/logging_control.py`, `qt/qt_link_opener.py` (`QDesktopServices.openUrl`
  with `QUrl.fromLocalFile`), schema and mapper updates.
- Presentation: `journal/journal_presenter.py`, `journal_snapshot.py`, `journal_filter.py` (pure
  filtering and search, accent folding with `unicodedata`); `settings/settings_presenter.py`,
  `settings_form.py`, `settings_snapshot.py`; `presentation/common/text_search.py` (reused by the
  TODO search in phase 6).
- UI: `ui/windows/journal_page.py`, `ui/windows/settings_page.py`, `ui/panels/journal_toolbar_panel.py`,
  `ui/panels/journal_table_panel.py`, `ui/panels/journal_detail_panel.py`,
  `ui/panels/settings_form_panel.py` (sections as group boxes), `ui/widgets/level_toggle_widget.py`,
  `ui/widgets/search_box_widget.py`, `ui/widgets/path_row_widget.py`, `ui/widgets/badge_button.py`
  (module bar badge).

New `ActionIdEnum` values: `JOURNAL_TOGGLE_LEVEL`, `JOURNAL_SEARCH`, `JOURNAL_TOGGLE_FOLLOW`,
`JOURNAL_TOGGLE_PAUSE`, `JOURNAL_COPY`, `JOURNAL_CLEAR_VIEW`, `JOURNAL_OPEN_LOG_FOLDER`,
`SETTINGS_SAVE`, `SETTINGS_REVERT`, `SETTINGS_SWITCH_DATA_FILE`, `SETTINGS_MOVE_DATA_FILE`,
`SETTINGS_OPEN_FOLDER`, `SETTINGS_RESET_LAYOUT`, `SETTINGS_CHIME_PREVIEW`.
New `RenderSectionEnum` values: `JOURNAL`, `SETTINGS`.

## File format (fields added to `settings`)

```toml
[settings]
id = '...'
created_at = '...'
updated_at = '...'
language = 2
log_level = 2
notify_when_inactive = true
```

## `concentrator.ini` (new keys)

```ini
[journal]
search_debounce_ms = 150
copy_max_rows = 2000

[settings]
default_log_level = INFO
default_notify_when_inactive = true
```

## Error codes

| Code | Name |
|---|---|
| 2018 | `STORAGE_TARGET_IS_CURRENT_FILE` |
| 2019 | `STORAGE_MOVE_FAILED` |
| 7003 | `LINK_OPEN_FAILED` (WARNING, logged only: Windows refused to open the target) |

## Tests

- `JournalFilter`: level toggles, accent-insensitive search (`"etat"` finds `"État"`), clear view,
  pause counter, follow flag.
- `JournalPresenter` with a fake feed: polls only while visible; badge on new ERROR while hidden;
  render skipped when nothing changed.
- `SnapshotTableModel`: append path inserts rows, other changes reset (pytest-qt, `ui` marker).
- `SettingsForm`: dirty, revert, inline errors (chime hours), save calls both writers once.
- Data file commands with fakes: switch to valid file, to damaged file (recovery path), to the
  current file (`STORAGE_TARGET_IS_CURRENT_FILE`); move success and failure (old file untouched).
- Reset layout removes only layout keys.
- Logging control: level change visible in the root logger.

## Acceptance criteria

- [ ] The journal shows startup entries and new ones live; level toggles and search filter
      instantly; follow and pause work; copy puts readable text in the clipboard.
- [ ] An ERROR logged while on the Focus page shows a badge on the Journal button.
- [ ] Settings: changing the language in the form and saving switches the UI live (same result as
      the status bar button, which keeps working).
- [ ] Save/Revert are disabled until a change; leaving the page with changes asks what to do.
- [ ] "Use another file" and "Move file" work and are remembered after restart.
- [ ] "Reset layout" restores default window size, splitter ratio and columns at once.

## Manual test script

1. Open the journal, toggle levels, search `timer`, pause, start a timer, unpause.
2. Trigger an error (choose a custom sound, delete the file, let the timer ring), return to the Focus
   page before it rings, check the badge.
3. Settings: change language, hours of the chime, Revert, change again, Save; switch pages with a
   pending change.
4. Move the data file to `D:/Concentrator/`, restart, check the path; switch back with "Use another
   file".

## Review gate questions

1. Journal shows only the current session (plus "Open log folder"): enough, or load the last log
   file at startup?
2. Should the ini constants be listed read-only in "About"?
