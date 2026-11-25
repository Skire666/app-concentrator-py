# Focus queue removal: report

Branch `remove-focus-queue`, from `main` (`0963ead`); not pushed. Owner request (2026-11-25): remove the
focus notion from the timer area and from the task table, and its logic from the task history. Plan approved
the same day ("Suit tes recommandations"), with one change by the owner: no existing TOML file to carry over,
so schema version 2 does not migrate version 1. Decisions in ADR-046.

## Summary

| Commit | Content |
|---|---|
| `44e09f6` `refactor(todo)!` | Zone 2 without the queue panel; task table without the star column; toolbar, context menu and tab menu without focus actions; `presentation.focus`, the queue widgets and `bootstrap/focus.py` removed; header blob `todo_header_v4`; eight task column widths. |
| `5e06473` `feat(storage)!` | `domain.focus`, `application.focus`, focus ports and stores, `TaskFocusHistory`, `[[focus_queue]]`, `[focus]`, the `6xxx` codes and the focus history texts removed; completions without `source`; schema version 2 without migration; `schema-v2.toml` frozen reference; `furryp.json` without `concentrator.domain.focus`. |
| docs commit | ADR-046 (ADR-013 and ADR-043 superseded), `AGENTS.md`, `USAGE.md`, `README.md`, `CONTRIBUTING.md`, `CHANGELOG.md` (Unreleased), phase 7 spec marked as removed, this report. |

118 files changed before the docs commit: 208 lines added, 5,290 removed. Kept on purpose: the Focus page
and its module button, the timer (it had no focus logic), `TaskOccurrenceCompletedEvent` (the TODO refresher
listens to it), `ui/support/focus_order.py` (keyboard focus, unrelated).

## Deviations from the plan

1. **No migration from version 1** (owner change): the planned step that dropped `focus_queue` and the
   focus events is not written. A version 1 file is refused (`STORAGE_FIELD_INVALID_VALUE` on
   `schema_version`) and never written; a test covers it.
2. **More dead code removed than listed**: `TodoViewState.reveal` ("Show in list") had no other caller.
   Same rule as the approved question 5.
3. **Rich text test**: it proved that a hostile text reached a plain-text label through a queue row; it now
   checks the cells of the task table.
4. **Keyboard test of the Focus page**: it queued two tasks; it now only adds them to the list.

## Gates

`uv run python scripts/check.py` on every commit:

```
ruff format    passed
ruff check     passed
basedpyright   passed
furryp         passed
pytest         passed (3,033 tests)
coverage gate  passed
```

| Scope | Coverage | Minimum |
|---|---|---|
| domain | 99.79 % | 80 % |
| application | 99.43 % | 75 % |
| presentation | 99.09 % | 70 % |
| overall | 98.42 % | 70 % |

`uv run python scripts/build.py`: build complete, 70.6 MB, self-check passed (the round trip no longer holds a
queued task).

## Manual checks for the owner (the GUI cannot be inspected by the agent)

1. Zone 2: timer, favorites and special options at the top, no queue; resize the window and the splitter.
2. Task table: no star column; check box, double click, a click on a link of the task column, sort by a
   header, the List column in "All lists"; column widths back to the defaults once.
3. Toolbar, table context menu and tab context menu: no focus action left.
4. History tab of a completed task (French and English): no focus wording.
5. Tab order on the Focus page; Alt letters of the module bar.
6. Open a data file of version 1.0.0 (a copy): it is refused and left untouched, the recovery dialog offers
   another file or a new one. A new data file is written with `schema_version = 2` and no `focus_queue`.
7. Run `dist/Concentrator/Concentrator.exe`.

## Open questions (default in parentheses)

1. The two `feat(todo)` commits made after release 1.0.0 (due date filled when Repeat is ticked, due date
   moved with the weekdays of a weekly series) are not in the changelog. (Add them to "Unreleased".)
2. The README screenshot `docs/images/focus-page.png` still shows the queue. (The owner takes it again.)
3. The specs of phases 2, 3, 5 and 6 still mention the queue as a later phase. (Leave them: they record what
   each phase was asked.)
