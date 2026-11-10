# Phase 4 review report

First issue (2026-11-10). Branch `phase-4-journal-settings`, 10 commits on top of `main`
(`2a17aaa`, which holds `phase-3-accepted`); the branch is not pushed. Owner decisions of the plan
review are in ADR-040; the items "decided during the build" there are to be approved.

## Summary

- **Journal (Menu B):** the log entries of the session, live.
  - Columns time (`HH:MM:SS.mmm`, local), level, source, thread and the first line of the message;
    the selected entry shows in full (traceback included) in a pane below, in a splitter.
  - Level toggles with counts, a search over message and source (case and accents ignored, applied
    150 ms after the last key press, the field is never disabled), Follow, Pause with the number of
    hidden new entries, Copy (and Ctrl+C) in the log file format, Clear view and Open log folder.
  - The log buffer is read on the heartbeat only while the page is shown; a table that only grows
    inserts rows, and once the buffer is full the oldest rows are removed, so 50 entries per tick
    give one render without a model reset.
  - While another page is shown, new ERROR and CRITICAL records put a count on the Journal button.
- **Settings (Menu C):** five sections in a scroll area, Save and Revert always visible below it.
  - General: language, journal detail level, "Flash the taskbar button when the timer rings while
    Concentrator is in the background". Hourly chime: switch, sound, volume with Preview, hours (the
    fields of the chime dialog, shared).
  - Save writes the user settings and the chime once each, only the parts that changed; a new
    language switches the UI at once, a new detail level applies to the root logger at once.
  - Leaving the page, switching the data file or closing with unsaved changes asks Save / Discard /
    Cancel (Save and quit / Quit without saving / Cancel when closing).
  - Data file: **Use another file...** (open or create; a file with a problem shows the recovery
    dialog over the window, where Cancel keeps the current file) and **Move file...** (atomic write,
    read back and compared, then used and remembered; the old file is kept).
  - Interface: **Reset layout** removes `layout/*` only and applies the default geometry, splitters,
    journal columns and level toggles at once. About: version and the four application paths, each
    with Open folder (a missing folder is created).
- **Data file:** `[settings]` gains `log_level` and `notify_when_inactive`; a phase 1-3 file takes the
  `[settings]` defaults of the ini and gets the keys at the next save.
- **Fix:** a late save result of the previous data file is now ignored after the coordinator is
  attached to another file (found while designing "Move file").

## Spec coverage

| Requirement | Status | Notes |
|---|---|---|
| Journal source, polling only while visible, render only on change | done | `JournalQueries`; badge reads `LogFeedPort.error_count()` while hidden |
| Columns, detail pane, selectable text | done | detail in a fixed-width font |
| Level toggles with counts, accent-insensitive search, filters persisted | deviated (owner) | level toggles and Follow are layout keys; search, Pause and Clear view are per session |
| Follow, Pause with counter, Copy, Clear view, Open log folder | done | Copy capped at `journal.copy_max_rows`, Ctrl+C too |
| Badge on the Journal button while hidden | done | counts errors since the journal was last shown, or since the start; `99+` |
| Append inserts rows, fluid at 50 entries/s | deviated (build) | plus the "head removed" path once the buffer is full; measured in tests, to confirm by hand |
| Settings sections and fields in the spec order | done | group boxes in a scroll area |
| `SettingsForm`: inline errors, `is_dirty`, Save and Revert only when dirty, leave guard | done | the form also follows stored values changed elsewhere (`FormState.rebase`) |
| Use another file / Move file with confirmation | done | Use another file asks Open / Create / Cancel; Move confirms the target |
| Reset layout clears the layout keys only and applies the defaults at once | done | new ini keys for the journal splitter and columns |
| Detail level applied at once (`LoggingControlPort`) | done | on Save, and when a data file opens |
| `LogLevelEnum`, `UserSettings` fields with ini defaults, rules | done | plus `GeneralSettings` |
| Application deliverables | deviated (build) | `save_settings(draft)` is two commands called by the presenter (AGENTS.md 6.3) |
| Infrastructure deliverables | done | plus `UserDataFilePort.is_same_file`, `LogFeedPort.error_count`, `ViewPreferencesPort.remove_group` |
| Presentation deliverables | done | `settings_presenter` delegates the file sections to `SettingsFilesPresenter` and `DataFileFlow` |
| UI deliverables | done | `settings_form_panel` is split into form, files and footer panels |
| New `ActionIdEnum` (43-56) and `RenderSectionEnum` (12-13) values | deviated (build) | plus `SETTINGS_CHIME_SOUND_CHOOSE_FILE` (57) and `STARTUP_CANCEL` (58) |
| File format | done | golden test: the writer produces the spec example byte for byte |
| `concentrator.ini` keys | deviated (build) | plus `journal.default_table_ratio_percent` and `journal.default_column_widths_px` |
| Error codes 2018, 2019, 7003 | done | each produced by a test, messages in both catalogs |
| Tests listed in the spec | done | see below |

