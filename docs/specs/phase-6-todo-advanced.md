# Phase 6 — TODO advanced: recurrence, history, filters, search, links

Depends on: phase 5. Branch: `phase-6-todo-advanced`.

## Goal

Recurring tasks with occurrence counting, a readable history per task, due-date filters and search,
bulk editing, and clickable folder paths and URLs inside task text.

## Recurrence

`Recurrence` value object (in `Task.recurrence`, `None` for a one-off task):

| Field | Values |
|---|---|
| `frequency` | `RecurrenceFrequencyEnum`: `DAILY=1, WEEKLY=2, MONTHLY=3, YEARLY=4` |
| `interval` | every N units, 1-`todo.max_recurrence_interval` |
| `weekdays` | `WeekdayEnum` (`MONDAY=1` ... `SUNDAY=7`), required and non-empty for WEEKLY |
| `anchor_date` | first due date of the series; drives week parity, day of month and day of year |
| `end_kind` | `RecurrenceEndEnum`: `NEVER=1, ON_DATE=2, AFTER_COUNT=3` |
| `end_date` | for ON_DATE, >= current due date |
| `end_count` | for AFTER_COUNT, 1-`todo.max_recurrence_count` |

`Task.occurrences_done` counts completed occurrences. A recurring task requires a due date.

Next due date after the current one (`RecurrenceCalculator`, pure domain):
- DAILY: `due + interval` days.
- WEEKLY: first later day whose weekday is in `weekdays` and whose week (Monday-based) is a multiple
  of `interval` weeks after the anchor week. Bounded search.
- MONTHLY: same day of month as the anchor, every `interval` months, clamped to the last day of
  shorter months (anchor 31 -> 30 Apr, 28/29 Feb, 31 Mar).
- YEARLY: anchor month and day every `interval` years; 29 Feb becomes 28 Feb in non-leap years.

Completing a recurring task (from the table, the toolbar, or later the focus queue):
1. `occurrences_done += 1`; history `OCCURRENCE_COMPLETED` with `occurrence`, `due`, `next_due`.
2. If the end condition is reached (AFTER_COUNT: `occurrences_done >= end_count`; ON_DATE: next due
   after `end_date`), the task becomes DONE (`COMPLETED` event).
3. Otherwise it stays OPEN with `due_date = next due` (computed from the current due date, even if
   it is still in the past: no occurrence is skipped silently).

Editor: a "Repeat" section in `TaskEditDialog` (frequency, interval, weekday toggles, ends: never /
on date / after N occurrences) with a live summary ("Every 2 weeks on Monday and Friday, 10 times")
and the next three dates as a preview.

## History

The details pane gets two tabs: Details and History. History lists events newest first with
translated descriptions and local timestamps, e.g. "06/11/2026 17:45 - Occurrence 3 completed (due
10/11/2026, next 17/11/2026)". New event kinds: `OCCURRENCE_COMPLETED=10`, `RECURRENCE_CHANGED=11`.

## Filters and search

- Due filter (`DueFilterEnum`): All, Overdue, Today, This week, Next 7 days, With date, No date.
- Toggles kept from phase 5 (Show done, Show archived) plus Recurring only.
- Search box: case- and accent-insensitive on every line of the text (`presentation/common/
  text_search.py` from phase 4), debounced `todo.search_debounce_ms`; scope "This list" or "All
  lists" (adds a List column).
- Counter "12 of 87 tasks". Filters and scope persisted in `ui-state.ini`. Filtering and sorting
  happen in the presenter on the in-memory collection.
- New table columns: Repeat (summary, short form), Occurrences ("3 / 10" or "3"), Links (count).

## Bulk editing

New bulk actions on the selection: Set due date... / Clear due date, in addition to phase 5 state,
move and delete actions. All or nothing, one history event per task.

## Clickable paths and URLs

Principle (ADR-014): a detected path or URL is simply made clickable, like a hyperlink. It is never
checked: no existence test, no reachability test, no file-type test, no confirmation. If the target
does not exist or fails to open, the user is responsible.

