"""History tab of the details pane (``TODO_HISTORY``): the events of the only selected task, newest first."""

from concentrator.application.ports.clock_port import ClockPort
from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.presentation.common.date_time_formatter import DateTimeFormatter
from concentrator.presentation.todo.task_history_formatter import TaskHistoryFormatter
from concentrator.presentation.todo.task_history_snapshot import TaskHistorySnapshot
from concentrator.presentation.todo.todo_view import TodoView


class TaskHistoryPresenter:
    """Builds ``TODO_HISTORY`` from the selection; the hint is the one of the Details tab."""

    def __init__(self, translator: TranslatorPort, clock: ClockPort, view: TodoView) -> None:
        """Create the presenter.

        Args:
            translator: Current-language translator.
            clock: Local time of the events.
            view: Selected tasks and lists.
        """
        self._translator = translator
        self._formatter = TaskHistoryFormatter(translator, DateTimeFormatter(translator, clock))
        self._view = view

    def build_snapshot(self) -> TaskHistorySnapshot:
        """Describe the tab now.

        Returns:
            The snapshot.
        """
        title = self._translator.tr("todo.history.title")
        selected = self._view.selected()
        if len(selected) != 1:
            empty = (
                self._translator.tr("todo.details.empty")
                if not selected
                else self._translator.tr_plural("todo.details.several", len(selected))
            )
            return TaskHistorySnapshot(title=title, lines=(), empty_text=empty)
        names: dict[str, str] = {item.id: item.name for item in self._view.lists()}
        events = reversed(selected[0].history.events)
        return TaskHistorySnapshot(
            title=title, lines=tuple(self._formatter.line(event, names) for event in events), empty_text=""
        )
