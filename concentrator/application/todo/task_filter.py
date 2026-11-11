"""Due date and repetition filters of the task table (phase 6)."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Final

from concentrator.application.todo.due_filter_enum import DueFilterEnum
from concentrator.domain.todo.due_marks import due_marks
from concentrator.domain.todo.task import Task

DAYS_AHEAD: Final = 6
"""Days after today of "Next 7 days" and after Monday of "This week" (today or Monday counts as the first)."""


def _monday(day: date) -> date:
    """Monday of the week of a date.

    Args:
        day: Any date.

    Returns:
        The Monday.
    """
    return day - timedelta(days=day.weekday())


def _between(task: Task, first: date, last: date) -> bool:
    """Tell whether a task is due within two dates.

    Args:
        task: Task.
        first: First day, included.
        last: Last day, included.

    Returns:
        Whether its due date is in the range.
    """
    return task.due_date is not None and first <= task.due_date <= last


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskFilter:
    """Due date filter and "Recurring only"; the states and the list are part of ``TaskQuery``.

    Attributes:
        due: Which due dates are shown.
        recurring_only: Only the tasks that repeat.
    """

    due: DueFilterEnum = DueFilterEnum.ALL
    recurring_only: bool = False

    @property
    def is_active(self) -> bool:
        """Whether the filter hides any task."""
        return self.recurring_only or self.due is not DueFilterEnum.ALL

    @property
    def depends_on_time(self) -> bool:
        """Whether the result changes with the clock (any due filter but All, With date and No date)."""
        return self.due not in {DueFilterEnum.ALL, DueFilterEnum.WITH_DATE, DueFilterEnum.NO_DATE}

    def matches(self, task: Task, now: datetime) -> bool:
        """Tell whether the table shows a task.

        Args:
            task: Task.
            now: Current local time (Overdue compares the due time too, as the table marks do).

        Returns:
            Whether it passes both filters.
        """
        if self.recurring_only and task.recurrence is None:
            return False
        return self._due_matches(task, now)

    def _due_matches(self, task: Task, now: datetime) -> bool:
        """Apply the due date filter.

        Args:
            task: Task.
            now: Current local time.

        Returns:
            Whether its due date passes (an unknown filter shows every task).
        """
        today = now.date()
        match self.due:
            case DueFilterEnum.OVERDUE:
                return due_marks(task, now).is_overdue
            case DueFilterEnum.TODAY:
                return task.due_date == today
            case DueFilterEnum.THIS_WEEK:
                return _between(task, _monday(today), _monday(today) + timedelta(days=DAYS_AHEAD))
            case DueFilterEnum.NEXT_7_DAYS:
                return _between(task, today, today + timedelta(days=DAYS_AHEAD))
            case DueFilterEnum.WITH_DATE:
                return task.due_date is not None
            case DueFilterEnum.NO_DATE:
                return task.due_date is None
            case _:
                return True
