# Phase 3 review report

First issue (2026-11-09). Branch `phase-3-timer-extras`, 8 commits on top of `main` (`ffffd94`, which
holds `phase-2-accepted` and the owner's renamed sounds); the branch is not pushed.

## Summary

Zone 2 of the Focus page now shows, below the timer and the room kept for the focus queue:
- **Favorites:**
  - one button per saved duration (15, 30 and 45 min in a new file), then **Add...**; the buttons wrap
    onto several lines when zone 2 is narrow;
  - one click sets the timer duration and starts the countdown; the buttons are disabled outside
    `IDLE`, with the tooltip "Reset the timer to use a favorite";
  - a right-click opens Edit, Move earlier, Move later and Delete, in every timer state.
- **Special options:** **Chime every hour**, the active hours (08:00 – 20:00) and a **...** button.
  The chime dialog sets the sound, the volume (with Preview) and the first and last hour.
- **Chime:** the chime plays once per local hour, within the first `chime.trigger_window_seconds`,
  never late, never twice when the clocks go back. It is skipped while the timer rings and has its own
  player.
- **Data file:** `[[timer_presets]]` and `[hourly_chime]` are written in the format of the spec. A
  phase 2 file gets them from `concentrator.ini` when it is opened; `timer_presets = []` stays empty.
- **Sounds:** the code and the docs follow the owner's renamed sounds (`alarm`, `beep`, `chime`,
  `notification`, `soft`); `timer.default_sound = alarm`, `chime.default_sound = chime`.

## Spec coverage

| Requirement | Status | Notes |
|---|---|---|
| `TimerPreset`, `TimerPresetsCollection` (order, limit, unique durations, `next_position`, `moved`) | deviated (approved) | `ordered()` for the display order; `moved(preset_id, offset, now)` renumbers positions |
| Seed from `timer.default_presets_minutes` when the section is missing | done | `timer_presets = []` is not seeded |
| Favorites UI: wrapping buttons, Add, context menu, delete confirmation | done | `FlowLayout`; the menu is opened through an event filter (see decisions) |
| One click on an idle timer sets and starts; disabled otherwise with the tooltip | done | `TimerCommands.start_with_duration` |
| `PresetEditDialog`: label, duration, real-time validation, `is_dirty` | deviated (approved) | Add: Save enabled when valid; Cancel closes without asking |
| Nine generic operations through the favorite ports | deviated (build) | reader port typed with `TimerPresetsCollection`, composes the generic reader |
| `HourlyChime` singleton, rules 0-23 and start <= end | done | plus `ChimeSettings` |
| `ChimeService` on `AppTicker`: window, once per (date, hour), no late chime | done | registered after the timer engine |
| No chime while RINGING, own `chime` player, plays once | done | skipped hour logged at INFO |
| Checkbox "Chime every hour" and "..." opening `ChimeSettingsDialog` | done | active hours shown next to the check box |
| Domain, application, infrastructure, presentation and ui deliverables | done | plus `ChimeQueries`, `ChimeDefaults`, `PresetEditForm` draft, shared sound helpers |
| New `ActionIdEnum` (29-41) and `RenderSectionEnum` (8-11) values | done | plus `CHIME_SOUND_CHOOSE_FILE` (42) |
| `PresetsPresenter` follows `TimerChangedEvent` | done | re-renders on transitions only |
| File format sections | done | golden test: the writer produces the spec example byte for byte |
| `concentrator.ini` keys | deviated (approved) | plus `timer.max_preset_label_length`; every key validated at startup |
| Error codes 4101-4103, 4201-4202 | done | each produced by at least one test, messages in both catalogs |
| Asset `assets/sounds/chime.mp3` | done | provided by the owner; the self-check requires it |
| Tests listed in the spec | done | DST with fixed-offset zones (no `tzdata` on Windows) |

## Deviations and decisions

All are recorded in ADR-039.

**Owner decisions applied** (plan review, "Suit tes recommandations"):
- The sounds were renamed by the owner, and the code and docs follow.
- The favorite and chime dialogs close without asking. This answers the open questions of the phase 2
  review, and `AGENTS.md` section 8.4 now says so.
