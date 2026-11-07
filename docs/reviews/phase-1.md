# Phase 1 review report

Second issue (2026-11-07), after the first review. Branch `phase-1-persistence`, 20 commits on top of
`main` (`7c3cc52`, pushed, tagged `phase-0-accepted`); the branch is not pushed.

## Summary

The user data file has its complete lifecycle:
- **Choosing the file:** a first-run dialog picks the file, and the path is remembered.
- **Reading:** the TOML file goes through the strict read pipeline (`tomllib`, pydantic DTOs, then
  domain rules) and is kept in an in-memory store.
- **Saving:** a debounced coordinator (with a maximum delay) saves on the single writer thread through
  an atomic, verified replace. Saving keeps a `.bak`, makes daily backups and refuses to overwrite a
  file changed outside Concentrator.
- **Recovering:** a recovery dialog handles interrupted saves, damaged, missing, locked and newer files
  (ADR-027 matrix).
- **Status and language:** the status bar shows the save state, and the language button persists in
  `UserSettings`. Pending changes are flushed on close, quit and Windows session end.
- **Second launch:** a missing single-instance lock is visible to the user (dialog and status bar).
- **Dialogs:** once the main window exists, every dialog dims it by 10 %, opens centered on it and
  cannot be moved outside it.

Changes since the first review (owner decisions of 2026-11-07):
- **TOML replaces JSON5 (ADR-035).** Literal strings `'...'`, `'''...'''` for values with an
  apostrophe, `"..."` only for `'''` or control characters. `tomllib` reads; our emitter writes;
  `json5` is gone. Reading 1,000 tasks takes 0.39 s instead of about 20 s.
- **Dialog rule (ADR-036):** `ModalHost` in `ui/support/`.
- **Benchmark volume:** 1,000 tasks with 20 history events each, also for the phase 5 and phase 8
  checks.

## Spec coverage

| Requirement | Status | Notes |
|---|---|---|
| Domain: `UserSettings`, `UserSettingsRules`, `MultilineText` | done | plus `EntityCollection`, `EntityRules`, `BusinessCopyable`, `ValidationResult.prefixed` (ADR-034) |
| Application: `UserData`, ports, `StartupCommands`, `SaveCoordinator`, `SaveStateEnum`, settings commands/queries | done | `load`/`create`/`restore` return `StoredUserData`; blocking `save`; `discard_temporary`; `ExternalChangeCommands`; language hint (ADR-027, ADR-034) |
| Infrastructure: TOML codec, schemas, pydantic mapper, mappers, TOML file, atomic writer, daily backup, recovery inspector, writer thread, store, generic store, settings store | done | plus fingerprint registry (ADR-033), file reader, side-file names; generic store typed `[E]` (ADR-034) |
| Presentation: first-run and recovery presenters and snapshots, storage messages, status bar texts | done | plus startup flow, external change, shutdown, status bar and instance protection presenters, `LanguageSwitcher`, `DateTimeFormatter` |
| UI: first-run and recovery dialogs and panels; modal host | done | plus `StartupDialogs` (port), `ButtonColumnWidget`, status bar tooltip and warning label, `QtDialogService.warn`; `ModalHost`, `DimmingOverlay`, `DialogConfinement`, `PositionClampFilter` (ADR-036) |
| Bootstrap: resolve, dialogs, load, language; flush on quit with "Quit without saving" / "Retry" | deviated (approved) | inserted after the catalogs; flush in `closeEvent`, plus `commitDataRequest` and `aboutToQuit` without dialog (ADR-027, ADR-032); shutdown dialogs parented to the window |
| File format version 1 (TOML) | done | golden test: the writer produces the spec example byte for byte |
| `[storage]` ini keys, `ui.dialog_overlay_opacity_percent`, `paths.default_data_file` in `.toml` | done | plus `save_max_delay_ms` and `blocking_write_timeout_ms` |
| Error codes 2001-2017, 2021 | done | 2020 `STORAGE_DUPLICATE_KEY` retired: TOML duplicates are syntax errors (2004) |
| Tests listed in the spec | done | the 27-case recovery matrix, every quoting case through `tomllib`, atomic writer, coordinator, nine store operations, messages in both languages, modal host, UI smoke |
| Benchmark | done | numbers below and in ADR-035 |

## Deviations and decisions

**Approved at the first review (2026-11-07):**
- **ADR-035:** quoting fallback (`'''...'''`, `"..."`), the `furryp.json` contracts moved from `json5`
  to `tomllib`, no migration.
- **ADR-036:** dialogs before the main window open centered on the screen; the Windows file picker is
  dimmed but placed by Windows.
