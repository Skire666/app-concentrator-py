"""Details pane under the table (``TODO_DETAILS``): the selected task in full, its links clickable."""

from concentrator.application.ports.clock_port import ClockPort
from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.domain.todo.link_detector import LinkDetector
from concentrator.domain.todo.task import Task
from concentrator.presentation.common.date_time_formatter import DateTimeFormatter
from concentrator.presentation.todo.task_details_snapshot import (
    DetailRowSnapshot,
    TaskDetailsSnapshot,
    TextLineSnapshot,
)
from concentrator.presentation.todo.task_row_formatter import TaskRowFormatter
from concentrator.presentation.todo.todo_view import TodoView


class TaskDetailsPresenter:
    """Shows the full text, list, due date, repetition, state and dates of the only selected task."""

    def __init__(self, translator: TranslatorPort, clock: ClockPort, view: TodoView, links: LinkDetector) -> None:
        """Create the presenter.

        Args:
            translator: Current-language translator.
            clock: Local time of the dates.
            view: Selected tasks and lists.
            links: Finds the links of the text.
        """
        self._translator = translator
        self._dates = DateTimeFormatter(translator, clock)
        self._rows = TaskRowFormatter(translator, self._dates, links)
        self._links = links
        self._view = view

    def build_snapshot(self) -> TaskDetailsSnapshot:
        """Describe the pane now.

        Returns:
            The snapshot: the task, or a hint when no task or several tasks are selected.
        """
        tr = self._translator.tr
        selected = self._view.selected()
        title = tr("todo.details.title")
        if len(selected) != 1:
            empty = (
                tr("todo.details.empty")
                if not selected
                else self._translator.tr_plural("todo.details.several", len(selected))
            )
            return TaskDetailsSnapshot(title=title, lines=(), rows=(), empty_text=empty)
        task = selected[0]
        return TaskDetailsSnapshot(title=title, lines=self._lines(task), rows=self._rows_of(task), empty_text="")

    def _lines(self, task: Task) -> tuple[TextLineSnapshot, ...]:
        """Lines of the text with their links, numbered in reading order.

        Args:
            task: Selected task.

        Returns:
            One snapshot per line.
        """
        found = {link.line: (number, link) for number, link in enumerate(self._links.find(task.text))}
        lines: list[TextLineSnapshot] = []
        for index, line in enumerate(task.text.lines):
            entry = found.get(index)
            if entry is None:
                lines.append(TextLineSnapshot(text=line))
                continue
            number, link = entry
            lines.append(TextLineSnapshot(text=line, link_start=link.start, link_end=link.end, link_index=number))
        return tuple(lines)

    def _repeat_rows(self, task: Task) -> tuple[DetailRowSnapshot, ...]:
        """Repetition and occurrences of a recurring task.

        Args:
            task: Selected task.

        Returns:
            Two rows, ``()`` for a one-off task.
        """
        if task.recurrence is None:
            return ()
        tr = self._translator.tr
        return (
            DetailRowSnapshot(label=tr("todo.details.repeat"), value=self._rows.summaries.full(task.recurrence)),
            DetailRowSnapshot(label=tr("todo.details.occurrences"), value=self._rows.occurrences_text(task)),
        )

    def _rows_of(self, task: Task) -> tuple[DetailRowSnapshot, ...]:
        """Labels and values of a task.

        Args:
            task: Selected task.

        Returns:
            List, due, repeat and occurrences (repeating tasks), state, created, updated.
        """
        tr = self._translator.tr
        task_list = next((item for item in self._view.lists() if item.id == task.list_id), None)
        due = self._rows.due_text(task) or tr("todo.details.no_due")
        rows = [
            DetailRowSnapshot(label=tr("todo.details.list"), value="" if task_list is None else task_list.name),
            DetailRowSnapshot(label=tr("todo.details.due"), value=due),
        ]
        rows.extend(self._repeat_rows(task))
        rows += [
            DetailRowSnapshot(label=tr("todo.details.state"), value=self._rows.state_text(task.state)),
            DetailRowSnapshot(label=tr("todo.details.created"), value=self._dates.date_time_minutes(task.created_at)),
            DetailRowSnapshot(label=tr("todo.details.updated"), value=self._dates.date_time_minutes(task.updated_at)),
        ]
        return tuple(rows)