- **Add...** proposes the timer duration and allows Save as soon as the draft is valid.
- The context menu stays available in every timer state.
- An hour that starts during an alarm is skipped.
- One click on a favorite sets the duration and starts the timer; the chime hours stay 08:00 to 20:00.
- New ini key `timer.max_preset_label_length` and new action `CHIME_SOUND_CHOOSE_FILE`.

**Decided during the build** (ADR-039, please approve):
1. A move renumbers the positions `0, 1, 2...`; the file lists the favorites in position order.
2. Strict limits on read, as in phase 2: a file with more favorites than `timer.max_presets`, a label
   that is too long, or two favorites with the same duration or the same id is invalid.
3. `TimerLimits` carries `max_presets` and `max_preset_label_length` (no separate limits class).
4. `TimerPresetReaderPort` is a standalone typed port (`DataResult` is invariant, so it cannot narrow
   `EntityReaderPort`).
5. `HourlyChime` holds `enabled` plus `ChimeSettings`.
6. The shared helpers are `sound_candidates`, `SoundChoices`, `SoundCheck`, `pick_sound_file` and
   `EditorDialogPort`.
7. **Context menu on a disabled favorite:** in Qt, a disabled button neither handles nor passes on its
   context menu event, but event filters still see it. The panel therefore filters the events of its
   buttons. Checked on the offscreen platform; please check it with the mouse (manual step 3).
8. **Automatic labels:** `15 min`, `2 h`, `1 h 30`, `1 min 30 s`.
9. **Chime timing:** switching the chime on during the window still chimes that hour. When the clocks go
   forward, the next hour that exists chimes.

No suppression comment was added: the only one in the code base is still the phase 0
`qt_main_thread_dispatcher.py` one.

## Gates

`uv run python scripts/check.py` on the last commit:

| Gate | Result |
|---|---|
| `ruff format` | passed |
| `ruff check` | passed |
| `basedpyright` (strict) | 0 errors, 0 warnings, 0 notes |
| `furryp check concentrator` | all checks passed (`domain.todo` still matches no module: phase 5) |
| `pytest --cov` | 1709 passed, 0 failed, 0 skipped |
| `coverage_gate.py` | passed |

I also ran `uv run python scripts/build.py`: the build succeeded and the frozen self-check passed. That
check covers both default sounds and the round trip of every section.

## Coverage per layer

Branch coverage (statements + branches):

| Layer | Coverage | Threshold |
|---|---|---|
| domain | 100.00 % | 90 % |
| application | 99.44 % | 85 % |
| presentation | 99.38 % | 80 % |
| infrastructure | 98.22 % | — |
| ui | 98.94 % | — |
| bootstrap | 89.24 % | — |
| overall | 98.42 % | 75 % |

Not covered:
- the event loop path of `bootstrap/app.py` (as in phases 1 and 2);
- the "not attached" wiring errors of the new presenters;
- a few test-only properties of the ui.

## Manual test script

The GUI cannot be inspected from here. Please run these steps on Windows 11 at 100 % and 150 % scaling,
with sound on.

1. **Default favorites.** Start with a new data file. Zone 2 shows, from top to bottom: the timer,
   empty room, **Favorites** (15 min, 30 min, 45 min, Add...) and **Special options**.
   - Click **15 min**: the countdown starts at 00:15:00 and the three favorites are disabled. Their
     tooltip reads "Reset the timer to use a favorite".
   - Reset, then repeat with 30 and 45 min.
2. **Pomodoro.** Click **Add...**: the dialog proposes the current duration and an empty label, with
   "Automatic: ..." as placeholder.
   - Type "Pomodoro" and set 25 min, then Save.
   - Try the duration of an existing favorite: the error shows under Duration and Save is disabled.
3. **Context menu.**
   - Right-click **Pomodoro** and choose **Move earlier** until it is first; the first favorite has
     Move earlier disabled.
   - Right-click **45 min**, choose **Delete...** and answer Delete.
   - Start a countdown and right-click a disabled favorite: the menu must open.
4. **Restart.** Restart Concentrator: Pomodoro, 15 min, 30 min, in this order.
   - Delete every favorite and restart: none comes back.
5. **Narrow zone 2.** Drag the splitter to the right: the favorite buttons wrap onto several lines and
   nothing overlaps the special options.
