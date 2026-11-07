# Phase 7 — Focus queue (quick TODO in zone 2)

Depends on: phases 3 and 6. Branch: `phase-7-focus-queue`.

## Goal

Under the timer, a short temporary list of what to do now, picked from existing tasks. It is fed by
a dedicated button on every task, by a picker, or by a quick-add field. Completing an item completes
the task, and the action is recorded in the task history.

## Design decision

Every focus item references a real task. Quick-add text creates a real task (in the list chosen as
"quick-add list", by default the Inbox list) and queues it. This keeps one model, one history and one
place for completion logic (recurring tasks included).

## Domain (`domain/focus/`)

- `FocusItem` entity: `id`, `created_at`, `updated_at`, `task_id`, `position`.
- `FocusItemsCollection`: ordered by position; no duplicate `task_id`; at most `focus.max_items`;
  `with_added(...)`, `without_task(task_id)`, `moved(item_id, offset)`.
- `FocusRules`: only OPEN tasks can be queued (`FOCUS_TASK_NOT_OPEN`), no duplicate
  (`FOCUS_TASK_ALREADY_QUEUED`), capacity (`FOCUS_QUEUE_FULL`).
- New `TaskEventKindEnum` values: `ADDED_TO_FOCUS=12`, `REMOVED_FROM_FOCUS=13`. A completion made
  from the queue adds `source: "focus"` to the details of the `COMPLETED` or `OCCURRENCE_COMPLETED`
  event.

## Application

- Ports: `focus_item_reader_port.py`, `focus_item_writer_port.py`.
- `focus/focus_commands.py`: `add_tasks(task_ids)`, `quick_add(text)`, `remove(item_id)`,
  `move(item_id, offset)`, `complete(item_id)` (delegates to `TaskCommands.complete` with source
  "focus"), `clear_done()`.
- `focus/focus_reactions.py` subscribes to `TaskStateChangedEvent` and `TaskDeletedEvent`: when a
  queued task becomes DONE or ARCHIVED, has an occurrence completed, or is deleted, its item is
  removed and `REMOVED_FROM_FOCUS` (with the reason) is added to the task history when the task
  still exists. Reopening a task does not re-queue it.
- `focus/focus_queries.py`: items joined with their task (text first line, list name, due, overdue),
  picker search over OPEN tasks of all lists not yet queued (`focus.picker_max_results`).

## Presentation and UI

- `FocusQueuePresenter` / `FocusQueueSnapshot`: rows (item id, checkbox, text, list name, due badge,
  overdue flag, remove button), empty-state text, picker results, quick-add list name, capacity
  indicator "4 / 20".
- `ui/panels/focus_queue_panel.py` in zone 2 between the timer and the favorites, taking the
  remaining vertical space with its own scroll area:
  - header: title, capacity, "Clear completed" (if any are kept visible during the cooldown);
  - picker: search field with a drop-down of matching tasks (Enter or click adds);
  - quick-add field: "New task for focus..." (Enter creates and queues);
  - rows: checkbox completes, x removes from the queue (the task is untouched), context menu Move up
    / Move down / Show in list (selects the task in zone 1), keyboard Alt+Up / Alt+Down.
- Zone 1 integration: a Focus column with a star toggle in the task table (queued / not queued),
  plus "Add to focus" and "Remove from focus" toolbar and context-menu actions for the selection.
- `ui/widgets/focus_row_widget.py`, `ui/widgets/task_picker_widget.py` (line edit + `QCompleter`
  fed by the snapshot, no direct data access).

New `ActionIdEnum` values: `FOCUS_ADD_SELECTED`, `FOCUS_REMOVE_SELECTED`, `FOCUS_TOGGLE_TASK`,
`FOCUS_PICK`, `FOCUS_QUICK_ADD`, `FOCUS_COMPLETE`, `FOCUS_REMOVE`, `FOCUS_MOVE_UP`,
`FOCUS_MOVE_DOWN`, `FOCUS_SHOW_IN_LIST`, `FOCUS_CLEAR_DONE`. New `RenderSectionEnum` value:
`FOCUS_QUEUE`.

The quick-add list is a view preference (`focus/quick_add_list_id`); if it no longer exists, the
first list named like the translated "Inbox" is used, or a new Inbox list is created.

## File format (section added)

```toml
[[focus_queue]]
id = '019a5c30-cccc-7ddd-8eee-5a6b7c8d9e0f'
created_at = '2026-11-06T17:10:00Z'
updated_at = '2026-11-06T17:10:00Z'
task_id = '019a5c22-bbbb-7ccc-8ddd-4f5a6b7c8d9e'
position = 0
```

On load, an item whose `task_id` does not exist is dropped with a WARNING (`FOCUS_TASK_MISSING`)
and the next save removes it from the file.

## `concentrator.ini` (new keys)

```ini
[focus]
max_items = 20
picker_max_results = 20
```

## Error codes

| Code | Name |
|---|---|
| 6001 | `FOCUS_TASK_ALREADY_QUEUED` |
| 6002 | `FOCUS_QUEUE_FULL` |
| 6003 | `FOCUS_TASK_NOT_OPEN` |
| 6004 | `FOCUS_TASK_MISSING` (WARNING) |

## Tests

- Collection and rules: duplicates, capacity, only OPEN tasks, move at both ends.
- Commands: quick add creates the task in the quick-add list then queues it (one history event
  each); complete from the queue completes the task with `source: "focus"`; recurring task: the
  occurrence is completed and the item removed while the task stays OPEN.
- Reactions: completing, archiving or deleting a queued task from zone 1 removes the item and
  records `REMOVED_FROM_FOCUS` (except on delete); reopening does not re-queue.
- Picker: excludes queued and non-OPEN tasks, accent-insensitive, limited results.
- Presenter: rows, overdue badge, capacity text in both languages, star state in the task table.
- Persistence: round trip; dangling `task_id` dropped with a warning.
- UI smoke: queue panel renders rows; checkbox emits complete with the item id; star toggle emits
  the task id.

## Acceptance criteria

- [ ] Star a task in zone 1: it appears under the timer; un-star: it disappears.
- [ ] Pick an existing task from the picker; quick-add a new one (it also appears in its list).
- [ ] Tick an item: the task is done in zone 1 and its history says it was completed from focus.
- [ ] Complete a queued task from zone 1: it leaves the queue.
- [ ] Reorder the queue; it is restored after restart.
- [ ] The queue never exceeds the capacity; adding beyond it shows an inline message.

## Manual test script

1. Star 3 tasks from two lists; pick a 4th; quick-add a 5th.
2. Tick one in the queue, archive one in zone 1, delete one in zone 1; check the queue and histories.
3. Queue a weekly recurring task, tick it: next due date moves, item leaves the queue.
4. Restart; check order and content.

## Review gate questions

1. Should starting a favorite (or the timer) be possible from a focus item (e.g. "Focus 25 min on
   this task")? Not in the brief; default: no.
2. Keep completed items visible until "Clear completed" (default: removed immediately)?
