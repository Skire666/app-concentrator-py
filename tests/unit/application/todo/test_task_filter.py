from dataclasses import replace
from datetime import UTC, date, datetime, time

import pytest

from concentrator.application.todo.due_filter_enum import DueFilterEnum
from concentrator.application.todo.task_filter import TaskFilter
from concentrator.application.todo.task_query import TaskQuery
from concentrator.application.todo.task_scope_enum import TaskScopeEnum
from concentrator.domain.todo.recurrence import Recurrence
from concentrator.domain.todo.recurrence_end_enum import RecurrenceEndEnum
from concentrator.domain.todo.recurrence_frequency_enum import RecurrenceFrequencyEnum
from concentrator.domain.todo.task import Task
from concentrator.domain.todo.task_sort_key_enum import TaskSortKeyEnum
from concentrator.domain.todo.task_state_enum import TaskStateEnum
from tests.fakes.todo_factory import HOME_LIST_ID, WORK_LIST_ID, make_task
from tests.fakes.todo_stack import TodoStack

NOW = datetime(2026, 11, 11, 12, 0, tzinfo=UTC)
"""A Wednesday: the week runs from Monday 9 to Sunday 15 November."""

TASKS = {
    "no date": make_task(1),
    "last week": make_task(2, due_date=date(2026, 11, 6)),
    "monday": make_task(3, due_date=date(2026, 11, 9)),
    "today passed": make_task(4, due_date=date(2026, 11, 11), due_time=time(11, 0)),
    "today later": make_task(5, due_date=date(2026, 11, 11), due_time=time(18, 0)),
    "sunday": make_task(6, due_date=date(2026, 11, 15)),
    "next tuesday": make_task(7, due_date=date(2026, 11, 17)),
    "next wednesday": make_task(8, due_date=date(2026, 11, 18)),
    "done late": make_task(9, due_date=date(2026, 11, 2), state=TaskStateEnum.DONE),
}


@pytest.mark.parametrize(
    ("due", "expected"),
    [
        (DueFilterEnum.ALL, set(TASKS)),
        (DueFilterEnum.UNKNOWN, set(TASKS)),
        (DueFilterEnum.OVERDUE, {"last week", "monday", "today passed"}),
        (DueFilterEnum.TODAY, {"today passed", "today later"}),
        (DueFilterEnum.THIS_WEEK, {"monday", "today passed", "today later", "sunday"}),
        (DueFilterEnum.NEXT_7_DAYS, {"today passed", "today later", "sunday", "next tuesday"}),
        (DueFilterEnum.WITH_DATE, set(TASKS) - {"no date"}),
        (DueFilterEnum.NO_DATE, {"no date"}),
    ],
)
def test_due_filters(due: DueFilterEnum, expected: set[str]) -> None:
    task_filter = TaskFilter(due=due)

    assert {name for name, task in TASKS.items() if task_filter.matches(task, NOW)} == expected


def _recurring(task: Task) -> Task:
    recurrence = Recurrence.create(
        frequency=RecurrenceFrequencyEnum.DAILY,
        interval=1,
        anchor_date=date(2026, 11, 9),
        end_kind=RecurrenceEndEnum.NEVER,
    )
    return replace(task, recurrence=recurrence)


def test_recurring_only_keeps_the_tasks_that_repeat() -> None:
    task_filter = TaskFilter(recurring_only=True)

    assert task_filter.matches(_recurring(TASKS["monday"]), NOW)
    assert not task_filter.matches(TASKS["monday"], NOW)


@pytest.mark.parametrize(
    ("task_filter", "active", "timed"),
    [
        (TaskFilter(), False, False),
        (TaskFilter(recurring_only=True), True, False),
        (TaskFilter(due=DueFilterEnum.NO_DATE), True, False),
        (TaskFilter(due=DueFilterEnum.OVERDUE), True, True),
    ],
)
def test_filter_flags(task_filter: TaskFilter, *, active: bool, timed: bool) -> None:
    assert (task_filter.is_active, task_filter.depends_on_time) == (active, timed)


def test_queries_combine_scope_states_and_filters() -> None:
    home = make_task(10, list_id=HOME_LIST_ID, due_date=date(2026, 11, 10))
    stack = TodoStack(tasks=[*TASKS.values(), home])
    query = TaskQuery(
        list_id=WORK_LIST_ID,
        show_done=False,
        show_archived=False,
        sort_key=TaskSortKeyEnum.DUE,
        descending=False,
        task_filter=TaskFilter(due=DueFilterEnum.OVERDUE),
        scope=TaskScopeEnum.ALL_LISTS,
    )

    shown = stack.queries.tasks(query, NOW)

    assert [task.id for task in shown] == ["task-002", "task-003", "task-010", "task-004"]
    assert len(stack.queries.in_scope(query)) == 10
    assert len(stack.queries.in_scope(replace(query, scope=TaskScopeEnum.THIS_LIST))) == 9
