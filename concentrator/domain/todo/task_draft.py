"""Editable values of a task: the draft of the task editor and the input of the task commands."""

from dataclasses import dataclass
from datetime import date, time
from typing import Final

from concentrator.domain.common.multiline_text import MultilineText
from concentrator.domain.todo.recurrence import Recurrence
from concentrator.domain.todo.task_list import TaskListId

_DATE_TIME_SEPARATOR: Final = "T"
_MINUTES_FORMAT: Final = "%H:%M"


def due_text(due_date: date | None, due_time: time | None) -> str:
    """ISO text of a due date and time, for the history details.

    Args:
        due_date: Due date, or ``None``.
        due_time: Due time, or ``None``.

    Returns:
        ``""``, ``2026-11-10`` or ``2026-11-10T14:30``.
    """
    if due_date is None:
        return ""
    if due_time is None:
        return due_date.isoformat()
    return f"{due_date.isoformat()}{_DATE_TIME_SEPARATOR}{due_time.strftime(_MINUTES_FORMAT)}"


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskDraft:
    """What the user edits in a task; checked by ``TaskRules.validate_draft``.

    Attributes:
        list_id: List of the task.
        text: Text, first line shown in the table.
        due_date: Due date (local), ``None`` for no date.
        due_time: Due time (local, minutes), ``None`` for the whole day; requires a date.
        recurrence: Repetition, ``None`` for a one-off task; requires a date. Its anchor follows a due date
            changed by hand (``anchored``).
    """

    list_id: TaskListId
    text: MultilineText
    due_date: date | None = None
    due_time: time | None = None
    recurrence: Recurrence | None = None
