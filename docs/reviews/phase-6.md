# Phase 6 review report

First issue (2026-11-11). Branch `phase-6-todo-advanced`, 11 commits on top of `main` (`c901e8c`). The
branch is not pushed. The owner decisions of the plan review are in ADR-042; the items "decided during the
build" there are to be approved.

## Summary

- **Repeating tasks.** A Repeat section in the task dialog (every N days, weeks, months or years, weekdays,
  ends never / on a date / after N times) with the series in words and the next 4 dates. Completing an
  occurrence moves the task to its next date, skipping the past dates (owner decision), until the series
  ends.
- **History tab.** The details pane has Details and History tabs; History lists the events newest first,
  occurrences included.
- **Filter bar.** Due date filter, Recurring only, search (case and accents ignored, every line), scope
  This list / All lists with a List column, and the counter "12 of 87 tasks"; all restored at start.
- **Bulk due date.** Set due date... and Clear due date on the selection, all or nothing.
- **Links.** A line holding only a web address or a path is a link (owner decision): underlined in the
  details and the table, listed by Open link, opened unchecked. The table of 1,000 tasks builds in 22 ms.

## Spec coverage

| Requirement | Status | Notes |
|---|---|---|
| `Recurrence`, enums, `RecurrenceCalculator`, `RecurrenceRules` | done | bounded weekly search; clamped months; 29 February |
| Completing a recurring task | deviated (owner) | late occurrence jumps to today or later; skipped dates in the event |
| Repeat section with summary and preview | done (owner) | 4 dates (`todo.recurrence_preview_count`), as the acceptance criterion lists |
| History tab, `OCCURRENCE_COMPLETED` (10), `RECURRENCE_CHANGED` (11) | done | plus "a deleted list" and "Event not recognized" |
| Due filter, toggles, Recurring only | done | Overdue = open tasks with the table rule |
| Search, debounce, scope, counter, persisted | done (owner) | scope applies to the whole table; search text restored |
| Columns Repeat, Occurrences, Links | done | plus List (All lists only); these four do not sort |
| Bulk Set / Clear due date | done (owner) | date only, times kept; Clear off for a repeating task |
| `LinkTarget`, `LinkDetector`, normalization | deviated (owner) | whole-line links only (ADR-014 amendment) |
| Links in details, table and context menu | done | `QTextBrowser` with escaped text; `LinkTextDelegate`; Open link submenu |
| `LinkOpenerPort.open`, refusal logged without the link | done | |
| Deliverables | deviated (build) | `TaskScheduleCommands` instead of new `TaskCommands` methods; no `set_recurrence`; date dialog in `ui/support` through `DialogPort.ask_date` |
| `ActionIdEnum` and `RenderSectionEnum` values | done | 83 to 89, 21 and 22 |
| File format | done | spec example written as is; phase 5 files unchanged |
| Ini keys | done (owner, build) | plus `recurrence_preview_count`; `url_schemes = http, https`; eight column widths |
| Error codes 5201 to 5207 | done | plus 5208 `RECURRENCE_END_DATE_MISSING`; each produced by a test |
| Tests listed in the spec | done | see the test files under `tests/*/todo`, `test_link_*`, `test_task_filter*` |

## Deviations and decisions

Owner decisions (plan review): ADR-042 items 1 to 9. Decided during the build, to approve: ADR-042 items 1
to 15. The main ones:

1. **`TaskScheduleCommands`** for the bulk due date (ten use cases per class); the recurrence is stored
   through `update` with the rest of the task, no `set_recurrence`.
2. **`RECURRENCE_END_DATE_MISSING` (5208)** for a hand-edited file whose series ends "on a date" without
   a date.
3. **`TaskOccurrenceCompletedEvent`** for phase 7; the overdue rule moves to the domain (`due_marks.py`).
4. **Table header key `todo_header_v2`**: the stored header of phase 5 has five columns, so the column
   layout starts from the ini defaults once.
5. **Date dialog** in `ui/support/date_prompt_dialog.py` behind `DialogPort.ask_date`, not
   `ui/windows/bulk_due_date_dialog.py` (`ui.support` cannot import `ui.windows`).
6. **Open link** is a submenu of the table context menu only, not a toolbar button.
7. **Link cache:** the row formatter keeps the links per task text (the table went from 31 to 22 ms for
   1,000 tasks, as in phase 5).

`AGENTS.md` (sections 5.1, 6.1 and 7.4), the phase 6 spec (owner answers written in), ADR-014 (amendment)
and `USAGE.md` are updated.

## Gates

`uv run python scripts/check.py` on the last commit:

| Gate | Result |
|---|---|
| `ruff format` | passed |
| `ruff check` | passed |
| `basedpyright` (strict) | 0 errors, 0 warnings, 0 notes |
| `furryp check concentrator` | all checks passed |
| `pytest --cov` | 2910 passed, 0 failed, 0 skipped |
| `coverage_gate.py` | passed |

`uv run python scripts/build.py` succeeded and the frozen self-check passed; its round trip now includes a
weekly task with one occurrence done.

## Coverage per layer

Branch coverage (statements + branches):

| Layer | Coverage | Threshold |
|---|---|---|
| domain | 99.79 % | 90 % |
| application | 99.43 % | 85 % |
| presentation | 99.08 % | 80 % |
| infrastructure | 98.34 % | — |
| ui | 97.15 % | — |
| bootstrap | 91.80 % | — |
| overall | 98.24 % | 75 % |

Not covered (new code): the painting of a link while its row is selected, and the hand cursor when the
mouse leaves a link (both need a real mouse over a shown table).

## Manual test script

I cannot see the GUI from here, so none of these steps has been run yet. Please run them on Windows 11
at 100 % and 150 % scaling. Steps 1 to 4 are the spec script.

1. **Repeating tasks.**
   - New task "Backup", due on a Friday, tick **Repeat**: weekly, the Friday ticked. Tick Monday too,
     interval 2, **Ends** After 4 times. The summary reads "Every 2 weeks on Monday and Friday, 4 times"
     and 4 next dates follow. Save.
   - Tick it 4 times (check box): each time it stays open and moves to the next date; the Times column
     reads `1 / 4`, `2 / 4`... After the 4th, it is done. The **History** tab shows each occurrence with
     its due and next dates.
   - New task due 31 October, monthly: the preview shows 30 Nov, 31 Dec, 31 Jan, 28 Feb.
   - Give a weekly task a due date 3 weeks ago, then tick it: it moves to the next date that is today or
     later, and History says how many past dates were skipped.
2. **Links.** Create a task with these lines: a folder on its own line `C:\Users\<you>\Documents`, a
   sentence holding a URL (`See https://example.org`), a URL alone `https://example.org`, a UNC path
   `\\<a machine>\<a share>`, `C:/Windows/notepad.exe`, and `Z:/does/not/exist`.
   - After Save, the paths read with `/`. The sentence stays plain text; the other lines are underlined
     in the Details tab.
   - Click each one: Explorer opens the folder, the browser the URL, Notepad starts; the missing path
     does nothing visible and the journal shows a WARNING without the path.
   - Put a URL on the first line of another task: it is underlined in the table, the cursor becomes a
     hand over it, a click opens it; a click elsewhere on the row only selects it.
   - Right-click the task, **Open link**: its links are listed (10 at most).
3. **Search and filters.** In a list holding "État des lieux", type `etat` in the search box: the task
   stays, the others go, the counter reads "1 of N tasks". Switch to **All lists**: the List column
   appears with tasks of other lists. Choose **Overdue**; tick **Recurring only**. Restart: the filters,
   the search and the scope come back. **Reset layout** clears them.
4. **Bulk due date.** Select 20 tasks, **Set due date...**: pick a date, **Set**: all 20 have it, each
   keeping its time. **Clear due date** removes them. Select a repeating task too: Clear due date is
   greyed and its tooltip says why. Put the dates back by hand.
5. **Columns.** The table starts with the ini column widths once (new header key); resize, restart, the
   widths come back.
6. **Language.** Switch FRA/ENG: summary, preview, history lines, filters, counter, Open link and the date
   dialog follow at once.
7. **Data file.** Open the file in a text editor: the weekly task has
   `recurrence = { frequency = 2, ... }` and `occurrences_done`; one-off tasks have neither. Write
   `frequency = 9` and reopen: the recovery dialog reports the recurrence frequency.
8. **Dialogs.** The date dialog darkens the window, opens centered and cannot leave it.
9. **Built app.** Build with `uv run python scripts/build.py` and repeat steps 1 and 2 with
   `dist\Concentrator\Concentrator.exe`.

## Open questions

1. **Times column header** reads "Times" ("Fois"); the spec says "Occurrences". Default: keep the short
   header, the details pane says "Times done".
2. **A click on a link in the table** also selects the row. Default: keep it (one click shows the task and
   opens its link).
3. **The table underlines only the links of the first line** (the column shows the first line only).
   Default: keep it; the other links are in the Details tab and the Open link menu.
4. **Reopen after the last occurrence** reopens the task with its last due date and the count kept; the
   next completion ends it again. Default: keep it (reset the count by editing the repetition).
