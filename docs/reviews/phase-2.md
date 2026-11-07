# Phase 2 review report

First issue (2026-11-07). Branch `phase-2-timer-core`, 9 commits on top of `main` (`911d243`, tagged
`phase-1-accepted`); the branch is not pushed.

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
- **Attention:** when no Concentrator window is active, a Windows notification appears and the taskbar
  button flashes. While another page is shown, the Focus button is highlighted.
- **Edit dialog:** the dialog runs over the main window. It validates while you type, enables Save only
  when the draft changed and is valid, asks before discarding changes, plays a preview and picks MP3
  files.
- **Quitting:** a notification area icon offers Show and Quit. Closing now asks "Do you want to quit
  Concentrator?" first.
- **Data file:** the `[timer]` section is saved in the data file. Files from phase 1 are completed from
  `concentrator.ini` when they are opened.

## Spec coverage

| Requirement | Status | Notes |
|---|---|---|
| Domain: `Duration`, `Volume`, `SoundKindEnum`, `SoundRef`, `TimerStateEnum`, `TimerTransitionEnum`, `TimerConfig`, `TimerConfigRules`, `TimerLimits`, `TimerSession` | done | plus `TimerSettings`, the editable part of the configuration (ADR-038, build item 4) |
| Application ports: sound player, sound catalog, attention, timer config reader/writer | deviated (approved) | `play(SoundPlayback)` carries the fallback files (owner decision 8); `AttentionPort.is_application_active()` added (build item 2) |
| `TimerEngine`, `AlarmCoordinator`, `TimerCommands`, `TimerQueries` | done | plus `SoundPreview`, `TimerDefaults`, `UserDataDefaults` (completion of missing sections) |
| `QtSoundPlayer` (alarm and preview instances), `BuiltinSoundCatalog`, persistence of `[timer]` | done | `QtSoundPlayer` also follows the default audio output device |
| `QtAttention` owning the tray icon | deviated | the icon is in `ui/panels/tray_panel.py` because of the layer contracts; `QtAttention` receives it (build item 1) |
| Presentation: timer presenter, snapshot, edit presenter, form, snapshot; `duration_formatter` | done | plus `TimerEditView`, `TimerLayout`, `TrayPresenter`, `MainWindowPresenters`, action groups |
| UI: `TimerPanel`, `TimerEditFormPanel`, the five widgets, `TimerEditDialog`, `FocusPage` zone 2 | done | plus `TrayPanel`; "Choose an MP3 file..." is a button next to the list (build item 6) |
| New `ActionIdEnum` and `RenderSectionEnum` values | done | as listed in the spec |
| File format `[timer]` | done | golden test: the writer produces the spec example byte for byte |
| `concentrator.ini` keys | done | plus `timer.min_auto_stop_seconds` (owner decision 7) |
| Error codes 4001-4007, 7101-7104, 7204 | done | every code is produced by at least one test |
| Assets | deviated (approved) | five sounds provided by the owner, names kept, license confirmed (owner decision 1) |
| Tests listed in the spec | done | "double click on Start" is read as two clicks within the cooldown (owner decision 5) |
| Frozen build plays MP3 | partial | the FFmpeg plugin is bundled and the frozen self-check decodes MP3; the sound itself is a manual check |

## Deviations and decisions

All are recorded in ADR-038 (new), ADR-004 (build verification) and ADR-011 (now accepted).

**Approved at the plan review (2026-11-07):**
1. **Sounds.** The five sounds keep their names `alarm-<author>-<title>.mp3`.
   - The default sound is `alarm-lesiakower-reverby-notification-sound`.
   - `assets/sounds/SOURCES.md` names the authors.
   - Each sound has an EN/FR label.
2. **Notification rule.** The notification and the flashing taskbar button come only when no
   Concentrator window is active. The acceptance criterion and manual step 1 of the spec are amended.
3. **Alarm while the edit dialog is open:** no special handling.
4. **Quit question.** Closing (close button, Alt+F4, "Quit" in the notification area menu) asks first.
   When the timer is not idle, the question says the countdown will be lost.
   - Found during the build: Qt 6 closes the windows itself after `WM_ENDSESSION`. Once Windows has
     announced the end of the session, the question is therefore skipped; the changes were flushed
     already.
5. **Cooldown per button.** A click on an enabled button always counts. The actions of the three timer
   buttons form one group in `ActionGate`, so the clicked button stays disabled for the cooldown even
   though it shows another action.
6. **Older files.** A file without `[timer]` is completed from the ini and saved when it is opened or
   reloaded.
7. **New ini key:** `timer.min_auto_stop_seconds = 5`.
8. **Sound fallback chain:**
   - The application checks that the chosen and default files exist; a missing file is logged as a
     WARNING, without its path.
   - The player tries the next file when Qt reports an error, then beeps.
9. **Spec review questions 1-4** confirmed: Reset is enabled in PAUSED; three buttons while ringing;
   automatic restart only after the automatic stop; a running countdown is not restored after a
   restart.

**Decided during the build** (please approve; ADR-038, "Decided during the build"):
1. **Tray icon in the ui.** `TrayPanel` owns the notification area icon; bootstrap hands it to
   `QtAttention`. A click on the icon or on a notification shows the window.
2. **`AttentionPort.is_application_active()`.** The notification rule lives in `AlarmCoordinator`,
   where it is tested.
