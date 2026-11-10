# Using Concentrator

Concentrator keeps your TODO lists and your settings in a data file you choose, and its countdown timer
rings with an MP3 alarm, even when the window is in the background. Favorites start the timer in one
click, and an hourly chime can mark each full hour. The journal shows what Concentrator logs, and the
settings page gathers your settings and the data file commands. Recurring tasks, search and clickable
links, then the focus queue, arrive in the next phases.

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

Closing the window first asks **Do you want to quit Concentrator?** (or, with unsaved changes on the
Settings page, **Save and quit**, **Quit without saving** or **Cancel**); Escape or **Cancel** keeps it
open. Concentrator then saves pending
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

## TODO lists

Zone 1 of the Focus page (left) is the TODO manager: your lists as tabs, a toolbar, a quick add field, the
tasks of the current list in a table and, under it, the details of the selected task.

### Lists

- Each list is a tab: its name, a mark for its priority (`‼` urgent, `↑` high, none for normal, `↓` low)
  and the number of open tasks. The tooltip shows the priority and the description; the description of
  the current list is also shown under the tabs.
- Tabs show the most urgent lists first, then, within a priority, the order you chose.
- **+** creates a list: name (at most 80 characters, unique without regard to case: `Work` and `work`
  are the same name), description (several lines) and priority (Normal by default,
  `default_list_priority` in `concentrator.ini`).
- **Right-click a tab** for **Edit list...**, **Move earlier**, **Move later** (only among the lists of
  the same priority; a list whose priority changes goes after the others of its new priority) and
  **Delete list...**. Deleting asks first; a list that still holds tasks is deleted with its tasks (the
  question gives their number). The last list cannot be deleted.
- A data file without any list gets one named **Inbox** (**Boîte de réception** in French), in the
  language shown when the file is opened. It is a list like any other: rename it if you want.

### Tasks

- **Quick add**: type in the **Add a task...** field above the table and press Enter: the task is added
  to the current list and selected, and the field empties so that you can type the next one. An empty
  field does nothing; a text too long shows why under the field.
- **New...** (or Ctrl+N anywhere in zone 1) opens the task dialog: the text (several lines; the first line is
  the title shown in the table, at most 5000 characters in all), the list, and optionally a due date
  (tick **Due date**, then pick it in the calendar) and a due time (tick **Time**; only with a date).
- **Edit...**, a double click or Enter on a task opens the same dialog. **Save** is enabled once
  something changed. **Cancel**, Escape or the close button ask **Discard the changes?** when you
  changed something.
- **Done** marks the selected open tasks done; **Reopen** reopens the selected done tasks; **Archive**
  puts the selected tasks aside; **Unarchive** brings them back (done if they were done, open
  otherwise). With a mixed selection, each button acts on the tasks it fits (Reopen only reopens the
  done ones).
- The **check box** of a row (or Space) marks the task done or reopens it without opening it. Archived
  tasks have a greyed check box.
- **Duplicate** copies the selected task as a new open task (its history starts again). **Move to list**
  moves the selected tasks to another list. **Delete...** (or Del) always asks first, with the number
  of tasks.
- Select several tasks with Ctrl+click or Shift+click; the toolbar buttons and the context menu
  (right-click in the table) follow the selection.

### Table

- Columns: done check box, task (first line, with `(+2 lines)` when the text has more), due date and
  time, creation and change dates.
- A task due today is bold; an overdue task (date past, or today with its time passed) is bold and
  highlighted. Done and archived tasks are greyed and never marked overdue.
- Click a column header to sort by it; click again to reverse the order. Tasks without a due date stay
  at the end when sorting by due date. New data files sort by creation date, newest first
  (`default_sort` and `default_sort_descending` in `concentrator.ini`).
- **Show done** and **Show archived** show or hide those tasks (done shown, archived hidden at first).
- Drag the headers to reorder or resize the columns, and the bar between the table and the details to
  resize them (drag it down to hide the details).
- The current list, the sort, the two toggles, the columns and the details size are restored at the
  next start; **Reset layout** on the Settings page brings the defaults back.
- The details pane shows the full text, list, due date, state and dates of the selected task.

### History

Each task keeps a short history (creation, text and due date changes, completions, reopenings,
archiving, moves, copies): the last 10 events, the creation always kept (`max_history_events` in
`concentrator.ini`). It is stored in the data file and shown in a later phase.

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
  front), the taskbar button flashes until you come back (unless you turned this off on the Settings
  page). While the Journal or Settings page is shown,
  the **Focus** button of the module bar is highlighted. Concentrator shows nothing in the notification
  area next to the clock: no icon and no Windows notification.
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
  value is valid. **Cancel**, Escape or the close button close the dialog at once and discard your
  changes, without asking.