- Defaults of the first report: default location `%APPDATA%\Concentrator\`, daily backups (7 days),
  the Escape behaviours, the ADR-034 build decisions (`StoredUserData`, generic store `[E]`,
  `StatusBarPresenter`, catalog key test, first-run buttons, no confirmation for "Start with an empty
  file").

**Decided during the rework** (please approve; recorded in ADR-035 and ADR-036):

1. **`WM_WINDOWPOSCHANGING`, not `WM_MOVING`.** Qt does not hand `WM_MOVING` to native event filters
   (checked on the real platform). `WM_WINDOWPOSCHANGING` reaches them before every move (drag,
   keyboard, another monitor), so one clamp covers all cases without flicker.
2. **Centering is Qt's.** Qt centers a parented dialog on its parent when it shows. The host never
   moves a dialog before it is visible: a test showed that this cancels Qt's centering.
3. **Native rectangles.** On Windows the clamp uses `GetWindowRect` (physical pixels), consistent
   with mixed display scaling. Those rectangles include the invisible resize borders Windows adds
   around windows, so a dragged dialog may stop a few pixels before the visible edge.
4. **Native TOML dates typed by hand** (`due_date = 2026-11-10`, no quotes) are accepted and written
   back quoted.
5. **Overlay color** from the palette's shadow role (black), so no color is hard-coded.
6. **`ShutdownPresenter.attach`.** A question without attached dialogs raises `RuntimeError`, a
   wiring error that bootstrap cannot produce.
7. **Architecture test:** `tomllib` may only be imported by `toml_codec.py`.

**Found during the rework, fixed by the owner:** the `furryp` layer contracts had never been
applied. `furryp.json` set `"source-roots": ["concentrator"]`, so modules were named `domain.x`
instead of `concentrator.domain.x` and no contract matched. The owner set `"source-roots": ["."]`
(`furryp` 1.0.3). Checked with probe files: imports of `concentrator.application`, `pydantic` and
`tomllib` in `domain/`, `tomllib` in `infrastructure/config/`, `PySide6` in `presentation/` and
`concentrator.domain` in `ui/` are all rejected, and the current code passes every contract.
`furryp` warns that `domain.timer` and `domain.todo` match no module yet; they arrive in phases 2
and 5.

**Found by the manual test (fixed):** a missing data file with a valid `.bak` next to it (manual
step 8) opened the recovery dialog without "Retry", although the file may only have been renamed or
moved. Retry is now offered in that case too (ADR-027 amendment), with a failing test written first.
The locked file of step 9 does show Retry (checked with the real startup flow); step 9 now starts by
undoing step 8.

No suppression comment was added: the only one in the code base is still the phase 0
`qt_main_thread_dispatcher.py` one.

## Gates

`uv run python scripts/check.py` on the final commit:

| Gate | Result |
|---|---|
| `ruff format` | passed |
| `ruff check` | passed |
| `basedpyright` (strict) | 0 errors, 0 warnings, 0 notes |
| `furryp check concentrator` | all checks passed, contracts applied (see the finding above) |
| `pytest --cov` | 883 passed, 0 failed, 0 skipped |
| `coverage_gate.py` | passed |

Also run here (not part of the gates):

- **Build:** `uv run python scripts/build.py` took 50 s and produced a 124 MB bundle. The frozen
  self-check passed, including the in-memory TOML round trip; `json5` is no longer in the bundle.
- **Native confinement:** a child process on the real Windows platform moves a hidden dialog to
  (-5000, 5000); the filter keeps it inside the main window, and it moves freely once untracked.

## Benchmark

`uv run python scripts/bench_storage.py`: 1,000 tasks, 20 history events each, 4 lines of text (one
task in three with apostrophes, a path and a URL), 1.74 MB, best of 3.

| Stage | Time | Throughput |
|---|---|---|
| `TomlCodec.decode` (`tomllib`) | 339 ms | 5.14 MB/s |
| `TomlCodec.encode` | 127 ms | 13.7 MB/s |
| read pipeline (TOML + pydantic) | 388 ms | 4.49 MB/s |
| write pipeline (pydantic + TOML) | 152 ms | 11.4 MB/s |

The same data as JSON5 (2.68 MB) took 20.7 s to read with `json5.loads`. The phase 8 startup target
(2 s for 1,000 tasks) is within reach.

## Coverage per layer

Branch coverage (statements + branches):

| Layer | Coverage | Threshold |
|---|---|---|
| domain | 100.00 % | 90 % |
| application | 98.85 % | 85 % |
| presentation | 99.41 % | 80 % |
| infrastructure | 97.61 % | — |
| ui | 98.39 % | — |
| bootstrap | 86.76 % | — |
| overall | 97.58 % | 75 % |

Not covered, by design:
- The `app.exec()` path and the `commitDataRequest`/`aboutToQuit` handlers of `bootstrap/app.py`.
- The native `GetWindowRect`/`SetWindowPos` calls of `NativeWindowRects`: they run in the child
  process test above, whose coverage is not collected.
- Two defensive guards of `SaveCoordinator._save_now`, which cannot be reached while timers are
  cancelled on close and on conflict.
- The `unlink` and `iterdir` failure branches of the atomic writer and the daily backup.

## Manual test script

The GUI cannot be inspected from here; please run these on Windows 11 at 100 % and 150 % scaling.
Paths assume the default location. If an earlier run left a `.json5` path in `ui-state.ini`, step 1
removes it.

1. **First run.** Delete `%APPDATA%\Concentrator\ui-state.ini` and start: the first-run dialog appears,
   centered on the screen. Choose "Create at default location". The main window opens; the status bar
   shows `Saved at HH:MM:SS`, and hovering over it shows the file path.
2. **Saving.** Toggle FRA/ENG and open `%APPDATA%\Concentrator\concentrator.toml` in Notepad: the
   `language` value and `saved_at` change within about 1 s, and every text is between single quotes.
   Click the button 20 times quickly: the file is written at most 2 or 3 times (watch `saved_at`), and
   the last state is saved.
3. **Damaged file.** Close the app, set `language = 'x'` in the file, start. The recovery dialog says
   `Language: A value has the wrong type.` (French: `Langue : Une valeur n'a pas le bon type.`) and
   lists the backup. Choose "Restore": the app opens, and the damaged file is next to it as
   `concentrator.toml.corrupt-YYYYMMDD-HHMMSS`. Repeat with a syntax error (`language = 2,`): the
   message gives the line and column.
