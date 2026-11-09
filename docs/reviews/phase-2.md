# Phase 2 review report

Second issue (2026-11-09), after the first review. Branch `phase-2-timer-core`, 11 commits on top of
`main` (`911d243`, tagged `phase-1-accepted`), including the owner's asset commit; the branch is not
pushed.

## Summary

The countdown timer runs at the top of zone 2 of the Focus page:
- **Display:** large `HH:MM:SS` digits in a monospaced font with tabular figures (64 px), a caption
  ("Ends at 17:52", "Snoozed, rings at 17:57", "Paused", "Time is up"), and three buttons that follow
  the state machine of the spec.
- **State machine:** `TimerSession` works on integer monotonic milliseconds. Every (state, command)
  pair is tested, and a one-hour run with 100 ms ticks rings exactly on time.
- **Alarm:** MP3 playback through QtMultimedia, with the chosen volume and play count (or "Repeat until
  stopped"). The fallback chain is the chosen sound, then the default sound, then the system beep.
  Snooze, automatic stop and automatic restart are in place.
- **Attention:** when no Concentrator window is active, the taskbar button flashes. While another page
  is shown, the Focus button is highlighted. Nothing appears in the notification area.
- **Edit dialog:** the dialog runs over the main window. It validates while you type, enables Save only
  when the draft changed and is valid, plays a preview and picks MP3 files. Cancel, Escape and its
  close button close it at once.
- **Quitting:** closing the window asks "Do you want to quit Concentrator?" first.
- **Data file:** the `[timer]` section is saved in the data file. Files from phase 1 are completed from
  `concentrator.ini` when they are opened.

## Changes since the first review

Owner decisions of 2026-11-09, made in one commit (ADR-038 amendment):
1. **Nothing in the notification area.**
   - Removed: the notification area icon and its Show/Quit menu (`TrayPanel`, `TrayPresenter`,
     `TRAY_SHOW`, `TRAY_QUIT`, `TRAY`), and the Windows notification. Qt can show a notification only
     through such an icon.
   - When the timer rings unseen, the sound plays and the taskbar button flashes.
   - Also removed: `AttentionPort.notify`, `NOTIFICATION_UNAVAILABLE` (7204, retired) and
     `timer.notification_duration_ms`.
   - The removed enum values (actions 27 and 28, section 7) are never reused.
2. **Cancel closes the edit dialog without asking.** Escape and the close button of the dialog behave
   the same way (question 1).
3. **One commit for the review changes.**
4. **Approved defaults:** the items decided during the build, the strict ini limits when a file is
   read, and `SOURCES.md` with the authors only.

The owner also added `alarm-notification-alert.mp3`. It got labels ("Notification alert" /
"Alerte de notification") and a line in `SOURCES.md`; the catalog test required the label.

One test gap was closed: the catalog test now also sees keys translated through a local alias
(`tr = self._translator.tr`).

## Spec coverage

| Requirement | Status | Notes |
|---|---|---|
| Domain: `Duration`, `Volume`, `SoundKindEnum`, `SoundRef`, `TimerStateEnum`, `TimerTransitionEnum`, `TimerConfig`, `TimerConfigRules`, `TimerLimits`, `TimerSession` | done | plus `TimerSettings`, the editable part of the configuration |
| Application ports: sound player, sound catalog, attention, timer config reader/writer | deviated (approved) | `play(SoundPlayback)` carries the fallback files; `AttentionPort` is `is_application_active` and `request_attention` |
| `TimerEngine`, `AlarmCoordinator`, `TimerCommands`, `TimerQueries` | done | plus `SoundPreview`, `TimerDefaults`, `UserDataDefaults` (completion of missing sections) |
| `QtSoundPlayer` (alarm and preview instances), `BuiltinSoundCatalog`, persistence of `[timer]` | done | `QtSoundPlayer` also follows the default audio output device |
| `QtAttention` with tray icon and notification | deviated (owner decision) | taskbar flash only; no icon, no notification |
| Presentation: timer presenter, snapshot, edit presenter, form, snapshot; `duration_formatter` | done | plus `TimerEditView`, `TimerLayout`, `MainWindowPresenters`, action groups |
| UI: `TimerPanel`, `TimerEditFormPanel`, the five widgets, `TimerEditDialog`, `FocusPage` zone 2 | done | "Choose an MP3 file..." is a button next to the list |
| Edit dialog: Cancel asks confirmation when dirty | deviated (owner decision) | closes without asking |
| New `ActionIdEnum` and `RenderSectionEnum` values | deviated (owner decision) | the tray ones are removed |
| File format `[timer]` | done | golden test: the writer produces the spec example byte for byte |
| `concentrator.ini` keys | deviated (approved) | plus `timer.min_auto_stop_seconds`; `timer.notification_duration_ms` removed |
| Error codes 4001-4007, 7101-7104 | done | every code is produced by at least one test; 7204 retired |
| Assets | deviated (approved) | six sounds provided by the owner, names kept, license confirmed |
| Tests listed in the spec | done | "double click on Start" is read as two clicks within the cooldown |
| Frozen build plays MP3 | partial | the FFmpeg plugin is bundled and the frozen self-check decodes MP3; the sound itself is a manual check |

## Deviations and decisions

All are recorded in ADR-038 (with its review amendment), ADR-004 (build verification) and ADR-011
(accepted). In short:
- **Sounds:** kept with their names; `SOURCES.md` names the authors; the license was confirmed by the
  owner.
- **Attention:** the taskbar flashes only when no Concentrator window is active; nothing appears in the
  notification area.
- **Quit question:** asked by the close button, except once Windows announced the end of the session.
- **Cooldown per button:** the three timer buttons share their cooldown (action groups); a click on an
  enabled button always counts.
- **Older files:** a file without `[timer]` is completed from the ini and saved; new ini key
  `timer.min_auto_stop_seconds`.
- **Sound fallback chain:** chosen file, then default sound, then beep.
- **Approved build items:** integer milliseconds, `TimerSettings`, strict ini limits on read, sound
  check of the edit form, `HH:MM:SS` limits in messages, catalog test on every layer, `TimerEditView`.
- **Edit dialog:** closes without confirmation.

No suppression comment was added: the only one in the code base is still the phase 0
`qt_main_thread_dispatcher.py` one.

## Gates

`uv run python scripts/check.py` on the review commit:

| Gate | Result |
|---|---|
| `ruff format` | passed |
| `ruff check` | passed |
| `basedpyright` (strict) | 0 errors, 0 warnings, 0 notes |
| `furryp check concentrator` | all checks passed (`domain.todo` still matches no module: phase 5) |
| `pytest --cov` | 1356 passed, 0 failed, 0 skipped |
| `coverage_gate.py` | passed |

Also run here: `uv run python scripts/build.py` succeeded and the frozen self-check passed; the bundle
contains `assets/sounds` and the FFmpeg multimedia plugin.

## Coverage per layer

Branch coverage (statements + branches):

| Layer | Coverage | Threshold |
|---|---|---|
| domain | 100.00 % | 90 % |
| application | 99.27 % | 85 % |
| presentation | 99.60 % | 80 % |
| infrastructure | 98.16 % | — |
| ui | 98.78 % | — |
| bootstrap | 87.81 % | — |
| overall | 98.18 % | 75 % |

Not covered: the event loop path of `bootstrap/app.py` (as in phase 1), `TimerServices.ringing`
(used only by the running window), and three test-only properties of the ui.

## Manual test script

The GUI cannot be inspected from here; please run these on Windows 11 at 100 % and 150 % scaling, with
sound on.

1. **Background page.** Edit timer: 00:00:10, Save. Start, switch to the Journal page, wait.
   - You should hear the sound and see the Focus button outlined.
   - Back on the Focus page, the digits blink.
2. **Window not active.** Repeat with the window minimized, then with another application in front.
   - The sound plays and the taskbar button flashes until you come back.
   - Nothing appears next to the clock, and no Windows notification.
3. **Snooze.** Let it ring, press Snooze 5 min.
   - The caption shows "Snoozed, rings at HH:MM".
   - Let it ring again, press OK.
4. **Automatic stop.** Set "Stop automatically after" to 10 s with "Restart the countdown after the
   automatic stop" checked, and let it ring without touching anything: the alarm stops after 10 s and
   the countdown starts again. Uncheck the restart option and repeat: the timer returns to idle.
5. **Custom files.**
   - Choose a very large MP3, and a file on another drive (`E:/...`): it plays at once and the window
     stays responsive.
   - Then move the file away and let it ring: the default sound plays, the log has a WARNING "Alarm
     sound (FILE) not found", and the dialog shows "The sound file was not found." under Sound.
6. **Sleep.** Start a 5 min countdown, put the PC to sleep for 2 min, wake it, and note the remaining
   time and the "Ends at" caption. Please report what you saw: it decides whether the deadline must use
   the wall clock (ADR-011).
7. **Language.** Switch FRA/ENG while ringing: every text updates (caption, buttons, Snooze label).
8. **Edit dialog.**
   - The window behind it is darker and the dialog is centered on it.
   - Typing 0 h 0 min 0 s shows the error under Duration and disables Save.
   - After a change, Cancel closes the dialog at once and the change is gone when you reopen it. Do the
     same with Escape and with the close button.
   - Preview plays once and stops when the dialog closes.
   - While the timer runs, the dialog shows the note about the next start.
   - The new sound "Notification alert" is in the list.
9. **Double click.** Double-click Start quickly: the timer starts and is not paused. Click the same
   button again after a moment: it pauses.
10. **Quit.** Click the close button: "Do you want to quit Concentrator?" appears, and Escape keeps the
    window open. While a countdown runs, the question mentions it.
11. **Persistence.** Change every setting, restart: the settings are kept and the countdown is not.
12. **Built app.** Build with `uv run python scripts/build.py` and repeat steps 1, 2 and 5 with
    `dist\Concentrator\Concentrator.exe`.

## Open questions

1. **Escape and the close button of the edit dialog.** Your decision named Cancel; I applied it to
   Escape and to the close button of the dialog as well, as Escape means Cancel in a dialog. Default:
   keep it that way.
2. **Later forms** (favorites in phase 3, settings in phase 4). Should they also close without asking?
   `AGENTS.md` section 8.4 keeps the confirmation as the general rule. Default: yes, no confirmation
   either, for consistency with the timer dialog.
