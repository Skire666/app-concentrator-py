"""Overdue and due-today marks of a task, shared by the table emphasis and the Overdue filter."""

from dataclasses import dataclass
from datetime import datetime

from concentrator.domain.todo.task import Task
from concentrator.domain.todo.task_state_enum import TaskStateEnum


@dataclass(frozen=True, slots=True, kw_only=True)
class DueMarks:
    """Emphasis of an open task's due date (ADR-041).

    Attributes:
        is_overdue: The due date is past, or it is today and the due time has passed.
        is_today: The task is due today and not overdue yet.
    """

    is_overdue: bool
    is_today: bool


def due_marks(task: Task, now: datetime) -> DueMarks:
    """Tell whether an open task is overdue or due today; done and archived tasks are never marked.

    Args:
        task: Task.
        now: Current local time.

    Returns:
        The marks.
    """
    if task.due_date is None or task.state is not TaskStateEnum.OPEN:
        return DueMarks(is_overdue=False, is_today=False)
    today = now.date()
    passed_time = task.due_time is not None and task.due_time <= now.time()
    overdue = task.due_date < today or (task.due_date == today and passed_time)
    return DueMarks(is_overdue=overdue, is_today=task.due_date == today and not overdue)
