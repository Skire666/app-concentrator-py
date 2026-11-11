from dataclasses import replace
from datetime import date, time

from concentrator.domain.todo.recurrence import Recurrence
from concentrator.domain.todo.recurrence_end_enum import RecurrenceEndEnum
from concentrator.domain.todo.recurrence_frequency_enum import RecurrenceFrequencyEnum
from concentrator.domain.todo.task import Task
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.button_snapshot import ButtonSnapshot
from concentrator.presentation.todo.task_menu_snapshot import TaskMenuSnapshot
from tests.fakes.todo_factory import make_task
from tests.fakes.todo_ui_stack import TodoUiStack

TODAY = date(2026, 11, 6)
NEW_DUE = date(2026, 11, 20)
SET = int(ActionIdEnum.TASK_SET_DUE_DATE)
CLEAR = int(ActionIdEnum.TASK_CLEAR_DUE_DATE)


def _button(menu: TaskMenuSnapshot, action: ActionIdEnum) -> ButtonSnapshot:
    return next(button for button in menu.buttons if button.action is action)


def _recurring(number: int) -> Task:
    recurrence = Recurrence.create(
        frequency=RecurrenceFrequencyEnum.DAILY, interval=1, anchor_date=TODAY, end_kind=RecurrenceEndEnum.NEVER
    )
    return replace(make_task(number, due_date=TODAY), recurrence=recurrence)


def _twenty() -> TodoUiStack:
    stack = TodoUiStack(tasks=[make_task(number, created_offset_minutes=number) for number in range(1, 21)])
    stack.select(*(f"task-{number:03d}" for number in range(1, 21)))
    return stack


def test_set_due_date_on_twenty_selected_tasks_in_one_action() -> None:
    stack = _twenty()
    stack.dialogs.date_answer = NEW_DUE

    stack.toolbar.on_action_requested(SET)
    stack.settle()

    assert {task.due_date for task in stack.tasks()} == {NEW_DUE}
    prompt = stack.dialogs.prompts[0]
    assert (prompt.initial, prompt.label) == (TODAY, "en:todo.set_due.label.other(count=20)")
    assert (prompt.accept_text, prompt.reject_text) == ("en:todo.set_due.accept", "en:dialog.button.cancel")


def test_cancelling_the_date_changes_nothing() -> None:
    stack = _twenty()

    stack.toolbar.on_action_requested(SET)

    assert {task.due_date for task in stack.tasks()} == {None}


def test_the_prompt_starts_on_the_first_due_date_and_times_are_kept() -> None:
    stack = TodoUiStack(tasks=[make_task(1, due_date=date(2026, 12, 1), due_time=time(8, 0))])
    stack.select("task-001")
    stack.dialogs.date_answer = NEW_DUE

    stack.toolbar.on_action_requested(SET)

    assert stack.dialogs.prompts[0].initial == date(2026, 12, 1)
    assert (stack.task("task-001").due_date, stack.task("task-001").due_time) == (NEW_DUE, time(8, 0))


def test_clear_due_date_is_off_without_a_date_and_for_a_repeating_task() -> None:
    stack = TodoUiStack(tasks=[make_task(1), make_task(2, due_date=TODAY), _recurring(3)])

    stack.select("task-001")
    assert not _button(stack.toolbar.build_snapshot().menu, ActionIdEnum.TASK_CLEAR_DUE_DATE).enabled
    stack.select("task-002")
    assert _button(stack.toolbar.build_snapshot().menu, ActionIdEnum.TASK_CLEAR_DUE_DATE).enabled
    stack.select("task-002", "task-003")
    button = _button(stack.toolbar.build_snapshot().menu, ActionIdEnum.TASK_CLEAR_DUE_DATE)
    assert not button.enabled
    assert button.tooltip == "en:error.recurrence_requires_due_date"


def test_clear_due_date_removes_the_dates_of_the_selection() -> None:
    stack = TodoUiStack(tasks=[make_task(1, due_date=TODAY), make_task(2, due_date=NEW_DUE)])
    stack.select("task-001", "task-002")

    stack.toolbar.on_action_requested(CLEAR)
    stack.settle()

    assert {task.due_date for task in stack.tasks()} == {None}


def test_set_due_date_without_selection_does_nothing() -> None:
    stack = TodoUiStack(tasks=[make_task(1)])

    stack.actions.run(ActionIdEnum.TASK_SET_DUE_DATE)

    assert stack.dialogs.prompts == []
