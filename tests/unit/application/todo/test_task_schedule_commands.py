from dataclasses import replace
from datetime import date, time

from concentrator.application.todo.todo_events import TaskChangedEvent
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.todo.recurrence import Recurrence
from concentrator.domain.todo.recurrence_end_enum import RecurrenceEndEnum
from concentrator.domain.todo.recurrence_frequency_enum import RecurrenceFrequencyEnum
from concentrator.domain.todo.task import Task
from concentrator.domain.todo.task_event_kind_enum import TaskEventKindEnum
from tests.fakes.todo_factory import make_task
from tests.fakes.todo_stack import WRITE_FAILED, TodoStack

NEW_DUE = date(2026, 11, 20)


def _recurring(number: int, end_date: date | None = None) -> Task:
    recurrence = Recurrence.create(
        frequency=RecurrenceFrequencyEnum.MONTHLY,
        interval=1,
        anchor_date=date(2026, 11, 10),
        end_kind=RecurrenceEndEnum.ON_DATE if end_date else RecurrenceEndEnum.NEVER,
        end_date=end_date,
    )
    return replace(make_task(number, due_date=date(2026, 11, 10)), recurrence=recurrence)


def test_set_due_date_on_twenty_tasks_writes_once_with_one_event_each() -> None:
    tasks = [make_task(number, due_time=None) for number in range(1, 21)]
    stack = TodoStack(tasks=tasks)
    ids = [task.id for task in tasks]

    assert stack.schedule_commands.set_due_date(ids, NEW_DUE).is_success

    assert {stack.task(task_id).due_date for task_id in ids} == {NEW_DUE}
    last_events = [stack.task(task_id).history.last for task_id in ids]
    assert [None if event is None else event.kind for event in last_events] == [TaskEventKindEnum.DUE_CHANGED] * 20
    assert stack.events == [TaskChangedEvent(task_ids=tuple(ids))]


def test_set_due_date_keeps_the_time_and_anchors_a_series() -> None:
    timed = make_task(1, due_date=date(2026, 11, 12), due_time=time(14, 30))
    stack = TodoStack(tasks=[timed, _recurring(2)])

    stack.schedule_commands.set_due_date(["task-001", "task-002"], NEW_DUE)

    assert stack.task("task-001").due_time == time(14, 30)
    recurrence = stack.task("task-002").recurrence
    assert recurrence is not None
    assert recurrence.anchor_date == NEW_DUE


def test_set_due_date_is_all_or_nothing() -> None:
    stack = TodoStack(tasks=[make_task(1), _recurring(2, end_date=date(2026, 11, 15))])

    result = stack.schedule_commands.set_due_date(["task-001", "task-002"], NEW_DUE)

    assert result.error_codes == (ErrorCodeEnum.RECURRENCE_END_DATE_BEFORE_DUE,)
    assert stack.task("task-001").due_date is None
    assert stack.events == []


def test_set_due_date_of_a_missing_task_changes_nothing() -> None:
    stack = TodoStack(tasks=[make_task(1)])

    result = stack.schedule_commands.set_due_date(["task-001", "missing"], NEW_DUE)

    assert result.error_codes == (ErrorCodeEnum.ENTITY_NOT_FOUND,)
    assert stack.task("task-001").due_date is None


def test_clear_due_date_refuses_a_recurring_task() -> None:
    stack = TodoStack(tasks=[make_task(1, due_date=NEW_DUE), _recurring(2)])

    result = stack.schedule_commands.clear_due_date(["task-001", "task-002"])

    assert result.error_codes == (ErrorCodeEnum.RECURRENCE_REQUIRES_DUE_DATE,)
    assert stack.task("task-001").due_date == NEW_DUE


def test_clear_due_date_removes_date_and_time() -> None:
    stack = TodoStack(tasks=[make_task(1, due_date=NEW_DUE, due_time=time(8, 0))])

    assert stack.schedule_commands.clear_due_date(["task-001"]).is_success

    assert (stack.task("task-001").due_date, stack.task("task-001").due_time) == (None, None)


def test_nothing_to_change_is_skipped() -> None:
    stack = TodoStack(tasks=[make_task(1, due_date=NEW_DUE)])

    assert stack.schedule_commands.set_due_date(["task-001"], NEW_DUE).is_skipped
    assert stack.schedule_commands.clear_due_date([]).is_skipped
    assert stack.events == []


def test_a_failed_write_is_reported() -> None:
    stack = TodoStack(tasks=[make_task(1)])
    stack.task_writer.fail = True

    assert stack.schedule_commands.set_due_date(["task-001"], NEW_DUE) == WRITE_FAILED
    assert stack.events == []