## Deviations and decisions

Owner decisions (plan review): ADR-040 items 1 to 7. Decided during the build, to approve: ADR-040
items 1 to 14. The main ones:

1. **Two writes for one Save** (`SettingsCommands.save_general`, `ChimeCommands.save`), called by the
   presenter, because a feature never calls the writer of another feature.
2. **`notify_when_inactive`** flashes the taskbar button (no notification, ADR-038).
3. **In-session recovery:** the startup dialogs move over the main window once it exists, and the same
   flow runs them for a file chosen on the settings page; Quit becomes Cancel.
4. **`SnapshotTableModel`** also handles rows dropped at the head of a full buffer.
5. **`ClipboardPort`** is a presentation port implemented in `ui.support` (the spec placed no port;
   the plan named an application port), since only presenters use it.
6. **Shared chime fields:** `ChimeFieldsPanel` is a panel composed by two panels (the chime dialog and
   the settings form).
7. **`SaveCoordinator` generations** (fix, with a failing test first).

Process note: the commit of step 9 was first created while one test failed (a render scheduled by a
new test ran after its window was deleted, in a later test). I fixed the test and amended that local
commit, so every commit of the branch passes the gates; the branch was never pushed.

## Gates

`uv run python scripts/check.py` on the last commit:

| Gate | Result |
|---|---|
| `ruff format` | passed |
| `ruff check` | passed |
| `basedpyright` (strict) | 0 errors, 0 warnings, 0 notes |
| `furryp check concentrator` | all checks passed (`domain.todo` still matches no module: phase 5) |
| `pytest --cov` | 2062 passed, 0 failed, 0 skipped |
| `coverage_gate.py` | passed |

I also ran `uv run python scripts/build.py`: the build succeeded, `concentrator.ini` (with the new
`[journal]` and `[settings]` sections) was copied next to the exe, and the frozen self-check passed.

## Coverage per layer

Branch coverage (statements + branches):

| Layer | Coverage | Threshold |
|---|---|---|
| domain | 100.00 % | 90 % |
| application | 99.40 % | 85 % |
| presentation | 99.40 % | 80 % |
| infrastructure | 98.37 % | — |
| ui | 99.10 % | — |
| bootstrap | 90.17 % | — |
| overall | 98.59 % | 75 % |

Not covered (new code):
- the recovery fallback of `bootstrap/settings.py` used only when the shell is built without the
  startup flow (tests);
- `DataFileFlow`: the branch where no settings can be read after a switch;
- a few test-only properties of the panels.

## Manual test script

The GUI cannot be inspected from here. Please run these steps on Windows 11 at 100 % and 150 %
scaling. Steps 1 to 4 are the spec script.

