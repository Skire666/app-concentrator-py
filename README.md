# Concentrator

A local, single-window desktop application for Windows 11 that helps you focus: a countdown timer with
alarms, one-click timer favorites, an hourly chime, a focus queue of the few tasks you work on now, and a
full TODO list manager. Everything stays on your computer, in one readable TOML file you choose.

![Focus page: TODO lists on the left; timer, focus queue, favorites and hourly chime on the right](docs/images/focus-page.png)

## Features

- **Timer**: countdown with an MP3 alarm (built-in sounds or your own file), volume, repetitions, snooze,
  automatic stop and restart; the taskbar button flashes when it rings in the background.
- **Favorites** start a saved duration in one click; the **hourly chime** marks each full hour within the
  hours you choose.
- **TODO lists** as tabs, with priorities; tasks with due dates and times, repetition (daily, weekly,
  monthly, yearly), history, filters, accent-insensitive search, bulk actions, and clickable folder paths
  and web addresses.
- **Focus queue** under the timer: the tasks you work on now, picked from your lists; completing one
  completes the task.
- **Journal** page showing the application log live; **Settings** page; English and French, switched live.
- **Safe storage**: atomic saves, a backup of the previous version, daily copies, recovery after a crash
  or a damaged file, detection of outside edits.
- Full keyboard use (Alt letters, reading-order Tab, shortcuts) and names for screen readers.

| Journal | Settings |
|---|---|
| ![Journal page](docs/images/journal-page.png) | ![Settings page](docs/images/settings-page.png) |

## Requirements

- Windows 11, 64-bit. No Python, no administrator rights, no network.
- About 105 MB of disk space for the application.

## Install

1. Download `Concentrator-<version>-win64.zip` and unzip it, for example into
   `%LOCALAPPDATA%\Programs\Concentrator`.
2. Run `Concentrator\Concentrator.exe`. Concentrator is not signed: if Windows SmartScreen shows "Windows
   protected your PC", choose **More info**, then **Run anyway**.
3. At the first start, choose where your data file goes (`%APPDATA%\Concentrator\concentrator.toml` by
   default).

Updating and removing are explained in [USAGE.md](USAGE.md#installing-updating-and-removing).

## Where your data lives

| What | Where |
|---|---|
| Your data (settings, timer, favorites, lists, tasks, focus queue) | the TOML file you chose, default `%APPDATA%\Concentrator\concentrator.toml`, with `.bak` next to it |
| Daily backups (last 7 days) | `%APPDATA%\Concentrator\backups\` |
| Window layout and the path of your data file | `%APPDATA%\Concentrator\ui-state.ini` |
| Logs (never the text of your tasks) | `%LOCALAPPDATA%\Concentrator\logs\` |
| Application constants | `concentrator.ini`, next to `Concentrator.exe` |

## Build from source

Prerequisites: Git, [uv](https://docs.astral.sh/uv/) (`winget install --id astral-sh.uv -e`), and the
`furryp` CLI on `PATH` for the quality gate.

```powershell
uv python install 3.14
uv sync
uv run concentrator                          # the application, without a console window
uv run python -m concentrator                # the same, from a terminal (debugging)
uv run python scripts/check.py               # every quality gate
uv run python scripts/build.py --release     # dist/Concentrator/ and dist/Concentrator-<version>-win64.zip
```

## Documentation

| File | Content |
|---|---|
| [USAGE.md](USAGE.md) | Every feature, the keyboard, the files, backups and recovery, `concentrator.ini` |
| [CHANGELOG.md](CHANGELOG.md) | Release notes |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Setup, gates, workflow, how to add an error code, an enum, a text, a setting |
| [AGENTS.md](AGENTS.md) | Architecture and coding rules (single source of truth) |
| [docs/decisions.md](docs/decisions.md) | Architecture decision records |
| [docs/specs/](docs/specs/) | Phase specifications |
| [docs/reviews/](docs/reviews/) | Phase review reports |

## License

[The Unlicense](LICENSE): public domain.