- While a countdown runs or is paused, saving a new duration replaces it: the countdown starts again at
  once with the new duration. A new sound or volume applies at the next ringing and leaves the
  countdown alone; the dialog says so. While the dialog is open, the timer buttons are behind it: close the
  dialog to stop a ringing alarm (the automatic stop still applies).
- If a chosen MP3 file is moved or deleted, the alarm plays the default sound instead and the journal
  records an error (the Journal button shows it); if no sound can be played at all, Windows beeps. The dialog shows the missing file under
  **Sound**, and you can still save the other settings.
- The built-in sounds are **Alarm** (the default), **Beep**, **Chime**, **Notification** and **Soft
  tone**. A data file that names a built-in sound of an older version plays the default sound until
  you choose another one.

## Favorites

The **Favorites** block, in the lower part of zone 2, shows one button per saved duration (15, 30 and
45 minutes in a new data file), then **Add...**. The buttons wrap onto several lines when zone 2 is
narrow.

- **One click starts the timer**: the favorite's duration becomes the timer duration (kept for the
  next starts too) and the countdown starts. The favorites stay clickable at all times: while a
  countdown runs, is paused or rings, a click stops it (and the alarm) and starts the favorite instead.
- A favorite shows its label, or its duration when the label is empty (`15 min`, `1 h 30`,
  `1 min 30 s`).
