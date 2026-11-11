# Phase 7 code review: findings and fixes

Branch `phase-7-focus-queue`, before the `phase-7-accepted` tag; not pushed. The review covered `main..bd74857`
(the 8 commits of the phase) and looked for defects, not style. It reported 10 findings; 8 are fixed, 1 is
fixed in part and 1 is not kept.

Findings 1 and 3 were reproduced with a failing UI test (real key presses on the drop-down, real scroll bar),
and findings 2, 4, 5 and 6 with a failing unit or UI test. Every fix started with that test. The decisions
are in amendment 2 of ADR-043.

## Findings and fixes

| # | Severity | Finding | Fix |
|---|---|---|---|
| 1 | medium | The task table now scrolls to a selection made elsewhere. After any model reset Qt drops the selection, the panel selected the same rows again and scrolled to them, which lost the scroll position just restored. Example: ticking a task in the queue while "Show done" is off sent the table back to the selected row. | `ui/support/table_selection.py` scrolls only when the selected tasks change, and the restored scroll position is kept after a reset. Test: 100 rows scrolled to the end, a reset keeps them there, a new selection scrolls to it. |
| 2 | medium | Enter on a highlighted entry of the search drop-down queued two tasks. The completer forwards Enter to the field (which picked the first entry) and then activates the highlighted entry. Reproduced: `['t1', 't2']`. | The field ignores Enter while the drop-down shows a highlighted entry. |
| 3 | medium | After a switch of the UI language, quick add created a second Inbox. The Inbox was looked up only under its name in the current language, so a file created in French ("Boîte de réception") got a new "Inbox". | `TranslatorPort.translations(key)` gives the text in every loaded language; the quick-add list matches any of them, the current language first. A new Inbox still takes the current language. |
| 4 | low to medium | Quick add created the Inbox before the text was checked. A refused text (too long) left an empty new Inbox behind. | Quick add checks the text with `TaskRules.validate_text` first. |
| 5 | low | When the history of the tasks could not be written, `add_tasks` reported a failure although the tasks were queued and the event published. Quick add then kept the text, and a second Enter created and queued the task twice. | The history failure is logged as a WARNING; the queue change succeeds. The same applies to removals. |
| 6 | low | A queue row tooltip showed the task text as Qt reads it: a text with tags could be rendered as HTML (`AGENTS.md` section 8.5). | `plain_tooltip` escapes it. |
| 7 | rule | `domain.focus` imported the `Task` entity and `TaskStateEnum` from `domain.todo`, but `AGENTS.md` section 4.2 allows only identifiers. | `FocusRules` takes a task id and whether the task is open. An architecture test now allows only `TaskId`, and section 4.2 says so. |
| 8 | rule, in part | `FocusRules.usable` took a `dict` of `Task` entities. | It now takes the open state of each task by id (finding 7). The items stay a `Sequence`, as in `TimerPresetRules.usable`: a file may repeat an id, which a `*Collection` refuses. |
| 9 | low (performance) | The search candidates checked each task against the queue with a linear scan, on every key press. | The queued ids are read once as a set. Not changed: `can_move` per row re-sorts a queue of at most 100 items, which is negligible. |
| 10 | cleanup | The quick-add hint repeated the Inbox catalog key instead of using `INBOX_NAME_KEY`, and two handlers requested `FOCUS_QUEUE` twice. | The constant is used and the duplicate requests are removed. |

The furryp limits forced two splits: `FocusCommands._queueable`, and the table selection helper (the panel
file exceeded its Halstead volume).

User-visible changes, besides the fixed cases: the quick add recognizes "Inbox" and "Boîte de réception"
whatever the language (`USAGE.md`).

## Gates

`uv run python scripts/check.py` on the fix commit:

| Gate | Result |
|---|---|
| ruff format, ruff check | passed |
| basedpyright | 0 errors |
| furryp | passed |
| pytest | 3115 passed |
| coverage gate | domain 99.81 %, application 99.00 %, presentation 99.02 %, overall 98.42 % |

## Manual checks to add

1. **Scroll after a reset.** In a long list, select a task near the top, scroll to the bottom, turn "Show
   done" off, then tick a queued task in the focus queue. The table stays at the bottom.
2. **Show in list.** Use it on a task far down the list: the table scrolls to it.
3. **Enter in the drop-down.** Type in the search field, highlight the second entry with the arrow keys,
   press Enter. Only that task is queued.
4. **Inbox and language.** In a file created in French with its "Boîte de réception", switch to ENG and
   quick-add a task. It goes to "Boîte de réception", and no "Inbox" tab appears.
5. **Text too long.** In a file without an Inbox, quick-add a text longer than 5000 characters. The message
   appears and no list is created.
6. **Tooltip.** Queue a task named `<b>Fix</b> layout`. Its tooltip in the queue shows the tags as typed.
