# Changelog

All notable changes to Concentrator. The format follows [Keep a Changelog](https://keepachangelog.com/),
and versions follow [Semantic Versioning](https://semver.org/). The data file has its own
`schema_version`; a release that changes it says so here.

## [1.0.0] - 2026-11-12

First release, for Windows 11 (64-bit), in English and French. Data file schema version 1.

### Timer

- Countdown with Start, Pause, Resume and Reset; large digits and the end time.
- Alarm with a built-in sound or any MP3 file, volume, number of plays or until stopped, snooze,
  automatic stop and automatic restart; the taskbar button flashes when the timer rings in the
  background.
- Favorites: saved durations that start the timer in one click (15, 30 and 45 minutes in a new file).
- Hourly chime within the hours you choose, never over a ringing alarm.

### TODO lists

- Lists as tabs with priorities and descriptions; tasks with several lines, due dates and times.
- Repetition every N days, weeks (on chosen days), months or years, until a date or for N times.
- History of each task, filters (due date, recurring only), accent-insensitive search, this list or all
  lists, sorting by any column, bulk actions (done, reopen, archive, move, set or clear the due date,
  delete).
- Folder paths, network paths and web addresses written on their own line open in one click.

### Focus queue

- The few tasks you work on now, under the timer, picked from your lists by a star, a search or a quick
  add; completing an entry completes its task.

### Application

- One readable TOML data file chosen at first launch; atomic saves with a backup of the previous version
  and daily copies; recovery after an interrupted save or a damaged file; outside edits detected before
  saving.
- Journal page with the live application log, level filters and search; Settings page with the language,
  the journal detail level, the taskbar alert, the hourly chime, the data file commands and Reset layout.
- English and French, switched live from the status bar.
- Full keyboard use: Alt letters in the dialogs, the Settings page and the module bar, reading-order Tab,
  shortcuts; accessible names for screen readers.
- One instance per Windows user; a second launch brings the window to the front.
- Startup in about 1.4 s with 1,000 tasks; saves off the interface thread.
