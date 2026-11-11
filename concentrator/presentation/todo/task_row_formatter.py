"""Display texts of a task: one table row, due date, overdue and today marks."""

from datetime import datetime
from typing import Final

from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.domain.common.multiline_text import MultilineText
from concentrator.domain.todo.due_marks import DueMarks, due_marks
from concentrator.domain.todo.link_detector import DetectedLink, LinkDetector
from concentrator.domain.todo.recurrence_end_enum import RecurrenceEndEnum
from concentrator.domain.todo.task import Task
from concentrator.domain.todo.task_sort_key_enum import TaskSortKeyEnum
from concentrator.domain.todo.task_state_enum import TaskStateEnum
from concentrator.presentation.common.date_time_formatter import DateTimeFormatter
from concentrator.presentation.common.row_tone_enum import RowToneEnum
from concentrator.presentation.common.table_snapshot import CellLinkSnapshot, TableRowSnapshot
from concentrator.presentation.todo.recurrence_summary_formatter import RecurrenceSummaryFormatter
from concentrator.presentation.todo.todo_texts import STATE_KEYS, UNKNOWN_KEY

STATE_COLUMN: Final = 0
"""Index of the check box column."""
FOCUS_COLUMN: Final = 1
"""Index of the focus star column (phase 7): a click queues or unqueues the task."""
TASK_COLUMN: Final = 2
"""Index of the column of the lines of the text."""
LIST_COLUMN: Final = 3
"""Index of the List column, shown only when the table shows every list."""

COLUMN_SORT_KEYS: Final[tuple[TaskSortKeyEnum | None, ...]] = (
    TaskSortKeyEnum.STATE,
    None,
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
    "todo.column.focus",
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
LINK_CACHE_SIZE: Final = 4096
"""Texts whose links are remembered (the texts are immutable; the cache empties when full)."""
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
        self._found: dict[MultilineText, tuple[DetectedLink, ...]] = {}
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

    def row(self, task: Task, now: datetime, list_name: str = "", *, queued: bool = False) -> TableRowSnapshot:
        """Describe one task.

        Args:
            task: Task.
            now: Current local time (due marks).
            list_name: Name of its list (List column).
            queued: Whether the task is in the focus queue (its star).

        Returns:
            The row keyed by the task id; the star of an open task can be clicked.
        """
        links = self.links(task.text)
        return TableRowSnapshot(
            key=task.id,
            cells=self._cells(task, list_name, len(links), queued=queued),
            tone=_tone(task, due_marks(task, now)),
            checked=task.state is not TaskStateEnum.OPEN,
            check_enabled=task.state in CHECKABLE_STATES,
            links=self._cell_links(task.text, links),
            overflow=self._translator.tr_plural("todo.table.overflow", task.text.line_count),
            toggle_enabled=task.state is TaskStateEnum.OPEN,
        )

    def _cell_links(self, text: MultilineText, links: tuple[DetectedLink, ...]) -> tuple[CellLinkSnapshot, ...]:
        """Place the links of a text in the task column, where its lines follow one another.

        Args:
            text: Text of the task.
            links: Its links.

        Returns:
            The links with their position in the cell text.
        """
        separator = len(self._translator.tr("todo.table.line_separator"))
        starts: list[int] = []
        position = 0
        for line in text.lines:
            starts.append(position)
            position += len(line) + separator
        return tuple(
            CellLinkSnapshot(
                column=TASK_COLUMN, start=starts[link.line] + link.start, end=starts[link.line] + link.end, index=number
            )
            for number, link in enumerate(links)
        )

    def _cells(self, task: Task, list_name: str, link_count: int, *, queued: bool) -> tuple[str, ...]:
        """Texts of the columns of a task.

        Args:
            task: Task.
            list_name: Name of its list.
            link_count: Number of links in its text.
            queued: Whether the task is in the focus queue.

        Returns:
            One text per column, in column order.
        """
        return (
            self._translator.tr(STATE_KEYS[TaskStateEnum.ARCHIVED]) if task.state is TaskStateEnum.ARCHIVED else "",
            self.focus_mark(task, queued=queued),
            self.title(task),
            list_name,
            self.due_text(task),
            "" if task.recurrence is None else self._summaries.short(task.recurrence),
            self.occurrences_text(task),
            str(link_count) if link_count else "",
            self._dates.date_time_minutes(task.created_at),
            self._dates.date_time_minutes(task.updated_at),
        )

    def focus_mark(self, task: Task, *, queued: bool) -> str:
        """Star of the Focus column.

        Args:
            task: Task.
            queued: Whether it is in the focus queue.

        Returns:
            A full star when queued, an empty one for another open task, ``""`` for a closed task.
        """
        if queued:
            return self._translator.tr("todo.table.focus_on")
        return self._translator.tr("todo.table.focus_off") if task.state is TaskStateEnum.OPEN else ""

    def links(self, text: MultilineText) -> tuple[DetectedLink, ...]:
        """Links of a text, found once per text.

        Args:
            text: Text of a task.

        Returns:
            Its links, in reading order.
        """
        found = self._found.get(text)
        if found is None:
            if len(self._found) >= LINK_CACHE_SIZE:
                self._found.clear()
            found = self._links.find(text)
            self._found[text] = found
        return found

    def title(self, task: Task) -> str:
        """Every line of a task, one after the other (owner request at the phase 6 review).

        Args:
            task: Task.

        Returns:
            The text of the Task column: ``Report  ·  with sources``.
        """
        return self._translator.tr("todo.table.line_separator").join(task.text.lines)

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