1. **Journal.** Open **Journal**: the startup entries are there, the newest at the bottom.
   - Toggle **Debug** and **Info** off and on: the rows and the counts follow at once.
   - Type `timer` in the search: only matching rows remain (try `etat` against an entry with
     "État").
   - Click **Pause**, start a timer on the Focus page, come back: the list did not move and "N new
     entries hidden" shows; click **Pause** again: the new entries appear.
   - Select two rows, click **Copy** (and try Ctrl+C), paste in Notepad: two log-file lines.
   - **Clear view** empties the list; new entries appear after it. **Open log folder** opens Explorer.
   - Set **Journal detail level** to Debug and Save: the journal shows DEBUG entries and stays still
     when nothing happens (no endless stream).
2. **Badge.** Choose a custom sound for the timer, delete the MP3, set a 10 s countdown, start it and
   go back to the Focus page before it rings: when it rings, the **Journal** button shows a number.
   Open the journal: the number goes away and the warning about the missing sound is there.
3. **Settings form.** Change the language and the chime hours: **Unsaved changes**, Save and Revert
   enabled. **Revert**: the stored values come back. Change again and **Save**: the UI switches
   language at once; the special options show the new hours.
   - Change a field, click **Focus**: the question Save / Discard / Cancel; Cancel stays, Discard
     leaves without saving.
   - Change a field and close the window: Save and quit / Quit without saving / Cancel.
   - Switch the language with the status bar button while a field is changed on the page: the
     language field follows, your change stays.
4. **Move and switch.** **Move file...** to `D:/Concentrator/concentrator.toml`: the message names both
   files; the status bar tooltip shows the new path. Restart: the new path is used.
   - **Use another file... > Open a file...**, choose the old file: it opens; restart: it stays.
   - Open a damaged copy (break a line by hand): the recovery dialog opens over the window, darkened
     behind; **Cancel** keeps the current file.
   - Choose the file in use: "This is already the current data file."
5. **Reset layout.** Resize the window, drag both splitters, widen a journal column, hide a level, then
   **Reset layout**: everything returns to the defaults at once; restart: the defaults stay.
6. **Taskbar alert.** Uncheck the taskbar setting and Save, let a timer ring while another application
   is in front: sound only, no flashing. Check it again: the button flashes.
7. **About.** Each **Open folder** opens the right folder; delete the backups folder first: it is
   created.
8. **Fluidity.** Set the detail level to Debug, keep the journal open and work in the app for a while
   (or drag a splitter fast): scrolling and typing in the search stay smooth.
9. **Language.** Switch FRA/ENG on the journal and the settings pages: every text follows, the journal
   times and level names included.
10. **Built app.** Build with `uv run python scripts/build.py` and repeat steps 1, 3 and 4 with
    `dist\Concentrator\Concentrator.exe`.

## Changes after the review (2026-11-10)

The owner tested the build and reported two problems; both are fixed, each starting with a failing
test (ADR-040 amendment).

1. **No badge when the timer rang with a deleted MP3** (manual step 2). The fallback to the default
   sound was logged at WARNING, and the badge counts ERROR and CRITICAL only. A sound that cannot be
   found is now logged at ERROR, for the alarm and the chime.
2. **A new duration saved while a countdown ran left the old countdown going** (the phase 2 rule "a new
   duration applies at the next start or reset"). Saving a new duration now resets the countdown and
   starts it at once with the new duration, from running or paused; the right button shows Pause
   again. A change of sound or volume alone keeps the countdown. The note of the dialog says so.

Manual checks to redo: step 2 above, and in the timer dialog, while a countdown runs: change the
duration and Save (the countdown restarts with it), then change only the volume and Save (the
countdown goes on).

## Open questions

1. **Error rows** are bold in the highlight color of the Windows palette (blue by default), since
   colors are never hard-coded. Do you want red? Default: keep the palette color; a red would need an
   ini key.
2. **Badge at startup.** Errors logged before you open the journal for the first time count in the
   badge (for example a missing sound at startup). Default: keep it.
3. **Failed move.** When the moved file does not read back the same data, it is left at the target
   (never deleted silently) and the current file stays in use. Default: keep it.
4. **Chime settings in two places** (the special options dialog and the Settings page), as the spec
   asks. Default: keep both.
