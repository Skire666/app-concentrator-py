"""Details pane under the table (``TODO_DETAILS``): the selected task in full."""

from concentrator.application.ports.clock_port import ClockPort
from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.domain.todo.task import Task
from concentrator.presentation.common.date_time_formatter import DateTimeFormatter
from concentrator.presentation.todo.task_details_snapshot import DetailRowSnapshot, TaskDetailsSnapshot
from concentrator.presentation.todo.task_row_formatter import TaskRowFormatter
from concentrator.presentation.todo.todo_view import TodoView


class TaskDetailsPresenter:
    """Shows the full text, list, due date, state and dates of the only selected task."""

    def __init__(self, translator: TranslatorPort, clock: ClockPort, view: TodoView) -> None:
        """Create the presenter.

        Args:
            translator: Current-language translator.
            clock: Local time of the dates.
            view: Selected tasks and lists.
        """
        self._translator = translator
        self._dates = DateTimeFormatter(translator, clock)
        self._rows = TaskRowFormatter(translator, self._dates)
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
            return TaskDetailsSnapshot(title=title, text="", rows=(), empty_text=empty)
        task = selected[0]
        return TaskDetailsSnapshot(title=title, text=task.text.as_text(), rows=self._rows_of(task), empty_text="")

    def _rows_of(self, task: Task) -> tuple[DetailRowSnapshot, ...]:
        """Labels and values of a task.

        Args:
            task: Selected task.

        Returns:
            List, due, state, created, updated.
        """
        tr = self._translator.tr
        task_list = next((item for item in self._view.lists() if item.id == task.list_id), None)
        due = self._rows.due_text(task) or tr("todo.details.no_due")
        return (
            DetailRowSnapshot(label=tr("todo.details.list"), value="" if task_list is None else task_list.name),
            DetailRowSnapshot(label=tr("todo.details.due"), value=due),
            DetailRowSnapshot(label=tr("todo.details.state"), value=self._rows.state_text(task.state)),
            DetailRowSnapshot(label=tr("todo.details.created"), value=self._dates.date_time_minutes(task.created_at)),
            DetailRowSnapshot(label=tr("todo.details.updated"), value=self._dates.date_time_minutes(task.updated_at)),
        )
