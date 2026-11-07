# Using Concentrator

Concentrator keeps your settings in a data file you choose, and its countdown timer rings with an MP3
alarm, even when the window is in the background. Timer favorites, the hourly chime, the TODO lists and
the focus queue arrive in the next phases.

## Starting

- Run `Concentrator.exe` (or `uv run concentrator` from the source tree). No console window opens.
- Only one Concentrator runs per Windows user. Starting it again brings the open window to the front;
  when Windows refuses to switch windows, the taskbar button flashes instead. The second launch then
  closes by itself.
- If Concentrator cannot check whether it is already running (its lock file in
  `%LOCALAPPDATA%\Concentrator\` cannot be created), it warns you at startup and the status bar shows
  **Second launch not blocked** for the whole session. Close any other Concentrator window: two windows
  would save to the same data file. If that happens anyway, the second save is refused (see "Editing the
  data file by hand").

## First launch: choosing the data file

The first time (or when `ui-state.ini` was deleted), a dialog asks where your data file goes:

- **Use the file found at the default location**: shown only when a data file already exists at
  `%APPDATA%\Concentrator\concentrator.toml`.
- **Create at the default location**: creates `%APPDATA%\Concentrator\concentrator.toml`.
- **Create elsewhere...** or **Open existing file...**: pick a file yourself, for example on another
  drive.
- **Quit**: closes Concentrator without creating anything (closing the dialog does the same).

The chosen path is remembered in `ui-state.ini` and opened directly at the next start. If that file is
missing at a later start (an unplugged USB or network drive, for example), the same dialog explains it;
connect the drive and choose **Retry**. Concentrator never recreates a missing file by itself.

## Saving

Every change is saved automatically, half a second after you stop changing things, and at the latest
1.5 seconds after the first unsaved change (both values are in `concentrator.ini`, `[storage]`). The
status bar shows the state; hover over it to see the file path and any problem:

| Status bar | Meaning |
|---|---|
| **Saved at 17:44:03** | Everything is in the file. |
| **Unsaved changes** | A save is coming. |
| **Saving...** | The file is being written. |
| **Save failed: ... Retrying.** | The file could not be written (locked by another program, disk full...). Your changes stay in memory and Concentrator tries again every 10 seconds, and at every new change. |
| **Not saved: ...** | The file was changed outside Concentrator; you are asked what to do. |

Closing the window (its close button, or **Quit** in the notification area menu) first asks **Do you
want to quit Concentrator?**; Escape or **Cancel** keeps it open. Concentrator then saves pending
changes. If that fails, you choose **Quit without saving** or **Retry**; Retry keeps Concentrator open
and it keeps trying. When Windows logs off or shuts down, pending changes are saved without asking
anything; if the logoff is cancelled, Concentrator goes on saving normally.

Each save is safe: the new content is written to `<file>.tmp`, checked, then swapped in. If Concentrator
or Windows stops in the middle, the data file is either the old or the new complete version, never a
mix. The previous version is kept in `<file>.bak`, and the first save of each day also copies the file
to `%APPDATA%\Concentrator\backups\` as `concentrator-YYYY-MM-DD.toml` (the last 7 days are kept; other
files in that folder are never touched).

## When the data file has a problem

At startup, if the data file cannot be used, a dialog explains why (with the faulty fields, in your
language) and offers what makes sense:

- **Restore**: replace the data file with the selected version. The versions are the temporary file of
  an interrupted save and the `.bak` copy, newest first.
- **Keep the current file**: when an interrupted save left a newer version, open the data file as it is.
  The newer version is renamed `<file>.tmp.discarded-YYYYMMDD-HHMMSS`, so the question does not come
  back.
- **Start with an empty file**: the damaged file is renamed `<file>.corrupt-YYYYMMDD-HHMMSS` (never
  deleted) and a new empty file takes its place. The versions listed above are kept too: they are
  renamed `<file>.tmp.discarded-...` and `<file>.bak.discarded-...`.
- **Choose another file...**, **Retry** (when the file is locked by another program, or missing: put
  it back, then choose Retry) and **Quit**.

A file locked by another program, or written by a newer version of Concentrator, is never renamed or
overwritten.

## Editing the data file by hand

The data file is TOML so that you can read and edit it in any text editor. Texts are written between
single quotes, without any escape: `'D:/Reports/2026'` is exactly what you see. A text that contains an
apostrophe uses three single quotes on each side (`'''Voir l'arborescence'''`); in the rare case of a
text containing `'''` or an invisible control character, Concentrator writes it between double quotes
with escapes. Dates are written as text (`'2026-11-06T16:44:03Z'`, in UTC); a date typed without
quotes is accepted and written back with quotes at the next save.

The safest way is to close Concentrator first. If you edit the file while Concentrator runs,
Concentrator notices it before its next save and asks:

- **Reload the file**: your edit is loaded; the changes made in Concentrator since its last save are lost.
- **Keep Concentrator's version**: the file is overwritten; your edited version is copied to
  `<file>.bak` first (until the following save replaces that copy).

If your edit makes the file unreadable, the reload explains what is wrong (with the line and column of
a syntax error); fix the file and choose again. Comments you add (`# ...`) are not kept at the next
save.

## The timer

The timer sits at the top of zone 2 of the Focus page: large `HH:MM:SS` digits, a line under them, and
three buttons that change with the state.

| State | Line under the digits | Left | Middle | Right |
|---|---|---|---|---|
| Waiting | (empty) | Edit timer | Reset (disabled) | Start |
| Running | Ends at 17:52 | Edit timer | Reset | Pause |
| Paused | Paused | Edit timer | Reset | Resume |
| Ringing | Time is up | Restart | OK | Snooze 5 min |

- **Start** counts the configured duration down. **Pause** freezes it, **Resume** goes on, **Reset**
  stops it and shows the full duration again.
- At zero the digits show `00:00:00` and blink, and the alarm plays the chosen sound, at the chosen
  volume, the chosen number of times (or until stopped). **OK** stops it. **Restart** stops it and counts
  the full duration again. **Snooze 5 min** stops it and rings again 5 minutes later (`snooze_minutes`
  in `concentrator.ini`, `[timer]`); the line shows **Snoozed, rings at 17:57**.
- **Stop automatically after** (edit dialog): after that many seconds of ringing the alarm stops by
  itself; with **Restart the countdown after the automatic stop**, the countdown starts again at once.
- When the timer rings and no Concentrator window is active (window minimized, another application in
  front), a Windows notification appears and the taskbar button flashes until you come back. While the
  Journal or Settings page is shown, the **Focus** button of the module bar is highlighted. Windows "Do
  not disturb" may hide the notification; the sound plays anyway.
- After a click, the three timer buttons stay disabled for a tenth of a second, so the second click of
  a quick double click on **Start** does not pause the timer. A click on an enabled button always
  counts.
- A countdown in progress is not kept when Concentrator closes: the quit question reminds you of it.
  The settings below are kept in your data file.

**Edit timer** opens a dialog over the window:

- **Duration**: hours (0-99), minutes and seconds.
- **Sound**: one of the built-in sounds, or **Choose an MP3 file...** for any MP3 on any drive. The path
  is stored with `/` separators. **Preview** plays the sound once at the chosen volume; closing the
  dialog stops it.
- **Volume** (0-100 %), **Number of plays** or **Repeat until stopped**, **Stop automatically after**
  (0 = never, otherwise 5 to 3600 seconds) and **Restart the countdown after the automatic stop**.
- Errors show under the field while you type. **Save** is enabled only when something changed and every
  value is valid. **Cancel**, Escape or the close button ask before discarding your changes.
- While the timer runs, a new duration applies at the next start or reset, and a new sound at the next
  ringing; the dialog says so. While the dialog is open, the timer buttons are behind it: close the
  dialog to stop a ringing alarm (the automatic stop still applies).
- If a chosen MP3 file is moved or deleted, the alarm plays the default sound instead (and the log
  says so); if no sound can be played at all, Windows beeps. The dialog shows the missing file under
  **Sound**, and you can still save the other settings.

The notification area (next to the clock) shows the Concentrator icon while it runs. Click it, or click
a timer notification, to bring the window back; its menu has **Show Concentrator** and **Quit**.

## The window

- **Module bar** (left, full height): **Focus**, **Journal** and **Settings** switch the page. The
  button of the visible page is highlighted.
- **Focus** page: zone 1 (TODO lists, left) and zone 2 (the timer; the focus queue and favorites
  later), separated by a splitter you can drag. Zone 1 shows a "coming soon" text for now.
- **Journal** and **Settings** pages: "coming soon" texts for now.
- **Status bar** (bottom, one line): the save state on the left, the language button on the right.
  The button shows the current language (`ENG` or `FRA`); click it to switch every text between
  English and French at once. The language is saved in your data file, and the startup dialogs use the
  language you used last.
- The window size and position and the splitter position are restored at the next start.
- **Dialogs**: while a message or a question is open, the window behind it is 10 % darker
  (`dialog_overlay_opacity_percent` in `concentrator.ini`, `[ui]`). The dialog opens centered on the
  window and cannot be dragged outside it; if the window was minimized, it comes back first. The Windows
  file picker also darkens the window, but Windows places it and lets you move it anywhere. The dialogs
  shown at startup, before the window exists, open in the middle of the screen.

## Files

| File | Location | Content |
|---|---|---|
| `concentrator.toml` | chosen at first launch (default `%APPDATA%\Concentrator\`) | Your data: settings and timer (`[timer]`) now, timer favorites, lists and tasks later. A file written before the timer existed gets its `[timer]` section from `concentrator.ini` at the next start. |
| `concentrator.toml.bak` | next to the data file | The version before the last save. |
| `concentrator.toml.tmp` | next to the data file | Only while saving, or after an interrupted save. |
| `*.corrupt-*`, `*.tmp.discarded-*`, `*.bak.discarded-*` | next to the data file | Files put aside by the recovery dialog; delete them when you no longer need them. |
| `backups\concentrator-YYYY-MM-DD.toml` | `%APPDATA%\Concentrator\` | One copy per day, last 7 days. |
| `concentrator.ini` | next to `Concentrator.exe` | Application constants: sizes, timings, paths, log level. Edit it with a text editor and restart; every key is documented in the file. |
| `ui-state.ini` | `%APPDATA%\Concentrator\` | Window layout, the path of your data file and the last language. Delete it to get the default layout back; the first-launch dialog then asks for the data file again. |
| `concentrator.log` | `%LOCALAPPDATA%\Concentrator\logs\` | Technical log (rotated). Never contains the text of your tasks. |
| `faulthandler.log` | `%LOCALAPPDATA%\Concentrator\logs\` | Low-level crash dumps, normally empty. |

If `concentrator.ini` is missing or one of its keys is missing or invalid, Concentrator does not start
and shows a message naming the file and the faulty keys.
