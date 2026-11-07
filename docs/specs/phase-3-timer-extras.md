# Phase 3 — Timer favorites and hourly chime

Depends on: phase 2. Branch: `phase-3-timer-extras`.

## Goal

Zone 2 gains, below the space reserved for the focus queue (phase 7): a list of **favorites**
(preset durations, 15 / 30 / 45 min by default) that start the timer in one click, and a
**special options** block with the **hourly chime**.

Zone 2 final order (top to bottom): timer, focus queue (phase 7), favorites, special options.

## Favorites

- `TimerPreset` entity: `id`, `created_at`, `updated_at`, `label` (optional, max 40 chars; empty =
  auto label "15 min" / "1 h 30"), `duration`, `position`.
- `TimerPresetsCollection`: ordered by `position`; at most `timer.max_presets`; durations unique
  (`PRESET_DURATION_DUPLICATE`); `next_position()`, `moved(preset_id, offset)`.
- Seed: when the file has no `timer_presets` section, create one preset per value of
  `timer.default_presets_minutes`.
- UI: a wrapping grid of buttons, one per preset, plus an "Add" button. Context menu on a preset:
  Edit, Move earlier, Move later, Delete (confirmation).
- Click on a preset: if the timer is IDLE, set the configured duration to the preset and start in the
  same action (one click). In any other state the preset buttons are disabled, tooltip "Reset the
  timer to use a favorite".
- `PresetEditDialog`: label, duration (hours, minutes, seconds), real-time validation, `is_dirty`.
- Uses the nine generic operations through `TimerPresetReaderPort` / `TimerPresetWriterPort`.

## Hourly chime

- `HourlyChime` singleton entity: `enabled`, `sound`, `volume`, `start_hour`, `end_hour`.
- Rings once at each full hour `H:00` local time when `enabled` and
  `start_hour <= H <= end_hour` (0-23, `start_hour <= end_hour`; 0-23 means all day).
- `ChimeService` (application, registered on `AppTicker`): chimes if the local time is within the
  first `chime.trigger_window_seconds` of the hour and this (date, hour) has not chimed yet. An hour
  missed during sleep or a busy period is not chimed late.
- Never chimes while the timer is RINGING; uses its own player instance (`chime`) so it never cuts
  an alarm; plays once.
- UI: checkbox "Chime every hour" and a "..." button opening `ChimeSettingsDialog` (sound, volume,
  preview, active hours). Phase 4 exposes the same fields in the settings page.

## Deliverables

- Domain (`domain/timer/`): `timer_preset.py`, `timer_presets_collection.py`,
  `timer_preset_rules.py`, `hourly_chime.py`, `hourly_chime_rules.py`. Auto labels are formatted by
  the presentation layer, not the domain.
- Application: preset reader/writer ports, `timer/preset_commands.py` (`create`, `update`, `delete`,
  `move`, `apply_and_start`), `timer/preset_queries.py`, chime reader/writer ports,
  `timer/chime_service.py`, `timer/chime_commands.py`.
- Infrastructure: schemas, mappers, stores (generic collection store for presets), seed logic,
  third `QtSoundPlayer` instance.
- Presentation: `presets_presenter.py`, `presets_snapshot.py`, `preset_edit_presenter.py`,
  `preset_edit_form.py`, `chime_presenter.py`, `chime_settings_form.py`,
  `presentation/common/duration_label_formatter.py` (catalog-based "15 min", "1 h 30").
- UI: `ui/panels/presets_panel.py`, `ui/panels/special_options_panel.py`,
  `ui/panels/preset_edit_form_panel.py`, `ui/panels/chime_settings_form_panel.py`,
  `ui/windows/preset_edit_dialog.py`, `ui/windows/chime_settings_dialog.py`,
  `ui/widgets/flow_layout.py` (wrapping layout), reuse of phase 2 widgets.

New `ActionIdEnum` values: `PRESET_APPLY`, `PRESET_ADD`, `PRESET_EDIT`, `PRESET_DELETE`,
`PRESET_MOVE_EARLIER`, `PRESET_MOVE_LATER`, `PRESET_EDIT_SAVE`, `PRESET_EDIT_CANCEL`,
`CHIME_TOGGLE`, `CHIME_EDIT`, `CHIME_EDIT_SAVE`, `CHIME_EDIT_CANCEL`, `CHIME_PREVIEW`.
New `RenderSectionEnum` values: `PRESETS`, `PRESET_EDIT`, `SPECIAL_OPTIONS`, `CHIME_EDIT`.

`PresetsPresenter` subscribes to `TimerChangedEvent` so preset buttons follow the timer state.

## File format (sections added)

```toml
[[timer_presets]]
id = '019a5c20-1111-7aaa-8bbb-1c2d3e4f5a6b'
created_at = '2026-11-06T16:40:00Z'
updated_at = '2026-11-06T16:40:00Z'
label = ''
duration_seconds = 900
position = 0

[hourly_chime]
id = '019a5c20-2222-7ccc-8ddd-2d3e4f5a6b7c'
created_at = '2026-11-06T16:40:00Z'
updated_at = '2026-11-06T16:40:00Z'
enabled = false
sound = { kind = 1, value = 'chime' }
volume = 60
start_hour = 8
end_hour = 20
```

## `concentrator.ini` (new keys)

```ini
[timer]
default_presets_minutes = 15, 30, 45
max_presets = 12

[chime]
default_enabled = false
default_sound = chime
default_volume = 60
default_start_hour = 8
default_end_hour = 20
trigger_window_seconds = 59
```

Asset to provide: `assets/sounds/chime.mp3`.

## Error codes

| Code | Name |
|---|---|
| 4101 | `PRESET_DURATION_DUPLICATE` |
| 4102 | `PRESET_LABEL_TOO_LONG` |
| 4103 | `PRESET_LIMIT_REACHED` |
| 4201 | `CHIME_HOUR_OUT_OF_RANGE` |
| 4202 | `CHIME_HOURS_REVERSED` |

Chime volume reuses `TIMER_VOLUME_OUT_OF_RANGE` (same `Volume` value object).

## Tests

- Collection: ordering, move at both ends, limit, duplicate duration, seed from ini values.
- `apply_and_start`: IDLE -> duration set and RUNNING in one call; any other state ->
  `TIMER_TRANSITION_INVALID`, configuration unchanged.
- `ChimeService` with `FakeClock`: chimes at 09:00:00 and at 09:00:40 (late tick) but not twice;
  not at 08:59; not outside hours; not while RINGING; missed hour after a jump from 09:58 to 10:03
  is not chimed; DST transitions do not double-chime.
- Presenters: preset buttons enabled only in IDLE; labels in both languages; chime form validation.
- UI smoke: presets panel renders N buttons and emits the preset id with the action.

## Acceptance criteria

- [ ] Fresh file: favorites 15, 30, 45 min appear; one click on "15 min" starts a 15:00 countdown.
- [ ] Add, edit, reorder, delete favorites; changes survive a restart.
- [ ] Favorites are disabled while the timer runs, is paused or rings.
- [ ] Hourly chime enabled with hours covering the current hour: it chimes once at the next full
      hour, not during an alarm, not outside the hours.
- [ ] Every new text switches language live.

## Manual test script

1. Use each default favorite; add "Pomodoro" 25 min; move it first; delete "45 min"; restart the app.
2. Enable the chime; set the Windows clock or wait for the next hour (tip: set hours to the current
   one); start a timer that rings at the full hour and check that the chime is skipped.

## Review gate questions

1. One click on a favorite sets and starts the timer: confirm (alternative: set only).
2. Active hours for the chime (default 08-20): keep, or chime all day?
