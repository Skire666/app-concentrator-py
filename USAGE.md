# Using Concentrator

Phase 1 adds your data file: Concentrator now remembers your settings (for now, the interface
language) in a file you choose. The timer, the TODO lists and the focus queue arrive in the next
phases.

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

Closing the window saves pending changes first. If that fails, you choose **Quit without saving** or
**Retry**; Retry keeps Concentrator open and it keeps trying. When Windows logs off or shuts down,
pending changes are saved without asking; if the logoff is cancelled, Concentrator goes on saving
normally.

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

## The window

- **Module bar** (left, full height): **Focus**, **Journal** and **Settings** switch the page. The
  button of the visible page is highlighted.
- **Focus** page: zone 1 (TODO lists, left) and zone 2 (timer, focus queue and favorites, right),
  separated by a splitter you can drag. Both zones show a "coming soon" text for now.
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
| `concentrator.toml` | chosen at first launch (default `%APPDATA%\Concentrator\`) | Your data: settings now, timer favorites, lists and tasks later. |
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
