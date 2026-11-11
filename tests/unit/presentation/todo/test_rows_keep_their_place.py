from dataclasses import replace
from datetime import date

from concentrator.domain.todo.recurrence import Recurrence
from concentrator.domain.todo.recurrence_end_enum import RecurrenceEndEnum
from concentrator.domain.todo.recurrence_frequency_enum import RecurrenceFrequencyEnum
from concentrator.domain.todo.task_state_enum import TaskStateEnum
from tests.fakes.todo_factory import WORK_LIST_ID, make_task
from tests.fakes.todo_ui_stack import TodoUiStack

TODAY = date(2026, 11, 6)


def _keys(stack: TodoUiStack) -> list[str | int]:
    return [row.key for row in stack.table.build_snapshot().table.rows]


def _sorted_by_state() -> TodoUiStack:
    stack = TodoUiStack(
        tasks=[make_task(1), make_task(2, created_offset_minutes=1), make_task(3, created_offset_minutes=2)],
        stored={"layout/todo/sort": "1", "layout/todo/sort_descending": "1"},
    )
    stack.select("task-002")
    return stack


def test_a_ticked_task_keeps_its_row_even_when_its_sort_value_changes() -> None:
    stack = _sorted_by_state()
    before = _keys(stack)

    stack.table.on_check_toggled("task-002")
    stack.settle()

    assert _keys(stack) == before
    assert stack.task("task-002").state is TaskStateEnum.DONE
    assert stack.rendered_table[-1].table.selection == (before.index("task-002"),)


def test_a_new_task_takes_the_place_of_the_sort_and_the_others_stay() -> None:
    stack = TodoUiStack(tasks=[make_task(1), make_task(2, created_offset_minutes=1)])
    stack.table.on_check_toggled("task-001")
    stack.settle()

    stack.clock.advance(seconds=86_400)
    stack.task_commands.quick_add(WORK_LIST_ID, "Newest")
    stack.settle()

    assert _keys(stack) == ["new-0001", "task-002", "task-001"]


def test_a_repeating_task_keeps_its_row_when_it_moves_to_its_next_date() -> None:
    recurrence = Recurrence.create(
        frequency=RecurrenceFrequencyEnum.DAILY, interval=7, anchor_date=TODAY, end_kind=RecurrenceEndEnum.NEVER
    )
    stack = TodoUiStack(
        tasks=[
            replace(make_task(1, due_date=TODAY), recurrence=recurrence),
            make_task(2, due_date=date(2026, 11, 8), created_offset_minutes=1),
        ],
        stored={"layout/todo/sort": "3", "layout/todo/sort_descending": "0"},
    )
    assert _keys(stack) == ["task-001", "task-002"]

    stack.table.on_check_toggled("task-001")
    stack.settle()

    assert _keys(stack) == ["task-001", "task-002"]
    assert stack.task("task-001").due_date == date(2026, 11, 13)


def test_sorting_again_puts_every_task_in_its_place() -> None:
    stack = _sorted_by_state()
    stack.table.on_check_toggled("task-002")
    stack.settle()

    stack.table.on_sort_requested(0)
    stack.settle()

    assert _keys(stack) == ["task-001", "task-003", "task-002"]


def test_reset_layout_and_another_file_sort_again() -> None:
    stack = _sorted_by_state()
    stack.table.on_check_toggled("task-002")
    stack.settle()

    stack.refresher.reset_layout()
    stack.settle()

    assert _keys(stack)[0] == "task-003"