- `LinkTarget` value object: `LinkKindEnum` (`URL=1, LOCAL_PATH=2, UNC_PATH=3`) and normalized
  `value` (single line, `\` replaced by `/`, drive letter upper-case, surrounding quotes removed).
- `LinkDetector` (pure domain) finds links in each text line:
  - URL: a scheme listed in `links.url_schemes` followed by `://`, up to whitespace, trailing
    `.,;:!?)]}>"'` excluded; `file:///C:/...` becomes a LOCAL_PATH.
  - Drive path on any drive letter (`C:/...`, `D:\...`, `E:/...`) and UNC (`//server/share` or
    `\\server\share`): when it starts the line (after an optional bullet `- `), the path runs to the
    end of the line, spaces included; elsewhere it runs to the next whitespace unless quoted with
    `"..."` or `<...>`.
- Normalization happens in the domain when a task is created or updated: detected paths in the text
  are rewritten with `/`, so the JSON5 file stores flat, unescaped paths and the UI shows the same.
- Display, styled as hyperlinks (underlined, link color from the palette, pointing-hand cursor):
  - details pane: `QTextBrowser` with anchors built from escaped text (`html.escape`) and
    index-based hrefs (`link:<n>`), `setOpenLinks(False)`, `anchorClicked` -> presenter;
  - task table, text column: links of the first line rendered by `LinkTextDelegate`; a click on a
    link opens it, a click elsewhere selects the row;
  - context menu "Open link" listing up to `links.max_links_in_menu` links of the task.
- Opening: `LinkOpenerPort.open(target) -> ValidationResult` hands the normalized target straight to
  `QDesktopServices.openUrl` (URLs as they are, paths through `QUrl.fromLocalFile`), exactly like a
  double-click in Explorer (an `.exe` runs, a slow network path is slow). The only outcome reported
  is Qt's own refusal: `LINK_OPEN_FAILED` logged at WARNING (no silent failure), no dialog, no
  blocking message.
- Logs record the link kind and the result, never the path or URL.

## Deliverables

- Domain: `recurrence.py`, `recurrence_frequency_enum.py`, `recurrence_end_enum.py`,
  `weekday_enum.py`, `recurrence_calculator.py`, `recurrence_rules.py`, `link_kind_enum.py`,
  `link_target.py`, `link_detector.py`; `Task` gains `recurrence`,
  `occurrences_done`, `complete_occurrence(now, today)`.
- Application: `task_commands.py` gains `set_recurrence`, `set_due_date(task_ids, date)`,
  `clear_due_date(task_ids)`; `complete` handles recurring tasks; `todo_queries.py` gains
  `TaskFilter`; `link_commands.py` (`open_link(task_id, index)`); `LinkOpenerPort.open(target)`.
- Infrastructure: `QtLinkOpener.open` (URLs via `QUrl`, paths via `QUrl.fromLocalFile`, no checks).
- Presentation: `task_filter_presenter.py`, `recurrence_form.py` (inside the task edit form),
  `recurrence_summary_formatter.py`, `task_history_formatter.py`, `link_presenter.py`.
- UI: `ui/panels/task_filter_panel.py`, `ui/panels/recurrence_form_panel.py`,
  `ui/panels/task_history_panel.py`, `ui/widgets/weekday_toggle_widget.py`,
  `ui/widgets/link_text_browser.py`, `ui/widgets/link_text_delegate.py`,
  `ui/windows/bulk_due_date_dialog.py`.

New `ActionIdEnum` values: `TODO_FILTER_DUE`, `TODO_TOGGLE_RECURRING_ONLY`, `TODO_SEARCH`,
`TODO_SEARCH_SCOPE`, `TASK_SET_DUE_DATE`, `TASK_CLEAR_DUE_DATE`, `LINK_OPEN`. New `RenderSectionEnum` values: `TODO_FILTERS`, `TODO_HISTORY`.

## File format (task fields added)

```json5
      text: ["Weekly backup", "Copy D:/Projects/Concentrator to //nas/backup/projects", "See https://example.org/backup-guide"],
      due_date: "2026-11-13",
      recurrence: {
        frequency: 2,
        interval: 1,
        weekdays: [5],
        anchor_date: "2026-11-06",
        end_kind: 3,
        end_date: null,
        end_count: 10,
      },
      occurrences_done: 1,
```

## `concentrator.ini` (new keys)

```ini
[todo]
max_recurrence_interval = 999
max_recurrence_count = 9999
search_debounce_ms = 150

[links]
url_schemes = http, https, ftp, file
max_links_in_menu = 10
```

## Error codes

| Code | Name |
|---|---|
| 5201 | `RECURRENCE_REQUIRES_DUE_DATE` |
| 5202 | `RECURRENCE_INTERVAL_OUT_OF_RANGE` |
| 5203 | `RECURRENCE_WEEKDAYS_EMPTY` |
| 5204 | `RECURRENCE_END_DATE_BEFORE_DUE` |
| 5205 | `RECURRENCE_COUNT_OUT_OF_RANGE` |
| 5206 | `RECURRENCE_FREQUENCY_UNSET` |
| 5207 | `RECURRENCE_END_KIND_UNSET` |

Link opening reuses `LINK_OPEN_FAILED` (7003, phase 4).

## Tests

- `RecurrenceCalculator` tables: daily interval 3; weekly Mon+Fri interval 2 across month and year
  boundaries; monthly anchor 31 over a full year; yearly 29 Feb over 8 years; bounded search
  terminates for every weekday set.
- Completion: AFTER_COUNT stops at N; ON_DATE stops when the next due passes the end; overdue
  occurrence keeps its sequence; history details correct.
- `LinkDetector` table: URL with trailing punctuation, URL in parentheses, whole-line path with
  spaces, inline path without spaces, quoted path, UNC both syntaxes, `file:///`, two links on one
  line, no false positive on `"ratio 3:2"` or times like `10:30`.
- Normalization: backslashes rewritten only inside detected paths; idempotent.
- Link opening with a fake opener: the normalized target reaches the opener unchanged for every
  kind; nothing touches the file system before opening (a non-existent path is opened like any
  other); an opener refusal returns `LINK_OPEN_FAILED`, logs a WARNING without the path, shows no
  dialog.
- Filters and search: every `DueFilterEnum` value with `FakeClock` (week starts Monday), accent
  folding, scope all lists, counter text in both languages.
- Bulk due date: all or nothing.
- Persistence round trip with recurrence; `UNKNOWN` frequency read from file -> rules error.

## Acceptance criteria

- [ ] A weekly task (Mon, Fri, every 2 weeks, 4 times) moves to the right dates when completed and
      becomes done after the 4th completion; History shows each occurrence.
- [ ] Monthly on the 31st shows 30 Nov, 31 Dec, 31 Jan, 28 Feb in the preview.
- [ ] Typing `C:\Users\me\Documents\My folder` on its own line stores `C:/Users/me/Documents/My folder`;
      clicking it opens Explorer there; an URL opens the default browser.
- [ ] Paths on `C:`, `D:`, `E:`, UNC paths and URLs are underlined and clickable in the details pane
      and in the table; a path that does not exist is still a link, and clicking it only adds a
      WARNING to the journal if Windows refuses it.
- [ ] Filters, search and scope combine correctly and are restored after restart.
- [ ] Set due date on 20 selected tasks in one action.

## Manual test script

1. Create the weekly and monthly examples above; complete them repeatedly; read the history.
2. Add a task with a folder path on its own line, an inline URL, a UNC path, a path to
   `C:/Windows/notepad.exe` and a path that does not exist; click each one in the details pane and
   in the table.
3. Search `etat` in a list containing "État des lieux"; switch scope to all lists; filter Overdue.
4. Select 20 tasks, Set due date; Clear due date; undo by hand.

## Review gate questions

1. Completing an overdue recurring occurrence moves to the next date after the old due date (may
   still be overdue). Keep, or jump to the first future occurrence?
2. Links only detected in the text (default), or also a dedicated "Links" field in the editor?