4. **Locked file.** Lock the file from PowerShell:
   `$f=[IO.File]::Open("$env:APPDATA\Concentrator\concentrator.toml",'Open','Read','None')`.
   - Toggle the language: the status bar shows `Save failed: ... Retrying.`
   - Run `$f.Close()`: within about 10 s the status bar shows `Saved at ...`.
5. **Kill during saves.** Toggle repeatedly and kill `Concentrator.exe` from Task Manager, then
   restart. The file opens. If the kill hit a save, the recovery dialog offers the interrupted version;
   "Keep the current file" renames it `.tmp.discarded-...`, and the question does not come back.
6. **Hand edit while running.** With the app running, change `language` in Notepad and save. Toggle
   the language in the app: the "Data file changed" question appears.
   - Choose "Reload the file": the interface follows your edit.
   - Repeat and choose "Keep Concentrator's version": the file is overwritten, and your edit is in
     `concentrator.toml.bak`.
7. **Dialog over the window.** With the question of step 6 open:
   - the whole window behind it (module bar, pages, status bar) is slightly darker (10 %); the
     Windows title bar is not;
   - the question is centered on the window;
   - dragging it by its title bar stops at each of the four edges of the window (a few pixels of
     margin are possible, see decision 3); Alt+Space, Move, then the arrow keys stop at the edges too;
   - repeat with the window maximized, with a small window, and with the window on a second screen
     with another scaling;
   - after closing it, the window is no longer darker.
8. **Missing file.** Close the app and rename the data file.
   - Start: the recovery dialog says the file is missing and offers Restore (the `.bak`), Retry and
     the other choices. Rename the file back, choose Retry: the app opens.
   - Close the app, rename both the data file and its `.bak`, start: the first-run dialog shows the
     "not found" notice and Retry (as when a USB or network drive is not connected). Rename both
     back, choose Retry: the app opens.
9. **Locked at startup.** Make sure the app opens normally (step 8 undone), close it, lock the file
   as in step 4, then start: the recovery dialog says the file cannot be read and offers Retry.
   Release the lock with `$f.Close()`, choose Retry: the app opens.
10. **Close with a failing save.** Lock the file, toggle the language, close the window: "Changes not
    saved" appears over the darkened window, centered on it (no longer centered on the screen).
    - "Retry" keeps the window open.
    - Release the lock: the status bar returns to `Saved at ...`, and closing now works without a
      question.
11. **Unguarded mode.** Close the app, then create a folder where the lock file goes:
    `New-Item -ItemType Directory "$env:LOCALAPPDATA\Concentrator\concentrator.lock"`. Start:
    - the warning "Single-instance check unavailable" appears before the window;
    - the status bar shows "Second launch not blocked".

    Remove the folder afterwards. If no warning appears, the lock still worked: please tell me, and I
    will provide another way to trigger the unguarded mode.
12. **Language at startup.** Switch to FRA, close, delete only the data file, start: the first-run
    dialog is in French (language hint).
13. **Built app.** Build with `uv run python scripts/build.py` and repeat steps 1, 2 and 7 with
    `dist\Concentrator\Concentrator.exe`.

## Open questions

1. **Edge margin** (decision 3): if the few pixels of invisible border matter, I can clamp on the
   visible bounds (`DwmGetWindowAttribute`). Default: keep it as is.
