# Phase 5 — TODO lists and tasks (core)

Depends on: phase 1 (phase 4 for the shared search and table widgets). Branch: `phase-5-todo-core`.

## Goal

Zone 1 (about 70 % of the Focus page) becomes a TODO manager: lists shown as tabs (priority, name,
description), tasks shown in a table, create / edit / delete one or several tasks, change their state
without opening them (done, reopen, archive), quick add, details pane, persisted layout.

## Out of scope

Recurrence, history display, due-date filters, search, clickable links (phase 6); focus queue
button (phase 7).

## Domain (`domain/todo/`)

| Type | Content |
|---|---|
| `PriorityEnum` | `UNKNOWN=-1, UNSET=0, LOW=1, NORMAL=2, HIGH=3, URGENT=4` |
| `TaskStateEnum` | `UNKNOWN=-1, UNSET=0, OPEN=1, DONE=2, ARCHIVED=3` |
| `TaskEventKindEnum` | `UNKNOWN=-1, UNSET=0, CREATED=1, TEXT_EDITED=2, DUE_CHANGED=3, COMPLETED=4, REOPENED=5, ARCHIVED=6, UNARCHIVED=7, MOVED=8, COPIED_FROM=9` (phases 6-7 append) |
| `TaskList` (entity) | `name` (1-`todo.max_list_name_length`, unique case-insensitively), `description: MultilineText`, `priority`, `position` |
| `Task` (entity) | `list_id`, `text: MultilineText` (first line not blank, <= `todo.max_task_text_length` chars), `due_date: date | None`, `due_time: time | None` (requires a date), `state`, `completed_at`, `history: TaskHistory` |
| `TaskEvent` (value) | `at` (UTC), `kind`, `details: tuple[tuple[str, str], ...]` |
| `TaskHistory` (collection of events) | append, cap at `todo.max_history_events` keeping the `CREATED` event and the newest ones |
| `TaskListsCollection` | ordered by priority (URGENT first) then `position`; name uniqueness; `next_position()`; at least one list |
| `TasksCollection` | `in_list(list_id)`, `with_states(...)`, `sorted_by(TaskSortKeyEnum, descending)`, bulk replace |
| `TaskRules`, `TaskListRules` | field rules and state transitions |

State transitions (every change adds a history event and sets `updated_at`):

| From | Action | To |
|---|---|---|
| OPEN | complete | DONE (`completed_at` = now) |
| DONE | reopen | OPEN (`completed_at` cleared) |
| OPEN, DONE | archive | ARCHIVED |
| ARCHIVED | unarchive | DONE if `completed_at` else OPEN |

A list always exists: when the file has no list, an "Inbox" list is created with the name translated
in the current language (it is user data afterwards and can be renamed). The last list cannot be
deleted. Deleting a non-empty list requires explicit confirmation and deletes its tasks.

## Application

- Ports: `task_list_reader_port.py`, `task_list_writer_port.py`, `task_reader_port.py`,
  `task_writer_port.py` (the nine operations).
- `todo/task_list_commands.py`: `create`, `update`, `delete(list_id, delete_tasks)`, `move`.
- `todo/task_commands.py`: `quick_add(list_id, text)`, `create(draft)`, `update(task_id, draft)`,
  `delete(task_ids)`, `complete(task_ids)`, `reopen(task_ids)`, `archive(task_ids)`,
  `unarchive(task_ids)`, `move_to_list(task_ids, list_id)`, `duplicate(task_id)` (`copy_business`).
  Bulk commands validate every item first and apply all or nothing.
- `todo/todo_queries.py`: ordered lists with open-task counts; tasks of a list for a `TaskQuery`
  (show done, show archived, sort key, order).
- Events: `TaskListChangedEvent`, `TaskCreatedEvent`, `TaskChangedEvent`,
  `TaskStateChangedEvent(task_id, old_state, new_state)`, `TaskDeletedEvent(task_ids)`.

