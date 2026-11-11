"""Display texts of a task: one table row, due date, overdue and today marks."""

from datetime import datetime
from typing import Final

from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.domain.todo.due_marks import DueMarks, due_marks
from concentrator.domain.todo.link_detector import LinkDetector
from concentrator.domain.todo.recurrence_end_enum import RecurrenceEndEnum
from concentrator.domain.todo.task import Task
from concentrator.domain.todo.task_sort_key_enum import TaskSortKeyEnum
from concentrator.domain.todo.task_state_enum import TaskStateEnum
from concentrator.presentation.common.date_time_formatter import DateTimeFormatter
from concentrator.presentation.common.row_tone_enum import RowToneEnum
from concentrator.presentation.common.table_snapshot import TableRowSnapshot
from concentrator.presentation.todo.recurrence_summary_formatter import RecurrenceSummaryFormatter
from concentrator.presentation.todo.todo_texts import STATE_KEYS, UNKNOWN_KEY

STATE_COLUMN: Final = 0
"""Index of the check box column."""
TASK_COLUMN: Final = 1
"""Index of the column of the first line of the text."""
LIST_COLUMN: Final = 2
"""Index of the List column, shown only when the table shows every list."""

COLUMN_SORT_KEYS: Final[tuple[TaskSortKeyEnum | None, ...]] = (
    TaskSortKeyEnum.STATE,
    TaskSortKeyEnum.TEXT,
    None,
    TaskSortKeyEnum.DUE,
    None,
    None,
    None,
    TaskSortKeyEnum.CREATED,
    TaskSortKeyEnum.UPDATED,
)
"""Sort key of each column, in column order (``None``: the column does not sort)."""

COLUMN_KEYS: Final = (
    "todo.column.state",
    "todo.column.task",
    "todo.column.list",
    "todo.column.due",
    "todo.column.repeat",
    "todo.column.occurrences",
    "todo.column.links",
    "todo.column.created",
    "todo.column.updated",
)
"""Header of each column, in column order."""

SEPARATOR: Final = " "
CHECKABLE_STATES: Final = frozenset({TaskStateEnum.OPEN, TaskStateEnum.DONE})


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

    def __init__(self, translator: TranslatorPort, dates: DateTimeFormatter, links: LinkDetector) -> None:
        """Create the formatter.

        Args:
            translator: Current-language translator.
            dates: Date and time templates.
            links: Counts the links of a text.
        """
        self._translator = translator
        self._dates = dates
        self._links = links
        self._summaries = RecurrenceSummaryFormatter(translator, dates)

    @property
    def summaries(self) -> RecurrenceSummaryFormatter:
        """Texts of the recurrences."""
        return self._summaries

    def columns(self) -> tuple[str, ...]:
        """Headers of the table.

        Returns:
            One text per column.
        """
        return tuple(self._translator.tr(key) for key in COLUMN_KEYS)

    def row(self, task: Task, now: datetime, list_name: str = "") -> TableRowSnapshot:
        """Describe one task.

        Args:
            task: Task.
            now: Current local time (due marks).
            list_name: Name of its list (List column).

        Returns:
            The row keyed by the task id.
        """
        marks = due_marks(task, now)
        link_count = len(self._links.find(task.text))
        cells = (
            self._translator.tr(STATE_KEYS[TaskStateEnum.ARCHIVED]) if task.state is TaskStateEnum.ARCHIVED else "",
            self.title(task),
            list_name,
            self.due_text(task),
            "" if task.recurrence is None else self._summaries.short(task.recurrence),
            self.occurrences_text(task),
            str(link_count) if link_count else "",
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

    def occurrences_text(self, task: Task) -> str:
        """Occurrences completed, out of the count of a series that ends after a count.

        Args:
            task: Task.

        Returns:
            ``3 / 10``, ``3``, or ``""`` for a one-off task.
        """
        recurrence = task.recurrence
        if recurrence is None:
            return ""
        if recurrence.end_kind is RecurrenceEndEnum.AFTER_COUNT and recurrence.end_count is not None:
            return self._translator.tr(
                "todo.table.occurrences_of", done=task.occurrences_done, count=recurrence.end_count
            )
        return str(task.occurrences_done)

    def state_text(self, state: TaskStateEnum) -> str:
        """Name of a state.

        Args:
            state: State.

        Returns:
            The translated name.
        """
        return self._translator.tr(STATE_KEYS.get(state, UNKNOWN_KEY))
