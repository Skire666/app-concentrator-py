# Phase 1 code review: findings and fixes

Branch `fix/phase-1-review`, started from `main` (`51c8d8d`, tagged `phase-1-accepted`); not pushed.
The review covered `phase-0-accepted..phase-1-accepted` (195 files). It kept 14 findings and dropped
one: errors raised during the startup dialogs are only logged, as ADR-024 decides. Every fix started
with a failing test. The decisions are recorded in ADR-037.

## Findings and fixes

| # | Finding | Fix | Commit |
|---|---|---|---|
| 1 | The Windows session end flush stopped saving for good; if the logoff was cancelled, every later change was lost silently | the session end flush keeps saving on; `aboutToQuit` stops it | `37166ab` |
| 2 | "Keep Concentrator's version" at close left the conflict flag set; a failed overwrite was never retried and new changes were ignored | the overwrite clears the conflict and holds until a save succeeds | `68250d0` |
| 3 | "Keep Concentrator's version" was forgotten after a transient failure, so the same question came back | same fix as 2 | `68250d0` |
| 4 | A failed save with a change waiting was retried at once, skipping `storage.failed_save_retry_ms` | the retry delay is kept | `68250d0` |
| 5 | Closing with a file changed outside opened two stacked questions (or one after the window closed) | statuses of the close flush are marked `interactive_shutdown` and left to the shutdown question | `6390589` |
| 6 | "Start with an empty file" overwrote the `.tmp` candidate at once and the `.bak` at the next save | creating a data file renames a leftover `.tmp`/`.bak` to `.discarded-YYYYMMDD-HHMMSS` first; nothing is written if that fails | `8d7fdab` |
| 7 | Restore could rename a main file that became unreadable or newer-version after the probe | restore refuses such a file and changes nothing | `8d7fdab` |
| 8 | A `.tmp` saved in the same second as the main file was never offered | it is offered when its data differs | `65d17d7` |
| 9 | A TOML key with an apostrophe was written `'''...'''`, which TOML forbids (latent: no such key in phase 1) | keys are bare, `'...'` or `"..."` | `0d4d4b9` |
| 10 | Every startup parsed the data twice (main file and `.bak`) | the `.bak` is read only when the main file is not valid (`FileStateEnum.NOT_INSPECTED`) | `fb0aba3` |
| 11 | The instance lock was released while a timed-out write could still run | `WriterThread.shutdown` waits for its jobs before the lock is released | `d5f6f2a` |
| 12 | A second launch during a startup dialog brought nothing to the front | the open dialog is brought to the front | `d5f6f2a` |
| 13 | The save picker asked "Replace?", then creation refused the existing file | no replace question; the creation message explains the refusal | `ec348ed` |
| 14 | Hard-coded sizes in the first-run and recovery dialogs | `ui.startup_dialog_min_width_px` (560) and `ui.dialog_spacing_px` (10) in `concentrator.ini` | `ec348ed` |

User-visible changes: `*.bak.discarded-*` files may appear next to the data file, and the
first-run dialog is now at least 560 px wide (it was 520), like the recovery dialog.

## Gates

`uv run python scripts/check.py` on the last commit: `ruff format`, `ruff check`, `basedpyright`
(0 errors) and `furryp` (contracts applied) passed; 908 tests passed (883 before the review), and the
coverage gate passed. `furryp` still warns that `domain.timer` and `domain.todo` match no module yet;
those packages arrive in phases 2 and 5.

| Layer | Coverage | Threshold |
|---|---|---|
| domain | 100.00 % | 90 % |
| application | 98.89 % | 85 % |
| presentation | 99.42 % | 80 % |
| infrastructure | 97.78 % | — |
| ui | 98.40 % | — |
| bootstrap | 85.85 % | — |
| overall | 97.57 % | 75 % |

## Manual checks

The GUI cannot be inspected from here; please run these on Windows 11.

1. **Cancelled logoff.** Leave a Notepad window with unsaved text open, change the language in
   Concentrator, then sign out. When Windows lists the apps that prevent signing out, choose Cancel.
   Change the language again: the status bar shows `Saved at ...` with the new time.
2. **Close with an outside edit.** Edit the data file in Notepad and save it, toggle the language in
   Concentrator, close the window: only one question appears ("Quit without saving" / "Keep
   Concentrator's version").
3. **Start empty keeps the versions.** Close the app, damage the data file (`language = 2,`), start,
   choose "Start with an empty file": next to the file you find `.corrupt-...` and
   `.bak.discarded-...`, and the app opens.
4. **Create on an existing file.** Delete `ui-state.ini`, start, choose "Create elsewhere..." and pick
   an existing file: Windows does not ask to replace it, and Concentrator says the file already
   exists.
5. **Second launch during the first-run dialog.** Delete `ui-state.ini`, start, put another window
   over the first-run dialog, start Concentrator again: the dialog comes to the front (or its taskbar
   button flashes).

## Left out

Phase 0 code keeps three hard-coded margins (`module_bar_panel.py` 6 px, `status_bar_panel.py` 8 and
2 px). They were outside the phase 1 review; moving them to `concentrator.ini` takes three more keys.
