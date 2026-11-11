from dataclasses import replace
from datetime import date

import pytest

from concentrator.application.focus.focus_events import FocusQueueChangedEvent
from concentrator.domain.focus.focus_removal_reason_enum import FocusRemovalReasonEnum
from concentrator.domain.todo.recurrence import Recurrence
from concentrator.domain.todo.recurrence_end_enum import RecurrenceEndEnum
from concentrator.domain.todo.recurrence_frequency_enum import RecurrenceFrequencyEnum
from concentrator.domain.todo.task import Task
from concentrator.domain.todo.task_event import DETAIL_REASON
from concentrator.domain.todo.task_event_kind_enum import TaskEventKindEnum
from concentrator.domain.todo.task_state_enum import TaskStateEnum
from tests.fakes.focus_factory import make_queue
from tests.fakes.focus_stack import FocusStack
from tests.fakes.todo_factory import WORK_LIST_ID, make_task

TODAY = date(2026, 11, 6)


def _removal_reason(task: Task) -> str:
    last = task.history.last
    assert last is not None
    assert last.kind is TaskEventKindEnum.REMOVED_FROM_FOCUS
    return last.detail(DETAIL_REASON)


def test_completing_a_queued_task_in_zone_one_unqueues_it_with_the_reason() -> None:
    stack = FocusStack(tasks=[make_task(1), make_task(2)], queue=make_queue(1, 2))

    assert stack.task_commands.complete(["task-001"]).is_success

    assert stack.queued() == ["task-002"]
    assert _removal_reason(stack.task("task-001")) == str(FocusRemovalReasonEnum.COMPLETED.value)
    assert stack.focus_events == [FocusQueueChangedEvent(task_ids=("task-001",))]


def test_archiving_a_queued_task_unqueues_it_with_the_reason() -> None:
    stack = FocusStack(tasks=[make_task(1)], queue=make_queue(1))

    assert stack.task_commands.archive(["task-001"]).is_success

    assert stack.queued() == []
    assert _removal_reason(stack.task("task-001")) == str(FocusRemovalReasonEnum.ARCHIVED.value)


def test_deleting_a_queued_task_unqueues_it() -> None:
    stack = FocusStack(tasks=[make_task(1), make_task(2)], queue=make_queue(1, 2))

    assert stack.task_commands.delete(["task-001"]).is_success

    assert stack.queued() == ["task-002"]
    assert stack.focus_events == [FocusQueueChangedEvent(task_ids=("task-001",))]


def test_deleting_a_list_unqueues_its_tasks() -> None:
    stack = FocusStack(tasks=[make_task(1)], queue=make_queue(1))

    assert stack.list_commands.delete(WORK_LIST_ID, delete_tasks=True).is_success

    assert stack.queued() == []


def test_reopening_a_task_does_not_queue_it_again() -> None:
    stack = FocusStack(tasks=[make_task(1)], queue=make_queue(1))
    stack.task_commands.complete(["task-001"])

    assert stack.task_commands.reopen(["task-001"]).is_success

    assert stack.queued() == []


def test_an_occurrence_completed_in_zone_one_unqueues_the_task_that_stays_open() -> None:
    recurrence = Recurrence.create(
        frequency=RecurrenceFrequencyEnum.DAILY, interval=1, anchor_date=TODAY, end_kind=RecurrenceEndEnum.NEVER
    )
    stack = FocusStack(tasks=[replace(make_task(1, due_date=TODAY), recurrence=recurrence)], queue=make_queue(1))

    assert stack.task_commands.complete(["task-001"]).is_success

    task = stack.task("task-001")
    assert task.state is TaskStateEnum.OPEN
    assert stack.queued() == []
    assert _removal_reason(task) == str(FocusRemovalReasonEnum.OCCURRENCE_COMPLETED.value)


def test_changes_of_tasks_that_are_not_queued_change_nothing() -> None:
    stack = FocusStack(tasks=[make_task(1), make_task(2)], queue=make_queue(2))

    stack.task_commands.complete(["task-001"])
    stack.task_commands.delete(["task-001"])

    assert stack.queued() == ["task-002"]
    assert stack.focus_events == []


def test_a_failed_history_write_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    stack = FocusStack(tasks=[make_task(1)], queue=make_queue(1))
    stack.task_writer.writes_before_failure = 1

    assert stack.task_commands.archive(["task-001"]).is_success

    assert stack.queued() == []
    assert "Focus queue not updated after a task change" in caplog.text