- **Add...** opens an empty dialog (no label, 00:00:00): type a label if you want one (at most 40
  characters, `max_preset_label_length` in `concentrator.ini`; the characters `<` `>` `!` `/` `\` are
  refused), set the duration and **Save**. Two favorites cannot have the same duration. **Add...** is
  disabled once you have 12 favorites (`max_presets`). A new favorite goes after the others.
- **Right-click a favorite** for **Edit...** and **Delete...** (after a confirmation).
- As in the timer dialog, errors show under the field while you type, and **Cancel**, Escape or the
  close button close the dialog without asking.
- If you delete every favorite, none comes back by itself; the 15/30/45 favorites are created only in
  a data file that has no favorites section at all.
- If you edit the data file by hand, a favorite that does not work (wrong value, same duration as
  another, more than 12) is ignored and the log says so; a label that breaks a rule is replaced by the
  automatic label. The rest of the file opens normally, and the next save writes the cleaned
  favorites.

## Hourly chime

The **Special options** block, at the bottom of zone 2, holds **Chime every hour**, the active hours
(`08:00 – 20:00` by default) and a **...** button.

- When **Chime every hour** is checked, a short sound plays once at each full hour (`09:00`,
  `10:00`...) between the first and the last chime, both included. Choose 00:00 and 23:00 to chime all
  day.
- **...** opens the chime settings: **Sound** (a built-in sound or **Choose an MP3 file...**), **Volume**
  with **Preview**, **First chime at** and **Last chime at**. The last chime cannot come before the
  first one.
- The chime plays only if Concentrator notices the new hour within its first minute
  (`trigger_window_seconds` in `concentrator.ini`, `[chime]`): an hour missed while the PC slept is
  not chimed late, and when the clocks go back in autumn the repeated hour does not chime twice.
- While the timer rings, the chime of that hour is skipped, so it never covers or cuts the alarm. A
  chime already playing when the alarm starts finishes on its own.
- A chime sound that cannot be found falls back to the built-in **Chime**, then to the Windows beep.

## The journal

The **Journal** page shows what Concentrator wrote to its log since it started, live: the newest
5000 entries (`journal_buffer_size` in `concentrator.ini`, `[logging]`). Older entries, and those of
earlier sessions, are in the log files: **Open log folder**.

- Each row shows the time (with milliseconds), the level, the source (the part of Concentrator that
  wrote it), the thread and the first line of the message; errors are bold and highlighted, debug
  entries greyed. Select a row to read the whole entry, traceback included, in the pane below; you can
  select and copy that text.
- **Debug**, **Info**, **Warning**, **Error** and **Critical** show or hide a level; each shows how many
  entries of the list have that level. **Search** keeps the entries whose message or source contains
  every word you type, whatever the case and the accents (`etat` finds `État`).
- **Follow** keeps the newest entry in view. **Pause** freezes the list while you read; the number of
  new entries hidden meanwhile shows next to it, and they appear when you click **Pause** again.
- **Copy** (or Ctrl+C) puts the selected entries in the clipboard, as lines of the log file (at most
  2000, `copy_max_rows` in `[journal]`). **Clear view** hides the entries shown so far; the log files
  are not changed.
- The level buttons and Follow are remembered; the search, Pause and Clear view are not.
- While another page is shown, an error written to the log puts a small number on the **Journal**
  button of the module bar (errors since you last opened the journal); it goes away when you open the
  journal.
- How much detail the log keeps is a setting: **Journal detail level** on the Settings page.

## Settings

The **Settings** page has five sections. **General** and **Hourly chime** are stored in your data
file: change them, then **Save** (or **Revert** to show the stored values again). Both buttons stay at
the bottom of the page and are enabled only when something changed; **Unsaved changes** shows next to
them meanwhile. Errors show under the field as you type.

- **General**: **Language** (the same as the status bar button), **Journal detail level** (Debug,
  Info, Warning, Error or Critical: entries below that level are neither written to the log files nor
  shown in the journal; it applies when you save) and **Flash the taskbar button when the timer rings
  while Concentrator is in the background**. Unchecked, a timer that rings unseen only plays its sound.
- **Hourly chime**: **Chime every hour** and the chime sound, volume (with **Preview**) and hours, as
  in the chime settings of the Focus page.
- If you leave the page, switch the data file or close Concentrator with unsaved changes, Concentrator
  asks: **Save**, **Discard** or **Cancel** (when closing: **Save and quit**, **Quit without saving** or
  **Cancel**).

The other sections act at once:

- **Data file** shows the file in use, with **Open folder**.
  - **Use another file...** saves your changes, then lets you **Open a file...** or **Create a
    file...** (with the default settings in your language). A file with a problem shows the recovery
    dialog described above; there, **Cancel** keeps the current file. The current file is kept as it
    is, and the new file is remembered for the next start. A countdown in progress goes on.
  - **Move file...** writes your data to a new file (it must not exist yet), checks that it reads back
    the same, then uses it from now on and remembers it. The previous file is kept as it was last
    saved; the message names both files.
- **Interface**: **Reset layout** brings back the default window size and position, splitter
  positions, journal columns and journal level buttons, at once. Your data file path and language are
  kept.
- **About**: the version, and where `concentrator.ini`, `ui-state.ini`, the log files and the daily
  backups are, each with **Open folder** (a folder that does not exist yet is created).

## The window

- **Module bar** (left, full height): **Focus**, **Journal** and **Settings** switch the page. The
  button of the visible page is highlighted; the Journal button shows the number of new errors.
- **Focus** page: zone 1 (TODO lists, left) and zone 2, separated by a splitter you can drag. Zone 2
  shows, from top to bottom, the timer, room for the focus queue (later), the favorites and the special
  options. Zone 1 is the TODO manager (see "TODO lists").
- **Journal** and **Settings** pages: see above.
- **Status bar** (bottom, one line): the save state on the left, the language button on the right.
  The button shows the current language (`ENG` or `FRA`); click it to switch every text between
  English and French at once. The language is saved in your data file, and the startup dialogs use the
  language you used last.
- The window size and position, the splitter positions, the task and journal columns and the TODO view
  (list, sort, toggles) are restored at the next start; **Reset layout** on the Settings page brings the defaults back.
- **Dialogs**: while a message or a question is open, the window behind it is 10 % darker
  (`dialog_overlay_opacity_percent` in `concentrator.ini`, `[ui]`). The dialog opens centered on the
  window and cannot be dragged outside it; if the window was minimized, it comes back first. The Windows
  file picker also darkens the window, but Windows places it and lets you move it anywhere. The dialogs
  shown at startup, before the window exists, open in the middle of the screen.

## Files

| File | Location | Content |
|---|---|---|
| `concentrator.toml` | chosen at first launch (default `%APPDATA%\Concentrator\`) | Your data: settings (language, journal detail level, taskbar alert), timer (`[timer]`), favorites (`[[timer_presets]]`, or `timer_presets = []` when you deleted them all), hourly chime (`[hourly_chime]`), lists (`[[task_lists]]`) and tasks (`[[tasks]]`). A task whose list does not exist makes the file unreadable (the recovery dialog explains it). A file written by an older version gets the missing sections from `concentrator.ini` at the next start. |
| `concentrator.toml.bak` | next to the data file | The version before the last save. |
| `concentrator.toml.tmp` | next to the data file | Only while saving, or after an interrupted save. |
| `*.corrupt-*`, `*.tmp.discarded-*`, `*.bak.discarded-*` | next to the data file | Files put aside by the recovery dialog; delete them when you no longer need them. |
| `backups\concentrator-YYYY-MM-DD.toml` | `%APPDATA%\Concentrator\` | One copy per day, last 7 days. |
| `concentrator.ini` | next to `Concentrator.exe` | Application constants: sizes, timings, paths, log level. Edit it with a text editor and restart; every key is documented in the file. |
| `ui-state.ini` | `%APPDATA%\Concentrator\` | Window layout, task columns, TODO view and journal level buttons, the path of your data file and the last language. **Reset layout** clears the layout only; deleting the file also forgets the data file, so the first-launch dialog asks for it again. |
| `concentrator.log` | `%LOCALAPPDATA%\Concentrator\logs\` | Technical log (rotated). Never contains the text of your tasks. |
| `faulthandler.log` | `%LOCALAPPDATA%\Concentrator\logs\` | Low-level crash dumps, normally empty. |

If `concentrator.ini` is missing or one of its keys is missing or invalid, Concentrator does not start
and shows a message naming the file and the faulty keys.
