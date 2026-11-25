from dataclasses import replace
from datetime import date

from concentrator.domain.common.multiline_text import MultilineText
from concentrator.domain.todo.recurrence import Recurrence
from concentrator.domain.todo.recurrence_end_enum import RecurrenceEndEnum
from concentrator.domain.todo.recurrence_frequency_enum import RecurrenceFrequencyEnum
from concentrator.domain.todo.task import Task
from concentrator.domain.todo.task_state_enum import TaskStateEnum
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from tests.fakes.todo_factory import HOME_LIST_ID, make_task
from tests.fakes.todo_ui_stack import DEFAULTS, TodoUiStack

TODAY = date(2026, 11, 6)
DEBOUNCE_MS = DEFAULTS.search_debounce_ms


def _recurring(task: Task) -> Task:
    recurrence = Recurrence.create(
        frequency=RecurrenceFrequencyEnum.DAILY, interval=1, anchor_date=TODAY, end_kind=RecurrenceEndEnum.NEVER
    )
    return replace(task, due_date=TODAY, recurrence=recurrence)


def _tasks() -> list[Task]:
    return [
        replace(make_task(1), text=MultilineText(("État des lieux", "Appartement"))),
        make_task(2, text="Groceries", due_date=TODAY, created_offset_minutes=1),
        _recurring(make_task(3, text="Water the plants", created_offset_minutes=2)),
        make_task(4, text="Old one", state=TaskStateEnum.DONE, created_offset_minutes=3),
        make_task(5, list_id=HOME_LIST_ID, text="Etat de la chaudière", created_offset_minutes=4),
    ]


def _keys(stack: TodoUiStack) -> list[str | int]:
    return [row.key for row in stack.rendered_table[-1].table.rows]


def _search(stack: TodoUiStack, text: str) -> None:
    stack.filters.on_search_changed(text)
    stack.scheduler.advance(DEBOUNCE_MS)
    stack.settle()


def test_initial_bar_shows_every_filter_and_the_counter() -> None:
    stack = TodoUiStack(tasks=_tasks())

    snapshot = stack.filters.build_snapshot()

    assert snapshot.due.options[0] == "en:todo.filter.due.all"
    assert (snapshot.due.selected, snapshot.scope.selected, snapshot.recurring_only.checked) == (0, 0, False)
    assert not snapshot.search.text
    assert snapshot.counter == "en:todo.filter.counter.other(count=4,shown=4)"


def test_due_filter_narrows_the_table_and_is_remembered() -> None:
    stack = TodoUiStack(tasks=_tasks())

    stack.filters.on_due_selected(2)
    stack.settle()

    assert _keys(stack) == ["task-003", "task-002"]
    assert stack.preferences.values["layout/todo/due_filter"] == "3"
    assert stack.rendered_filters[-1].counter == "en:todo.filter.counter.other(count=4,shown=2)"


def test_a_bad_due_index_changes_nothing() -> None:
    stack = TodoUiStack(tasks=_tasks())

    stack.filters.on_due_selected(99)
    stack.filters.on_scope_selected(-1)
    stack.settle()

    assert "layout/todo/due_filter" not in stack.preferences.values
    assert "layout/todo/scope" not in stack.preferences.values


def test_recurring_only_keeps_the_tasks_that_repeat() -> None:
    stack = TodoUiStack(tasks=_tasks())

    stack.filters.on_action_requested(int(ActionIdEnum.TODO_TOGGLE_RECURRING_ONLY))
    stack.settle()

    assert _keys(stack) == ["task-003"]
    assert stack.rendered_filters[-1].recurring_only.checked
    assert stack.preferences.values["layout/todo/recurring_only"] == "1"


def test_an_unknown_filter_action_is_ignored() -> None:
    stack = TodoUiStack(tasks=_tasks())

    stack.filters.on_action_requested(int(ActionIdEnum.TASK_NEW))
    stack.settle()

    assert not stack.view.state.task_filter.recurring_only