## Presentation

- `todo/todo_tabs_presenter.py` / `TodoTabsSnapshot`: tabs (name, tooltip = description, priority
  badge text, open count), selected tab, "+" action.
- `todo/task_table_presenter.py` / `TaskTableSnapshot`: rows keyed by task id; columns State
  (checkbox), Task (first line, a marker when multi-line), Due (formatted, `is_overdue`,
  `is_today`), Created, Updated; current sort; selected ids preserved across renders; toolbar
  button states derived from the selection (e.g. Reopen enabled only if a selected task is DONE).
- `todo/task_details_presenter.py`: full text, list, due, state, created, updated.
- `todo/task_edit_form.py`, `todo/task_edit_presenter.py`, `todo/list_edit_form.py`,
  `todo/list_edit_presenter.py`: real-time validation, `is_dirty`.
- Confirmations through `DialogPort` with plural-aware texts ("Delete 3 tasks?").
- View preferences (`ViewPreferencesPort`): selected list id, sort key and order, show done, show
  archived, details pane visible.

## UI

Zone 1, top to bottom:

1. `TodoTabsPanel`: `QTabBar` (tabs from the snapshot, context menu Edit / Move earlier / Move later
   / Delete) and a "+" button; the description of the current list is shown under the tabs.
2. `TodoToolbarPanel`: New, Edit, Done, Reopen, Archive, Unarchive, Duplicate, Move to list (menu),
   Delete, toggles Show done / Show archived.
3. `QuickAddPanel`: one-line input "Add a task..." (Enter creates the task in the current list).
4. `TaskTablePanel`: `QTableView` + `SnapshotTableModel`, extended selection, clickable checkbox
   column (toggles done/open), double-click or Enter opens the editor, Del deletes, Space toggles
   done, Ctrl+N new task, context menu with the toolbar actions; header state (column widths and
   order) persisted through `LayoutStateKeeper` under a `layout/*` key (ADR-022).
5. `TaskDetailsPanel` in a vertical splitter under the table (collapsible, size persisted).

Dialogs: `TaskEditDialog` (multi-line text, list combo, due date with "No date", optional time),
`ListEditDialog` (name, description, priority).

New `ActionIdEnum` values: `LIST_ADD`, `LIST_EDIT`, `LIST_DELETE`, `LIST_MOVE_EARLIER`,
`LIST_MOVE_LATER`, `LIST_SELECT`, `TASK_NEW`, `TASK_QUICK_ADD`, `TASK_EDIT`, `TASK_COMPLETE`,
`TASK_REOPEN`, `TASK_TOGGLE_DONE`, `TASK_ARCHIVE`, `TASK_UNARCHIVE`, `TASK_DUPLICATE`, `TASK_MOVE`,
`TASK_DELETE`, `TASK_EDIT_SAVE`, `TASK_EDIT_CANCEL`, `LIST_EDIT_SAVE`, `LIST_EDIT_CANCEL`,
`TODO_TOGGLE_SHOW_DONE`, `TODO_TOGGLE_SHOW_ARCHIVED`, `TODO_SORT`.
New `RenderSectionEnum` values: `TODO_TABS`, `TODO_TOOLBAR`, `TODO_TABLE`, `TODO_DETAILS`,
`TASK_EDIT`, `LIST_EDIT`.

## File format (sections added)

```json5
  task_lists: [
    {
      id: "019a5c21-aaaa-7bbb-8ccc-3e4f5a6b7c8d",
      created_at: "2026-11-06T16:41:00Z",
      updated_at: "2026-11-06T16:41:00Z",
      name: "Work",
      description: ["Client projects", "and admin"],
      priority: 3,
      position: 0,
    },
  ],
  tasks: [
    {
      id: "019a5c22-bbbb-7ccc-8ddd-4f5a6b7c8d9e",
      created_at: "2026-11-06T16:45:00Z",
      updated_at: "2026-11-06T16:45:00Z",
      list_id: "019a5c21-aaaa-7bbb-8ccc-3e4f5a6b7c8d",
      text: ["Prepare the quarterly report", "Sources in D:/Reports/2026/Q4"],
      due_date: "2026-11-10",
      due_time: null,
      state: 1,
      completed_at: null,
      history: [{ at: "2026-11-06T16:45:00Z", kind: 1, details: {} }],
    },
  ],
```

