# Phase 2 — Timer core

Depends on: phase 1. Branch: `phase-2-timer-core`.

## Goal

The countdown timer at the top of zone 2: hours, minutes, seconds in large digits, one-click start,
a strict state machine with the button matrix below, an MP3 alarm that rings even when the app is in
the background (sound, Windows notification, flashing taskbar button), snooze, auto-stop,
auto-restart, and an edit dialog with real-time validation.

## In scope

Timer configuration (persisted), timer session (runtime, not persisted), alarm playback, attention
(tray toast, taskbar flash, module bar highlight), edit dialog, tray icon with Show/Quit menu.
Amended at the review (ADR-038): no tray toast and no tray icon; the taskbar flash and the module bar
highlight remain.

## Out of scope

Presets and hourly chime (phase 3), focus queue (phase 7), restoring a running countdown after a
restart (not planned, see review question 4).

## State machine

States (`TimerStateEnum`): `UNKNOWN=-1, UNSET=0, IDLE=1, RUNNING=2, PAUSED=3, RINGING=4`.

| From | Command / event | To | Effect |
|---|---|---|---|
| IDLE | start | RUNNING | deadline = now + duration |
| RUNNING | pause | PAUSED | remaining frozen |
| PAUSED | resume | RUNNING | deadline = now + remaining |
| RUNNING, PAUSED | reset | IDLE | remaining = configured duration, snooze flag cleared |
| RUNNING | tick, remaining <= 0 | RINGING | alarm starts (sound, attention) |
| RINGING | acknowledge (OK) | IDLE | alarm stops |
| RINGING | restart | RUNNING | full configured duration, alarm stops |
| RINGING | snooze | RUNNING (snoozed) | duration = `timer.snooze_minutes`, alarm stops |
| RINGING | tick, ringing for `auto_stop_seconds` (> 0) | IDLE, or RUNNING if `auto_restart` | alarm stops |

Any other pair returns `DataResult.fail(TIMER_TRANSITION_INVALID)` and changes nothing. A snoozed
countdown that reaches zero rings again. The engine computes remaining time from
`ClockPort.monotonic()` at each tick; it never decrements a counter.

## Button matrix (left / middle / right)

| State | Left | Middle | Right |
|---|---|---|---|
| IDLE | Edit timer (enabled) | Reset (disabled) | Start (enabled) |
| RUNNING | Edit timer (enabled) | Reset (enabled) | Pause (enabled) |
| PAUSED | Edit timer (enabled) | Reset (enabled) | Resume (enabled) |
| RINGING | Restart (enabled) | OK (enabled) | Snooze {n} min (enabled) |

Plus the `ActionGate` rule: every button is disabled while its action is busy and for at least
`ui.action_cooldown_ms`.

## Display

- Always `HH:MM:SS`, font `ui.timer_font_family` at `ui.timer_font_size_px` (64 px), tabular digits
  so the width never jitters.
- IDLE: configured duration. RUNNING: `ceil(remaining)`. PAUSED: frozen value. RINGING: `00:00:00`
  blinking every `ui.alert_blink_interval_ms` (blink phase computed by the presenter from the
  monotonic clock; the widget only applies an `alert` property).
- Caption under the digits: RUNNING "Ends at 17:52", snoozed "Snoozed, rings at 17:57", PAUSED
  "Paused", RINGING "Time is up", IDLE empty.
- While RINGING and another page (journal, settings) is shown, the Focus button of the module bar is
  highlighted.

## Edit dialog

