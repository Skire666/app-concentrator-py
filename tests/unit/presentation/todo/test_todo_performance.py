"""Building the task table for 1,000 tasks stays under 100 ms (phase 5 spec)."""

import time
from datetime import date, timedelta
from typing import Final

import pytest

from concentrator.domain.todo.task_state_enum import TaskStateEnum
from tests.fakes.todo_factory import make_task
from tests.fakes.todo_ui_stack import TodoUiStack

TASKS: Final = 1000
BUDGET_S: Final = 0.1
RUNS: Final = 5
STATES: Final = (TaskStateEnum.OPEN, TaskStateEnum.OPEN, TaskStateEnum.DONE)


@pytest.mark.slow
def test_table_snapshot_of_1000_tasks_is_built_under_100_ms() -> None:
    tasks = [
        make_task(
            number,
            text=f"Task {number}\nsecond line",
            state=STATES[number % len(STATES)],
            due_date=date(2026, 11, 1) + timedelta(days=number % 20) if number % 4 else None,
            created_offset_minutes=number,
        )
        for number in range(TASKS)
    ]
    stack = TodoUiStack(tasks=tasks)
    stack.select(*(task.id for task in tasks[:500]))
    snapshot = stack.table.build_snapshot()
    timings: list[float] = []

    for _ in range(RUNS):
        start = time.perf_counter()
        snapshot = stack.table.build_snapshot()
        timings.append(time.perf_counter() - start)

    assert len(snapshot.table.rows) == TASKS
    assert len(snapshot.table.selection) == 500
    assert min(timings) < BUDGET_S, f"best build took {min(timings) * 1000:.1f} ms"
