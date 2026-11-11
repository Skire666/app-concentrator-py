# Phase 7 review report

First issue (2026-11-11). Branch `phase-7-focus-queue`, 7 commits on top of `main` (`c683127`). The branch
is not pushed. The owner decisions of the plan review are in ADR-043; the items "decided during the build"
there are to be approved.

## Summary

- **Focus queue under the timer.** It lists queued tasks with a check box, the first line, the due badge
  (bold today, highlighted when overdue), the list name and a × button. A context menu offers Move up,
  Move down and Show in list, and Alt+Up / Alt+Down also move a row. The header shows "4 / 20".
- **Four ways in.** The star of the new Focus column of the task table, "Add to focus" in the toolbar and
  context menu, a search field over the open tasks of every list, and a quick-add field that creates the
  task in the chosen quick-add list (the tab menu sets it; Inbox by default) and queues it.
- **One model.** Every item is a real task (ADR-013). Ticking an item completes the task, or its
  occurrence for a repeating task, through `TaskCommands`. The history says "Completed, from the focus
  queue".
- **Reactions.** A task completed, archived or deleted elsewhere leaves the queue, and its history gives
  the reason (deletion aside). Reopening it does not queue it again.
- **Storage.** The `[[focus_queue]]` section is read leniently: items whose task is missing or closed are
  dropped with a warning. The self-check round trip includes one queued task.

## Spec coverage

| Requirement | Status | Notes |
|---|---|---|
| `FocusItem`, `FocusItemsCollection`, `FocusRules` | done | plus `FocusLimits`, `FocusRemovalReasonEnum`, `FocusRules.usable` for reading files |
| `ADDED_TO_FOCUS` (12), `REMOVED_FROM_FOCUS` (13), `source: "focus"` | done (owner) | no removal event after a completion made from the queue (ADR-043 owner 1) |
| Ports, `focus_commands.py` | done | `add_tasks`, `quick_add`, `remove`, `remove_tasks`, `toggle_task`, `move`, `complete` |
| `clear_done()` | not built (owner) | completed items leave at once (ADR-043 owner 2) |
| `focus_reactions.py` | done | state, occurrence and deletion events; reopening does not queue again |
| `focus_queries.py` | done | entries with list names, candidates, quick-add list |
| Picker search | deviated (build) | search runs in the presenter with `TextSearch` (ADR-043 build 5) |
| `FocusQueuePresenter` / `FocusQueueSnapshot` | done | plus `FocusTaskActions`, `FocusFeedback`, `QuickAddListChoice` |
| Panel, `focus_row_widget.py`, `task_picker_widget.py` | done | no "Clear completed" (owner 2) |
| Zone 1: Focus column, Add / Remove from focus | done | star right after the check box (ADR-043 build 7) |
| Quick-add list preference | done (owner) | chosen from the tab menu, `FOCUS_SET_QUICK_ADD_LIST` (100) |
| `ActionIdEnum`, `RenderSectionEnum` | done | 90 to 99 as listed, plus 100; `FOCUS_QUEUE` = 23; `FOCUS_CLEAR_DONE` not added |
| File format | done | spec example written as is; empty queue `focus_queue = []`; `schema_version` stays 1 |
| Ini keys | done | `[focus] max_items = 20`, `picker_max_results = 20`, ranges 1 to 100 |
| Error codes 6001 to 6004 | done | each produced by a test; 6004 is a WARNING of the lenient reading |
| Tests listed in the spec | done | `tests/unit/{domain,application,presentation}/focus`, `test_focus_persistence.py`, `tests/ui/test_focus_ui.py` |

## Deviations and decisions

Owner decisions at the plan review: ADR-043 items 1 to 7. Decided during the build, for your approval:
ADR-043 items 1 to 12. The main ones:

1. **Lenient reading.** Besides an item whose task is missing (the spec's case), items of closed tasks,
   repeated items and items beyond the capacity are also dropped with a warning. None of them makes the
   file invalid.
2. **`TaskFocusHistory`** in `application/todo` writes the focus events, so the focus feature never calls
   the task writer. These events change `updated_at`.
3. **The picker searches in the presenter**, not in `focus_queries` (the same choice as the table search in
   phase 6). Results come due date first, at most 20, and none while the field is empty.
4. **The Focus column sits after the check box.**
   - The task column becomes index 2.
   - The header layout moves to `todo_header_v3`, so the columns start once from the ini widths.
   - `default_column_widths_px` has nine values.
5. **One inline message** under the queue fields serves every focus action, including the star and "Add to
   focus" in zone 1.
6. **The task table scrolls to a selection made elsewhere** (Show in list, quick add, duplicate).
7. **Unrelated test fix (separate commit `40bd0c2`).** Your commit `c683127` set
   `todo.text_width_percent = 78` in the shipped ini, and two ini tests still expected 80. I aligned the
   tests and left the ini unchanged.

`AGENTS.md` (section 7.3, the new UI state key), ADR-043 and `USAGE.md` (new "Focus queue" section, the
table, history and window sections) are updated.

## Gates

`uv run python scripts/check.py` on the last code commit:

| Gate | Result |
|---|---|
| `ruff format` | passed |
| `ruff check` | passed |
| `basedpyright` (strict) | 0 errors, 0 warnings, 0 notes |
| `furryp check concentrator` | all checks passed |
| `pytest --cov` | 3107 passed, 0 failed, 0 skipped |
| `coverage_gate.py` | passed |

`uv run python scripts/build.py` succeeded and the frozen self-check passed.

## Coverage per layer

Branch coverage (statements + branches):

| Layer | Coverage | Threshold |
|---|---|---|
| domain | 99.81 % | 90 % |
| application | 99.07 % | 85 % |
| presentation | 99.02 % | 80 % |
| infrastructure | 98.38 % | — |
| ui | 97.96 % | — |
| bootstrap | 92.51 % | — |
| overall | 98.42 % | 75 % |

Not covered in the new code:

- the drop-down closing when the field loses its matches;
- the focus following a row moved with Alt+Up / Alt+Down after the render.

Both need a real window with the keyboard focus.

## Manual test script

The GUI cannot be inspected from here, so I have not run any of these steps. Please run them on Windows 11
at 100 % and 150 % scaling. Steps 1 to 4 are the spec script.

1. **Feeding the queue.**
   - Star 3 tasks from two lists in the table: each appears under the timer, with its list name. A full
     star ★ shows on the queued tasks. Click a star again: the task leaves the queue.
   - Type 3 letters of a 4th task in the search field: a drop-down lists matching open tasks of every list
     (not the queued ones). Click the entry: the task is queued and the field empties. Repeat and press
     Enter: the first entry is queued.
   - Type "Call the bank" in the quick-add field, then Enter. It appears in the queue and in the Inbox tab,
     or in the list chosen with right-click on a tab > "Use for focus quick add" (checked there). The hint
     of the field names that list.
2. **Leaving the queue.**
   - Tick one entry: the task is done in zone 1. Its History tab reads "Completed, from the focus queue",
     with no "Left the focus queue" line after it.
   - Archive a queued task in zone 1: it leaves the queue, and its history ends with "Left the focus
     queue: archived".
   - Delete a queued task in zone 1: it leaves the queue.
   - Reopen the done task: it does not come back.
3. **Repeating task.** Queue a weekly repeating task, then tick it. Its due date moves one week, it stays
   open in zone 1, it leaves the queue, and its history shows the occurrence "from the focus queue".
4. **Order and restart.** Reorder the queue with right-click > Move up / Move down, and with Alt+Up /
   Alt+Down on a clicked row (it keeps the focus). Restart: the order and the content come back, and so
   does the quick-add list choice.
5. **Capacity.** Set `max_items = 3` in `concentrator.ini` and restart. Queue 3 tasks; star a 4th: the
   message "The focus queue is full (3 tasks)…" shows under the fields and nothing is added. Typing in a
   field clears it. Select 2 open tasks and use **Add to focus**: same message, none added. Put back 20.
6. **Show in list.** Type a search in zone 1 that hides a queued task, then right-click the entry > Show in
   list. The task's tab opens, the search and due filter are cleared, and the task is selected and
   scrolled into view.
7. **Marks.** Queue a task due yesterday (bold, highlighted) and one due today (bold). At midnight, or
   after you change a due date, the marks follow.
8. **Columns.** The task table starts once from the ini widths, because of the new header key. The Focus
   column is narrow, after the check box, and does not sort. A double click on a star does not open the
   task.
9. **Language.** Switch FRA/ENG: the title, capacity, hints, entries, menu, star column header, toolbar
   buttons, tab menu item and history lines all follow.
10. **Data file.** In a text editor, the file has `[[focus_queue]]` entries in queue order. Change one
    `task_id` to a made-up id and reopen the file. The entry is gone, the journal shows a WARNING
    `FOCUS_TASK_MISSING`, and the next save removes the entry from the file.
11. **Built app.** Build with `uv run python scripts/build.py` and repeat steps 1 and 4 with
    `dist\Concentrator\Concentrator.exe`.

## Open questions

1. **History cap.** With 10 events kept, a task cycled through the queue now keeps fewer older events
   (added, completed). Raise `todo.max_history_events`? Default: keep 10.
2. **Search field empty.** Propose nothing until something is typed? Default: yes, as built.
3. **Show in list with "All lists".** Keep the scope, or switch back to "This list"? Default: keep the
   scope, as built.
4. **Star column position.** Right after the check box? Default: keep. The column can be dragged elsewhere,
   and "Reset layout" brings it back.
5. **Due badge in a row.** Date only (with the time when set), like the table? Default: keep.