Fields: duration (hours 0-99, minutes 0-59, seconds 0-59), sound (built-in list + "Choose an MP3
file..."), volume 0-100 with a "Preview" button, play count (1-`timer.max_loop_count`) or "Repeat
until stopped", auto-stop after N seconds (0 = never, otherwise 5-`timer.max_auto_stop_seconds`),
"Restart automatically after auto-stop".

- Real-time validation through `TimerConfigRules`, inline errors, `is_dirty`, Save enabled only
  when dirty and valid, Cancel asks confirmation when dirty. Amended at the review (ADR-038): Cancel,
  Escape and the close button close the dialog without asking.
- While RUNNING or PAUSED, sound settings apply to the next ringing; a duration change applies at the
  next start or reset (the dialog says so).
- Preview plays once at the chosen volume and stops when the dialog closes.
- A chosen file path is normalized (`\` -> `/`) and must exist; a missing file at ringing time falls
  back to `timer.default_sound` (WARNING logged) and then to `QApplication.beep()`.

## Deliverables

### Domain (`domain/timer/`)

`duration.py` (`Duration` in whole seconds, `from_hms`, `hms`), `volume.py`, `sound_kind_enum.py`
(`BUILTIN=1, FILE=2`), `sound_ref.py`, `timer_state_enum.py`, `timer_transition_enum.py`
(`STARTED, PAUSED, RESUMED, RESET, ALARM_STARTED, ACKNOWLEDGED, RESTARTED, SNOOZED, AUTO_STOPPED,
AUTO_RESTARTED`), `timer_config.py` (entity), `timer_config_rules.py`, `timer_limits.py` (frozen
limits built from `AppConfig`), `timer_session.py` (immutable; `start`, `pause`, `resume`, `reset`,
`acknowledge`, `restart`, `snooze`, `tick(now) -> TimerTickResult(session, transitions)`,
`remaining(now)`, `displayed_seconds(now)`).

### Application

- Ports: `sound_player_port.py` (`play(sound, volume, loops)`, `stop()`, `check(sound)`),
  `sound_catalog_port.py` (`builtin_sounds()`, `resolve(sound) -> DataResult[str]`),
  `attention_port.py` (`notify(title, message)`, `request_attention()`),
  `timer_config_reader_port.py`, `timer_config_writer_port.py`.
- `timer/timer_engine.py`: owns the `TimerSession`, registered on `AppTicker`, publishes
  `TimerChangedEvent(transitions, displayed_seconds)` only when state, displayed second or blink
  phase changes.
- `timer/alarm_coordinator.py`: subscribes to timer events; starts/stops the alarm player; calls
  attention with translated texts.
- `timer/timer_commands.py`: `start`, `pause`, `resume`, `reset`, `acknowledge`, `restart`, `snooze`,
  `update_config(draft)`. `timer/timer_queries.py`: `current_view()`, `config()`, `builtin_sounds()`.

### Infrastructure

- `qt/qt_sound_player.py`: `QMediaPlayer` + `QAudioOutput`; loops via `setLoops` (`-1` = infinite);
  `QAudio.convertVolume(value / 100, LogarithmicVolumeScale, LinearVolumeScale)`; `errorOccurred`
  logged and converted to the fallback chain. Two instances: `alarm` and `preview` (phase 3 adds
  `chime`).
- `qt/qt_attention.py`: `QApplication.alert` only, when no Concentrator window is active. Amended at
  the review (ADR-038): no notification area icon, no Windows notification (`showMessage`).
- `system/builtin_sound_catalog.py`: lists `assets/sounds/*.mp3`; label key
  `sound.builtin.<file stem>`.
- Persistence: `TimerConfigSchema`, mapper, singleton store; default config created from the ini on
  first load.

### Presentation and UI

- `presentation/timer/`: `timer_presenter.py`, `timer_snapshot.py`, `timer_edit_presenter.py`,
  `timer_edit_form.py`, `timer_edit_snapshot.py`; `presentation/common/duration_formatter.py`.
- `ui/panels/timer_panel.py` (display + caption + three `SnapshotButton`s, emits
  `action_requested(int)`), `ui/panels/timer_edit_form_panel.py`.
- `ui/widgets/`: `duration_display_widget.py`, `duration_input_widget.py`, `sound_picker_widget.py`,
  `volume_slider_widget.py`, `field_error_label.py`.
- `ui/windows/timer_edit_dialog.py`; `FocusPage` places `TimerPanel` at the top of zone 2.

New `ActionIdEnum` values: `TIMER_EDIT`, `TIMER_START`, `TIMER_PAUSE`, `TIMER_RESUME`, `TIMER_RESET`,
`TIMER_ACKNOWLEDGE`, `TIMER_RESTART`, `TIMER_SNOOZE`, `TIMER_EDIT_SAVE`, `TIMER_EDIT_CANCEL`,
`TIMER_SOUND_PREVIEW`, `TIMER_SOUND_CHOOSE_FILE`, `TRAY_SHOW`, `TRAY_QUIT`. New `RenderSectionEnum`
values: `TIMER`, `TIMER_EDIT`, `TRAY`. Amended at the review (ADR-038): `TRAY_SHOW`, `TRAY_QUIT`
and `TRAY` are removed (values 27, 28 and 7 are not reused).

## File format (section added)

```toml
[timer]
id = '019a5c1f-0b2e-7d4a-8c61-2a3b4c5d6e7f'
created_at = '2026-11-06T16:40:00Z'
updated_at = '2026-11-06T16:50:12Z'
duration_seconds = 1500
sound = { kind = 2, value = 'D:/Music/Alarms/long alarm.mp3' }
volume = 80
loop_count = 3
loop_forever = false
auto_stop_seconds = 120
auto_restart = false
```

## `concentrator.ini` (new keys)

```ini
[ui]
timer_font_family = Cascadia Mono
timer_font_size_px = 64
alert_blink_interval_ms = 500

[timer]
snooze_minutes = 5
default_duration_seconds = 1500
min_duration_seconds = 1
max_duration_seconds = 359999
default_sound = alarm-classic
default_volume = 80
default_loop_count = 3
max_loop_count = 99
default_auto_stop_seconds = 120
max_auto_stop_seconds = 3600
notification_duration_ms = 8000
```

Added by ADR-038: `min_auto_stop_seconds = 5`. Removed at the review (ADR-038):
`notification_duration_ms`.

## Error codes

| Code | Name |
|---|---|
| 4001 | `TIMER_DURATION_TOO_SHORT` |
| 4002 | `TIMER_DURATION_TOO_LONG` |
| 4003 | `TIMER_VOLUME_OUT_OF_RANGE` |
| 4004 | `TIMER_LOOP_COUNT_OUT_OF_RANGE` |
| 4005 | `TIMER_AUTO_STOP_OUT_OF_RANGE` |
| 4006 | `TIMER_TRANSITION_INVALID` |
| 4007 | `TIMER_SOUND_UNSET` |
| 7101 | `AUDIO_FILE_NOT_FOUND` |
| 7102 | `AUDIO_FORMAT_UNSUPPORTED` |
| 7103 | `AUDIO_PLAYBACK_FAILED` |
| 7104 | `AUDIO_DEVICE_UNAVAILABLE` |
| 7204 | `NOTIFICATION_UNAVAILABLE` (retired at the review, never reused, ADR-038) |

## Assets to provide before this phase

`assets/sounds/alarm-classic.mp3`, `assets/sounds/alarm-soft.mp3` (CC0 or your own recordings),
`assets/icons/concentrator.ico` if the placeholder is not kept. The agent cannot download them.
Amended (ADR-038): five sounds `alarm-<author>-<title>.mp3` were provided, with a license confirmed by
the owner; `timer.default_sound = alarm-lesiakower-reverby-notification-sound`.

## Tests

- `TimerSession`: parametrized table of every (state, command) pair; `tick` boundaries
  (remaining 0.001 s -> still RUNNING, displayed 1; 0 -> RINGING); pause/resume accumulation over
  many cycles; one-hour run with `FakeClock` stepping 100 ms stays exact; auto-stop with and without
  auto-restart; snooze rings again; reset clears snooze.
- `TimerConfigRules`: every limit, both sides.
- `TimerEngine` + `AlarmCoordinator` with fakes: sound played once with the right loops and volume;
  attention called only when the window is inactive (fake flag); events only on visible change.
- `TimerPresenter`: button matrix for each state in English and French; captions; blink phase.
- `TimerEditForm`: dirty tracking, inline errors, save disabled when invalid, duration change while
  running does not alter remaining time.
- Gate: a double click on Start performs one start.
- Persistence: timer section round trip; unknown sound kind -> `UNKNOWN` -> rules error.
- UI smoke: `TimerPanel.render` for each state sets texts, enabled flags and the alert property.

## Acceptance criteria

- [ ] One click on Start starts the countdown; digits are 64 px and do not jitter.
- [ ] The button matrix matches the table in every state.
- [ ] At zero, the alarm rings with the chosen sound, volume and play count.
- [ ] With the journal page shown: sound plays, the digits blink, the Focus button is highlighted.
      With the window minimized or another app focused: sound plays and the taskbar button flashes
      until the window is activated; no Windows notification, no notification area icon (amended,
      ADR-038).
- [ ] OK, Restart, Snooze and auto-stop (with and without auto-restart) behave as specified.
- [ ] A 100 MB+ MP3 plays immediately and the UI stays responsive.
- [ ] A deleted custom sound falls back to the default sound with a WARNING in the log.
- [ ] Edit dialog: inline errors appear while typing; Save is disabled until valid and changed.
- [ ] Settings survive a restart; a running countdown does not (documented in `USAGE.md`).
- [ ] The frozen build (`scripts/build.py`) plays MP3 files (QtMultimedia plugins bundled).

## Manual test script

1. Set 00:00:10, Start, switch to the journal page, wait: sound, blinking digits, highlighted Focus
   button, no toast while the window stays active (amended, ADR-038).
2. Repeat with the window minimized, then with another application in front.
3. Snooze; check the caption; let it ring again; press OK.
4. Auto-stop 10 s with auto-restart on; let it ring without touching anything.
5. Choose a very large MP3 and a file on another drive (`E:/...`); move the file away; let it ring.
6. Start a 5 min countdown, put the PC to sleep for 2 min, wake it, note the remaining time. Record
   the observed behavior in the review report (it decides whether the deadline must switch from the
   monotonic clock to wall-clock UTC).
7. Switch FRA/ENG while ringing: every text updates.

## Review gate questions

1. In PAUSED, Reset is enabled (your brief said disabled when "stopped"): confirm.
2. When finished there are three buttons (Restart, OK, Snooze 5 min): confirm.
3. "Restart automatically" is applied after auto-stop only: is that the intended meaning?
4. Should a running countdown survive an app restart (persist the UTC deadline)? Default: no.
