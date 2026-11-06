# Using Concentrator

Phase 0 delivers the window shell only; the timer, the TODO lists and the focus queue arrive in the
next phases.

## Starting

- Run `Concentrator.exe` (or `uv run concentrator` from the source tree). No console window opens.
- Only one Concentrator runs per Windows user. Starting it again brings the open window to the front;
  when Windows refuses to switch windows, the taskbar button flashes instead. The second launch then
  closes by itself.
- Closing the window quits the application.

## The window

- **Module bar** (left, full height): **Focus**, **Journal** and **Settings** switch the page. The
  button of the visible page is highlighted.
- **Focus** page: zone 1 (TODO lists, left) and zone 2 (timer, focus queue and favorites, right),
  separated by a splitter you can drag. Both zones show a "coming soon" text for now.
- **Journal** and **Settings** pages: "coming soon" texts for now.
- **Status bar** (bottom, one line): the save state on the left, the language button on the right.
  The button shows the current language (`ENG` or `FRA`); click it to switch every text between
  English and French at once. The language is not remembered yet: the application starts in the
  language set in `concentrator.ini` (`[i18n] default_language`).
- The window size and position and the splitter position are restored at the next start.

## Files

| File | Location | Content |
|---|---|---|
| `concentrator.ini` | next to `Concentrator.exe` | Application constants: sizes, timings, paths, log level. Edit it with a text editor and restart; every key is documented in the file. |
| `ui-state.ini` | `%APPDATA%\Concentrator\` | Window layout. Delete it to get the default layout back. |
| `concentrator.log` | `%LOCALAPPDATA%\Concentrator\logs\` | Technical log (rotated). Never contains the text of your tasks. |
| `faulthandler.log` | `%LOCALAPPDATA%\Concentrator\logs\` | Low-level crash dumps, normally empty. |

If `concentrator.ini` is missing or one of its keys is missing or invalid, Concentrator does not start
and shows a message naming the file and the faulty keys.