Load-time rules: every `list_id` must reference an existing list (`TASK_LIST_NOT_FOUND`).

## `concentrator.ini` (new keys)

```ini
[todo]
max_task_text_length = 5000
max_list_name_length = 80
max_list_description_length = 2000
max_history_events = 50
default_list_priority = NORMAL
```

## Error codes

| Code | Name |
|---|---|
| 5001 | `TASK_TEXT_EMPTY` |
| 5002 | `TASK_TEXT_TOO_LONG` |
| 5003 | `TASK_DUE_TIME_WITHOUT_DATE` |
| 5004 | `TASK_STATE_TRANSITION_INVALID` |
| 5005 | `TASK_LIST_NOT_FOUND` |
| 5101 | `LIST_NAME_EMPTY` |
| 5102 | `LIST_NAME_TOO_LONG` |
| 5103 | `LIST_NAME_DUPLICATE` |
| 5104 | `LIST_DESCRIPTION_TOO_LONG` |
| 5105 | `LIST_NOT_EMPTY` |
| 5106 | `LIST_LAST_CANNOT_DELETE` |
| 5107 | `LIST_PRIORITY_UNSET` |

## Tests

- Rules and transitions: every field limit; transition table; history cap keeps `CREATED`.
- Collections: list ordering by priority then position; casefold uniqueness ("Work" vs "work");
  tasks sorting for each key and both orders, stable on ties.
- Commands: bulk all-or-nothing (one invalid id -> nothing changed); duplicate creates a new id,
  new timestamps and a `COPIED_FROM` event; delete of the last list refused; delete non-empty list
  without confirmation refused; events published once per command.
- Presenters: column formatting in English and French; overdue / today flags with `FakeClock`;
  selection kept after a re-render and after sorting; toolbar states for mixed selections; plural
  confirmation texts.
- Persistence: round trip with several lists and tasks; dangling `list_id` -> error.
- UI smoke: table with 3 rows renders; clicking the checkbox emits the toggle with the right id;
  tab bar renders names and badges.
- Performance (`slow` marker): building the table snapshot for 2,000 tasks takes < 100 ms.

## Acceptance criteria

- [ ] Create, rename, reorder, delete lists; tabs follow priority then position.
- [ ] Quick add with Enter; create and edit with the dialog (multi-line text, due date).
- [ ] Select several tasks: complete, reopen, archive, move, delete in one action.
- [ ] The checkbox column toggles done without opening the task.
- [ ] Show done / Show archived toggles, sort by any column; everything is restored after restart
      (selected tab, sort, columns, splitter).
- [ ] 2,000 tasks in a list: scrolling and selection stay fluid.
- [ ] FRA/ENG switch updates headers, buttons, dates and confirmations live.

## Manual test script

1. Create lists Work (HIGH), Home (NORMAL), Ideas (LOW); check the tab order; reorder Home first
   within its priority.
2. Quick add 5 tasks, edit one with 3 lines and a due date yesterday (overdue display).
3. Select 3 tasks, Done; Show done off; Show archived on; archive one; unarchive it.
4. Resize and reorder columns, sort by Due descending, restart.
5. Generate 2,000 tasks with `scripts/bench_storage.py --seed-tasks 2000 --into <copy of your file>`
   and open that copy with "Use another file".

## Review gate questions

1. Tasks have no individual priority (only lists do, as in the brief): confirm or add one.
2. Deleting a non-empty list deletes its tasks after confirmation (alternative: move them).
