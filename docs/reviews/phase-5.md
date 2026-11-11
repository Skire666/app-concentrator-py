# Phase 5 review report

First issue (2026-11-10). Branch `phase-5-todo-core`, 7 commits on top of `main` (`e43ebce`, which holds
`phase-4-accepted` and the owner's spec notes). The branch is not pushed. The owner decisions of the plan
review are in ADR-041; the items "decided during the build" there are to be approved.

## Summary

- **Zone 1 is the TODO manager.** List tabs (priority mark, open count, description), a toolbar, a quick
  add field, the task table and a details pane under it, in a vertical splitter.
- **Lists:** create, edit, move within a priority, delete (with their tasks, after a confirmation that
  gives their number). A file without any list gets an Inbox named in the current language.
- **Tasks:** quick add with Enter, a dialog for the multi-line text, the list and an optional due date
  and time. Done, Reopen, Archive, Unarchive, Duplicate, Move to list and Delete apply to a multi-row
  selection. The check box column (and Space) completes or reopens a task without opening it.
- **Table:** sorting on every column, overdue and today marks, Show done / Show archived. Every view
  setting is a layout key, restored at start and reset by "Reset layout". Building the table for 1,000
  tasks takes about 21 ms (the budget is 100 ms).
- **Data file:** `[[task_lists]]` and `[[tasks]]` with a capped history (10 events). A task whose list
  does not exist makes the file invalid. `bench_storage.py --seed-tasks N --into FILE` fills a copy for
  the manual test.

## Spec coverage

| Requirement | Status | Notes |
|---|---|---|
| Domain types, enums, collections, rules, transition table | done | plus `TaskSortKeyEnum`, `TaskDraft`, `TodoLimits` |
| History capped, `CREATED` kept | done (owner) | 10 events; the `COPIED_FROM` event of a duplicate is kept too; longer histories are shortened on read |
| Inbox when the file has no list; last list not deletable; non-empty list needs confirmation | done | the confirmation deletes the tasks (owner decision) |
| Ports with the nine operations | deviated (build) | plus `update_many` and `delete_many` (one write, all or nothing) |
| `TaskListCommands`, `TaskCommands`, bulk all or nothing | done | state actions take the tasks of the selection they fit (presenter) |
| `TodoQueries`, events | done | `ListOverview` also counts every task (delete question) |
| Tabs, table, details, edit forms and presenters | done | plus `TodoToolbarPresenter`, `QuickAddPresenter`, `TaskActions`, `TodoView`, `TodoRefresher` |
| Plural confirmations | done | "Delete 3 tasks?" asked even for one task (owner decision) |
| View preferences | deviated (build) | layout keys `layout/todo/*` (ADR-040); "details visible" is the collapsed splitter |
| UI panels and dialogs, keyboard, context menus, header persisted | done | keys read by an event filter; Ctrl+N works while the table has the focus |
| New `ActionIdEnum` (59 to 82) and `RenderSectionEnum` (14 to 19) | deviated (build) | plus `QUICK_ADD` (20) |
| File format and load rule (`TASK_LIST_NOT_FOUND`) | done | golden test: the spec example is written byte for byte |
| `concentrator.ini` keys | deviated (owner, build) | `max_history_events = 10`; plus the default sort, table share and column widths |
| Error codes 5001 to 5005 and 5101 to 5107 | done | each produced by a test, messages in both catalogs |
| Tests listed in the spec | done | see below; the 1,000-task performance test has the `slow` marker |

## Deviations and decisions

Owner decisions (plan review): ADR-041 items 1 to 7. Decided during the build, to approve: ADR-041
items 1 to 15. The main ones:

1. **Bulk writes:** `update_many` and `delete_many` on the task and list writers (`AGENTS.md` section
   6.2 now names them).
2. **Shortened histories on read:** lowering `max_history_events` shortens histories without making the
   file unusable.
3. **Mixed selections:** each state button acts on the tasks it fits; Space completes the open ones, or
   reopens the done ones when none is open.
4. **Layout keys** for the current list, the sort and the two toggles, plus the table header and the
   table / details splitter.
5. **Table model:** check boxes and a sort indicator in the shared model; changed rows are updated in
   place, so the scroll position stays when a task is ticked. The journal model test was adapted.
6. **Quick add field never disabled** (it keeps the focus between tasks typed in a row), found while
   reviewing my own work and fixed in its own commit with a test.
7. **Heartbeat** moved to `bootstrap/heartbeat.py`, because `bootstrap/shell.py` reached its size limit.

## Gates

`uv run python scripts/check.py` on the last commit:

| Gate | Result |
|---|---|
| `ruff format` | passed |
| `ruff check` | passed |
| `basedpyright` (strict) | 0 errors, 0 warnings, 0 notes |
| `furryp check concentrator` | all checks passed |
| `pytest --cov` | 2528 passed, 0 failed, 0 skipped |
| `coverage_gate.py` | passed |

I also ran `uv run python scripts/build.py`: the build succeeded and the frozen self-check passed. The
self-check round trip now includes a list and a completed task with a due date and time.

## Coverage per layer

Branch coverage (statements + branches):

| Layer | Coverage | Threshold |
|---|---|---|
| domain | 100.00 % | 90 % |
| application | 99.38 % | 85 % |
| presentation | 99.06 % | 80 % |
| infrastructure | 98.35 % | — |
| ui | 98.52 % | — |
| bootstrap | 91.45 % | — |
| overall | 98.51 % | 75 % |

Not covered (new code): a few writer failures that the rules make impossible (a list deleted between
the check and the write), and some test-only properties of the panels.

## Manual test script

I cannot see the GUI from here, so none of these steps has been run yet. Please run them on Windows 11
at 100 % and 150 % scaling. Steps 1 to 5 are the spec script.

1. **Lists.** Open a phase 4 data file: an **Inbox** tab appears.
   - With **+**, create Work (High), Home (Normal) and Ideas (Low). Check the order: Work, then Inbox
     and Home (Normal), then Ideas.
   - Right-click Home, **Move earlier**: Home goes before Inbox. Move earlier is disabled on the first
     list of a priority.
   - Right-click Inbox, **Edit list...**, give it the High priority: it moves after Work.
   - Create a list named `work`: "A list with this name already exists." under the name.
2. **Tasks.** In Work, type 5 tasks in **Add a task...** and press Enter after each one. The field stays
   focused and empties every time; the new task is selected at the top.
   - Double-click one task and give it 3 lines. Tick **Due date** and pick yesterday: the row shows
     `(+2 lines)` and is bold and highlighted (overdue).
   - Set another task to today, 1 minute from now: it is bold. Wait for that minute: it becomes
     highlighted.
   - Change a text, then press Escape: "Discard the changes?". **Keep editing** keeps the dialog open,
     **Discard** closes it.
3. **Selection.** Select 3 tasks (Ctrl+click), click **Done**: they are ticked and greyed.
   - Untick **Show done**: they disappear. Tick **Show archived**, select a task, **Archive**, then
     **Unarchive** it.
   - Tick and untick a check box: the task is done, then open again, and no dialog opens.
   - Select a done and an open task: Done and Reopen are both enabled. **Reopen** reopens only the done
     one.
   - **Move to list > Home**: the tasks leave Work. **Delete...** (or Del): "Delete 2 tasks?".
4. **Layout.** Resize and reorder the columns, sort by **Due** (click twice for descending), drag the
   bar above the details, choose the Home tab, then restart. Everything comes back: tab, sort, columns,
   splitter, toggles.
   - **Reset layout** (Settings) brings the defaults back at once: Created, newest first, done shown.
5. **1,000 tasks.** Copy your data file, then run
   `uv run python scripts/bench_storage.py --seed-tasks 1000 --into <copy>`. Open the copy with **Use
   another file...**.
   - Scrolling, selecting with Shift+click, sorting and ticking a task at the bottom of the table stay
     fluid.
   - After ticking a task, the table keeps its scroll position.
6. **Delete a list.** Right-click a list that holds tasks, **Delete list...**: the question gives the
   number of tasks. After **Delete**, the tasks are gone. The last list cannot be deleted (greyed).
7. **Language.** Switch FRA/ENG: tabs, headers, buttons, dates (`2026-11-10` and `10/11/2026`), the
   dialogs and the confirmations follow at once.
8. **Data file.** Open the data file in a text editor: lists in tab order, tasks with `text = [...]`,
   `due_date = '...'`, `due_time = 'HH:MM'` and `history = [...]` (10 events at most). Change a task's
   `list_id` to an unknown id and reopen: the recovery dialog reports the task's list.
9. **Dialogs.** The task and list dialogs darken the window, open centered and cannot leave it.
10. **Built app.** Build with `uv run python scripts/build.py` and repeat steps 2 and 3 with
    `dist\Concentrator\Concentrator.exe`.

## Open questions

1. **Ctrl+N** works only while the table has the focus, as the spec places it. Should it also work from
   the quick add field and the toolbar? Default: extend it to the whole zone 1 (a small change once you
   answer).
2. **Priority marks** on the tabs: `‼` urgent, `↑` high, none for normal, `↓` low (catalog texts, so
   easy to change). Default: keep them.
3. **New due time** starts at 09:00 when **Time** is ticked. Default: keep it; an ini key otherwise.
4. **Overdue colour** is the highlight colour of the Windows palette (blue by default), as for the
   journal errors, since colours are never hard-coded. Default: keep it until the themes phase.
5. **Duplicate** of a done task gives an open copy. Default: keep it.

## Changes after the review (2026-11-10)

The owner approved the build items of ADR-041 and the defaults of the open questions ("Suit tes
recommandations"; ADR-041 amendment).

1. **Ctrl+N anywhere in zone 1** (question 1): it now opens the task dialog from the tabs, the toolbar,
   the quick add field, the table and the details pane, not only from the table.
2. Questions 2 to 5 keep what was built: priority marks, 09:00 proposed time, palette colour for overdue
   tasks, open copy of a duplicated done task.

Manual check to add: with the focus in **Add a task...**, press Ctrl+N: the task dialog opens on the
current list. On the Journal or Settings page, Ctrl+N does nothing.

## Code review (2026-11-11)

A code review of the phase found 8 defects (two medium: a bulk change slowed down with the square of the
number of tasks, and a tab click ignored during the cooldown left the tab bar out of step). All are fixed
in `7560ab3`, each starting with a failing test; see `docs/reviews/phase-5-code-review.md` for the
findings and the six manual checks to add.
