# Phase 5 code review: findings and fixes

Branch `phase-5-todo-core`, before the `phase-5-accepted` tag; not pushed. The review covered
`main..f3f9267` (142 files) and looked for defects, not style. It kept 8 findings. Findings 1, 2 and 4 were
reproduced (profiler, throwaway UI tests); 3 and 5 follow from the Qt documentation; 6 follows from the code
and needs a check on Windows. Every fix started with a failing test. The decisions are recorded in the
second amendment of ADR-041. All fixes are in commit `7560ab3`.

## Findings and fixes

| # | Severity | Finding | Fix |
|---|---|---|---|
| 1 | medium | A bulk state change publishes one `TaskStateChangedEvent` per task, and the view followed the data (existing list, visible selection) on each one: the cost grew with the square of the number of tasks. Done on 1,000 selected tasks took 142 ms, 95 % of it in `TodoView.sync`. | `TodoRefresher` marks the view stale; the view follows the data once, at its next read. 1,000 tasks: 9 ms. |
| 2 | medium | A second tab click during the `LIST_SELECT` cooldown was ignored, the snapshot did not change, so no render came: the tab bar showed the clicked tab while the table showed the previous list. | The tab bar shows the rendered tab again at once, then sends `LIST_SELECT`; the next snapshot moves it. |
| 3 | low to medium | `&` in a list name was read as a keyboard shortcut in the tabs and in the menus ("R&D" shown "RD", with Alt+D). | `without_mnemonic` doubles `&` in tab labels and in the menu items that show list names. |
| 4 | low | Qt moves the sort indicator itself on a header click; a click ignored during the `TODO_SORT` cooldown left an indicator for an order the rows did not have. | The header shows the rendered indicator again at once, then sends the click. |
| 5 | low | Qt takes a tooltip for rich text when it looks like HTML: a list description with tags was rendered in the tab tooltip (`AGENTS.md` section 8.5). | `plain_tooltip` escapes the text and keeps its line breaks. |
| 6 | low (to check on Windows) | The task and list dialogs send Cancel from `reject()`; when Windows closes the windows at the end of the session, a changed dialog would ask "Discard the changes?", against ADR-038 (nothing asked after `commitDataRequest`). | `ShutdownPresenter.is_session_ending()` is given to the dialogs; they close without asking then. |
| 7 | documentation | `AGENTS.md` section 8.2 still said that every change but an append resets the table model. | Section 8.2 describes the head removal, the in-place updates and widgets that show the rendered state again. |
| 8 | cleanup | `TOGGLE_ACTIONS` in `todo_toolbar_presenter.py` was not used. | Removed. |

Not kept: a double click on a check box toggles twice when the clicks are more than the cooldown apart;
that is Qt's own behaviour for check boxes in a table (two clicks), and each click is a separate action.

User-visible changes: none outside the fixed cases.

## Gates

`uv run python scripts/check.py` on `7560ab3`: ruff format and ruff check passed, basedpyright 0 errors,
furryp passed, 2535 tests passed, coverage gate passed (domain 100.00 %, application 99.38 %, presentation
99.07 %, overall 98.48 %).

## Manual checks to add

1. Click a tab, then quickly another one: the tab shown always matches the tasks shown.
2. Create a list named `R&D`: the tab and the "Move to list" menu show `R&D`.
3. Give a list the description `<b>bold</b>`: its tab tooltip shows the tags as typed.
4. Click two different column headers quickly: the sort indicator always matches the order of the rows.
5. Select every task of the 1,000-task copy (Ctrl+A in the table) and click **Done**: no visible pause.
6. Open the task dialog, change the text, then log off Windows: the session ends without the "Discard the
   changes?" question.