6. **Chime.** Check **Chime every hour**. In **...**, set the first and the last chime to the current
   hour, Preview, then Save. The hours next to the check box follow.
   - Wait for the next full hour, or set the Windows clock to `HH:59:30`. One chime plays at `H:00`, not
     twice.
   - Set the hours so that they do not include the next hour: no chime.
7. **Chime during an alarm.** Start a timer that rings a few seconds before a full hour. The alarm
   plays, the chime is skipped, and the log has "Hourly chime of HH:00 skipped: the timer is ringing".
8. **Sounds.** The lists show **Alarm, Beep, Chime, Notification, Soft tone** in both dialogs. If your
   data file names a phase 2 sound, the timer dialog shows "The sound file was not found." under Sound
   and the alarm plays **Alarm**. Choose a sound and save.
9. **Language.** Switch FRA/ENG: the favorites block, the menu, both dialogs, the special options and
   the automatic labels ("15 min", "1 h 30") update at once.
10. **Built app.** Build with `uv run python scripts/build.py` and repeat steps 1 and 6 with
    `dist\Concentrator\Concentrator.exe`.

## Open questions

1. **Sounds of your existing data file.** Your file may still name a phase 2 sound
   (`alarm-lesiakower-...`). That sound plays the default **Alarm**, and the dialog shows it as missing
   until you choose another one. Should the old names be translated automatically when the file is
   read (for example, the lesiakower sound becomes `chime`)? Default: no; choose the sound once in the
   timer dialog.
2. **Automatic label with hours and seconds.** 1 h 0 min 5 s reads "1 h 5 s". Default: keep it, since
   favorites are usually whole minutes.
3. **Lowering `max_presets` or `max_preset_label_length`** below what the file holds makes the file
   invalid at the next start (strict limits, as in phase 2). Default: keep this, since the ini
   documents it.

## Owner answers (2026-11-09)

"Suit tes recommandations pour les arbitrages": the build decisions are approved and the three open
questions take their defaults (ADR-039 amendment).

## Code review (2026-11-09)

A code review of `main...phase-3-timer-extras` found the issues below. Nothing is changed yet; each line
gives the recommended fix.

| # | Severity | Where | Issue | Recommended fix |
|---|---|---|---|---|
| 1 | bug (UX) | `preset_edit_presenter.py` | After a click on a favorite, the timer duration is that favorite's, so **Add...** always opens on a duplicate with Save disabled | Propose the timer duration if it is free, else the first free duration in steps of 5 minutes after it |
| 2 | bug (low) | `presets_presenter.py`, `qt_dialog_service.py` | The delete question shows the user's label in a `QMessageBox` in automatic text format: a label such as `<b>x</b>` renders as rich text (`AGENTS.md` section 8.5) | Plain text in every `QtDialogService` message box |
| 3 | rule | `timer_presets_collection.py` | `moved()` returns a bare tuple of entities (`AGENTS.md` rule 7) | Return a `TimerPresetsCollection` of the changed favorites |
| 4 | robustness | `preset_commands.py` | `move()` writes favorite by favorite and stops at the first failure without undoing (the failure cannot happen today: same synchronous turn) | Check every write is possible first; keep one event |
| 5 | consistency | `timer_presets_mapper.py` | A label written by hand on two lines or with extra spaces is loaded as is | Normalize the label when the file is read, like paths |
| 6 | latent | `timer_preset.py` | `copy_business` of a favorite (generic operation, no caller) would store a second favorite with the same duration, which makes the file invalid | Refuse it in the favorite writer with `PRESET_DURATION_DUPLICATE` |
| 7 | UX (rare) | `preset_edit_presenter.py` | A save refused by the command for a reason the form does not check (limit reached, favorite gone) is only logged | Show the message in the dialog through `DialogPort.error` |
| 8 | duplication | presenters | The duration field and the field error lookup are copied from `TimerEditView`; `action_button` is not used everywhere | Share them |
| 9 | efficiency | `presets_presenter.py` | Each render reads and sorts the favorites twice | Read once |
| 10 | decided | `concentrator.ini` | Phase 2 sound names are not translated | Owner decision: no translation (question 1) |