def test_search_ignores_case_and_accents_after_the_debounce() -> None:
    stack = TodoUiStack(tasks=_tasks())

    stack.filters.on_search_changed("etat")
    stack.settle()
    assert len(stack.view.visible()) == 4

    stack.scheduler.advance(DEBOUNCE_MS)
    stack.settle()

    assert _keys(stack) == ["task-001"]
    assert stack.preferences.values["layout/todo/search"] == "etat"


def test_search_on_every_line_and_every_word() -> None:
    stack = TodoUiStack(tasks=_tasks())

    _search(stack, "APPARTEMENT état")

    assert _keys(stack) == ["task-001"]


def test_scope_all_lists_searches_every_list_and_shows_the_list_column() -> None:
    stack = TodoUiStack(tasks=_tasks())
    _search(stack, "etat")

    stack.filters.on_scope_selected(1)
    stack.settle()

    table = stack.rendered_table[-1].table
    assert [row.key for row in table.rows] == ["task-005", "task-001"]
    assert table.hidden_columns == ()
    assert table.rows[0].cells[2] == "Home"
    assert stack.rendered_filters[-1].counter == "en:todo.filter.counter.other(count=5,shown=2)"


def test_typed_text_is_shown_until_it_applies() -> None:
    stack = TodoUiStack(tasks=_tasks())

    stack.filters.on_search_changed("gro")
    stack.filters.on_search_changed("groc")

    assert stack.filters.build_snapshot().search.text == "groc"
    stack.scheduler.advance(DEBOUNCE_MS)
    stack.settle()
    assert _keys(stack) == ["task-002"]


def test_search_waits_while_the_previous_search_cools_down() -> None:
    stack = TodoUiStack(tasks=_tasks())
    busy = stack.gate.begin(ActionIdEnum.TODO_SEARCH).data
    assert busy is not None

    stack.filters.on_search_changed("water")
    stack.scheduler.advance(DEBOUNCE_MS)
    stack.scheduler.run_pending()
    assert not stack.view.state.search.query

    busy.finish()
    stack.scheduler.advance(DEBOUNCE_MS)
    stack.settle()
    assert stack.view.state.search.query == "water"


def test_filters_are_restored_from_the_layout_keys() -> None:
    stored = {
        "layout/todo/due_filter": "6",
        "layout/todo/recurring_only": "1",
        "layout/todo/scope": "2",
        "layout/todo/search": "water",
    }

    stack = TodoUiStack(tasks=_tasks(), stored=stored)

    state = stack.view.state
    snapshot = stack.filters.build_snapshot()
    assert (snapshot.due.selected, snapshot.recurring_only.checked, snapshot.scope.selected) == (5, True, 1)
    assert (snapshot.search.text, state.search.query) == ("water", "water")
    assert [task.id for task in stack.view.visible()] == ["task-003"]


def test_values_not_understood_take_their_default() -> None:
    stored = {"layout/todo/due_filter": "42", "layout/todo/scope": "x", "layout/todo/recurring_only": "?"}

    stack = TodoUiStack(tasks=_tasks(), stored=stored)

    snapshot = stack.filters.build_snapshot()
    assert (snapshot.due.selected, snapshot.scope.selected, snapshot.recurring_only.checked) == (0, 0, False)


def test_reset_layout_clears_the_filters() -> None:
    stack = TodoUiStack(tasks=_tasks(), stored={"layout/todo/due_filter": "2", "layout/todo/search": "x"})

    stack.refresher.reset_layout()
    stack.settle()

    snapshot = stack.filters.build_snapshot()
    assert (snapshot.due.selected, snapshot.search.text) == (0, "")
    assert len(_keys(stack)) == 4


def test_the_overdue_filter_follows_the_clock() -> None:
    stack = TodoUiStack(tasks=[make_task(1, due_date=TODAY)])
    stack.filters.on_due_selected(1)
    stack.settle()
    assert _keys(stack) == []

    stack.clock.advance(seconds=24 * 3600)
    stack.table.on_tick()
    stack.settle()

    assert _keys(stack) == ["task-001"]
