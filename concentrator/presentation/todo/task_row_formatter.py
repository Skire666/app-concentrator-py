"""Display texts of a task: one table row, due date, overdue and today marks."""

from dataclasses import dataclass
from datetime import datetime
from typing import Final

from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.domain.todo.task import Task
from concentrator.domain.todo.task_sort_key_enum import TaskSortKeyEnum
from concentrator.domain.todo.task_state_enum import TaskStateEnum
from concentrator.presentation.common.date_time_formatter import DateTimeFormatter
from concentrator.presentation.common.row_tone_enum import RowToneEnum
from concentrator.presentation.common.table_snapshot import TableRowSnapshot
from concentrator.presentation.todo.todo_texts import STATE_KEYS, UNKNOWN_KEY

STATE_COLUMN: Final = 0
"""Index of the check box column."""

COLUMN_SORT_KEYS: Final = (
    TaskSortKeyEnum.STATE,
    TaskSortKeyEnum.TEXT,
    TaskSortKeyEnum.DUE,
    TaskSortKeyEnum.CREATED,
    TaskSortKeyEnum.UPDATED,
)
"""Sort key of each column, in column order."""

COLUMN_KEYS: Final = (
    "todo.column.state",
    "todo.column.task",
    "todo.column.due",
    "todo.column.created",
    "todo.column.updated",
)
"""Header of each column, in column order."""

SEPARATOR: Final = " "
CHECKABLE_STATES: Final = frozenset({TaskStateEnum.OPEN, TaskStateEnum.DONE})


@dataclass(frozen=True, slots=True, kw_only=True)
class DueMarks:
    """Emphasis of an open task's due date.

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


def _tone(task: Task, marks: DueMarks) -> RowToneEnum:
    """Emphasis of a row.

    Args:
        task: Task.
        marks: Due marks.

    Returns:
        ERROR when overdue, WARNING when due today, MUTED when done or archived, NORMAL otherwise.
    """
    if marks.is_overdue:
        return RowToneEnum.ERROR
    if marks.is_today:
        return RowToneEnum.WARNING
    return RowToneEnum.NORMAL if task.state is TaskStateEnum.OPEN else RowToneEnum.MUTED


class TaskRowFormatter:
    """Builds the rows of the task table and the texts of the details pane in the current language."""

    def __init__(self, translator: TranslatorPort, dates: DateTimeFormatter) -> None:
        """Create the formatter.

        Args:
            translator: Current-language translator.
            dates: Date and time templates.
        """
        self._translator = translator
        self._dates = dates

    def columns(self) -> tuple[str, ...]:
        """Headers of the table.

        Returns:
            One text per column.
        """
        return tuple(self._translator.tr(key) for key in COLUMN_KEYS)

    def row(self, task: Task, now: datetime) -> TableRowSnapshot:
        """Describe one task.

        Args:
            task: Task.
            now: Current local time (due marks).

        Returns:
            The row keyed by the task id.
        """
        marks = due_marks(task, now)
        cells = (
            self._translator.tr(STATE_KEYS[TaskStateEnum.ARCHIVED]) if task.state is TaskStateEnum.ARCHIVED else "",
            self.title(task),
            self.due_text(task),
            self._dates.date_time_minutes(task.created_at),
            self._dates.date_time_minutes(task.updated_at),
        )
        return TableRowSnapshot(
            key=task.id,
            cells=cells,
            tone=_tone(task, marks),
            checked=task.state is not TaskStateEnum.OPEN,
            check_enabled=task.state in CHECKABLE_STATES,
        )

    def title(self, task: Task) -> str:
        """First line of a task, with a mark when the text has more lines.

        Args:
            task: Task.

        Returns:
            The text of the Task column.
        """
        more = task.text.line_count - 1
        if more <= 0:
            return task.text.first_line
        return task.text.first_line + SEPARATOR + self._translator.tr_plural("todo.table.more_lines", more)

    def due_text(self, task: Task) -> str:
        """Due date and time.

        Args:
            task: Task.

        Returns:
            ``10/11/2026 14:30``, the date alone, or ``""`` without a due date.
        """
        if task.due_date is None:
            return ""
        text = self._dates.calendar_date(task.due_date)
        if task.due_time is None:
            return text
        return text + SEPARATOR + self._dates.clock_time(task.due_time)

    def state_text(self, state: TaskStateEnum) -> str:
        """Name of a state.

        Args:
            state: State.

        Returns:
            The translated name.
        """
        return self._translator.tr(STATE_KEYS.get(state, UNKNOWN_KEY))