3. **Integer milliseconds, steady caption.** The session works on integer milliseconds. The "Ends at"
   time is computed once, when the countdown starts running, so it never flickers.
4. **`TimerSettings`** is the draft of the edit form. The file keeps the flat layout of the spec.
5. **Ini limits on read.** The limits of `concentrator.ini` apply when a file is read: a stored value
   outside them makes the file invalid (question 2).
6. **Sound check in the edit form:**
   - A missing stored sound is only a warning: you can still save, and the alarm falls back.
   - A newly chosen sound that cannot be played blocks Save.
   - Files chosen while the dialog is open stay in the list.
7. **Error messages** give the duration limits as `HH:MM:SS`.
8. **Catalog test.** It now checks the literal keys passed to `tr()` in every layer, because the
   application layer translates the notification.
9. **Wrappers.** `MainWindowHandle` and `TimerEditWindow` wrap the Qt widgets: a `QWidget` cannot
   subclass a `Protocol`. `MainWindow` takes its presenters as one value.
10. **Details:**
    - no event on the first idle tick;
    - `placeholder.focus.zone2` removed;
    - the edit dialog takes the size of its layout (no ini key);
    - the snapshot of the edit dialog is built by `TimerEditView` (file size limit).

No suppression comment was added: the only one in the code base is still the phase 0
`qt_main_thread_dispatcher.py` one.

## Gates

`uv run python scripts/check.py` on the final code commit:

| Gate | Result |
|---|---|
| `ruff format` | passed |
| `ruff check` | passed |
| `basedpyright` (strict) | 0 errors, 0 warnings, 0 notes |
| `furryp check concentrator` | all checks passed (`domain.todo` still matches no module: phase 5) |
| `pytest --cov` | 1381 passed, 0 failed, 0 skipped |
| `coverage_gate.py` | passed |

Also run here (not part of the gates):
- **Build:** `uv run python scripts/build.py` succeeded. The bundle grows from 124 MB to 146 MB. It
  contains `assets/sounds` and `PySide6/plugins/multimedia/ffmpegmediaplugin.dll`. The frozen
  self-check passed; it now also requires the default sound and MP3 decoding.
- **Shipped sounds:** each of the five files loads in `QMediaPlayer` without error, with durations from
  1.0 to 2.4 s.

## Coverage per layer

Branch coverage (statements + branches):

| Layer | Coverage | Threshold |
|---|---|---|
| domain | 100.00 % | 90 % |
| application | 99.28 % | 85 % |
| presentation | 99.62 % | 80 % |
| infrastructure | 98.08 % | — |
| ui | 98.77 % | — |
| bootstrap | 87.92 % | — |
| overall | 98.18 % | 75 % |

Not covered: the event loop path of `bootstrap/app.py` (as in phase 1), `TimerServices.ringing`
(used only by the running window), and three test-only properties of the ui.

## Manual test script

The GUI cannot be inspected from here; please run these on Windows 11 at 100 % and 150 % scaling, with
sound on. The first start after this phase completes your data file with a `[timer]` section (open it
in Notepad to check).

1. **Background page.** Edit timer: 00:00:10, Save. Start, switch to the Journal page, wait.
   - You should hear the sound and see the digits blink (on the Focus page) and the Focus button
     outlined.
   - No Windows notification, because the window is active (ADR-038).
2. **Window not active.** Repeat with the window minimized, then with another application in front.
   - A notification "Time is up" appears and the taskbar button flashes until you come back.
   - Clicking the notification brings the window back.
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
7. **Language.** Switch FRA/ENG while ringing: every text updates (digits caption, buttons, Snooze
   label).
8. **Edit dialog.**
   - The window behind it is darker and the dialog is centered on it.
   - Typing 0 h 0 min 0 s shows the error under Duration and disables Save.
   - Cancel after a change asks "Discard the changes...?".
   - Preview plays once and stops when the dialog closes.
   - While the timer runs, the dialog shows the note about the next start.
9. **Double click.** Double-click Start quickly: the timer starts and is not paused. Click the same
   button again after a moment: it pauses.
10. **Quit.**
    - Click the close button: "Do you want to quit Concentrator?" appears, and Escape keeps the window
      open.
    - While a countdown runs, the question mentions it.
    - "Quit" in the menu of the notification area icon asks the same question.
    - After quitting, no stale icon stays in the notification area.
11. **Persistence.** Change every setting, restart: the settings are kept and the countdown is not.
12. **Built app.** Build with `uv run python scripts/build.py` and repeat steps 1, 2 and 5 with
    `dist\Concentrator\Concentrator.exe`. In the built app, the notification should name Concentrator,
    not Python.

## Open questions

1. **Decided during the build** (ADR-038, items 1 to 10): approve them. Default: approve.
2. **Ini limits on read.** If you lower a maximum in `concentrator.ini` (for example
   `max_duration_seconds`), a data file holding a larger value no longer opens and the recovery dialog
   appears. Alternative: accept the stored value and only enforce the limit when it is edited. Default:
   keep the strict rule.
3. **Sound sources.** `SOURCES.md` names the authors from the file names. Do you want the source site
   or URL recorded too? Default: as is.
4. **Notification area tooltip.** It shows "Concentrator". It could show the remaining time. Default:
   keep it simple.
