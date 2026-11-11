"""Re-renders the TODO manager when its data changes, another file opens or the layout is reset."""

from concentrator.application.storage.storage_events import UserDataReplacedEvent
from concentrator.application.todo.todo_events import (
    TaskChangedEvent,
    TaskCreatedEvent,
    TaskDeletedEvent,
    TaskListChangedEvent,
    TaskOccurrenceCompletedEvent,
    TaskStateChangedEvent,
)
from concentrator.presentation.common.render_coordinator import RenderCoordinator
from concentrator.presentation.todo.todo_tabs_presenter import TODO_SECTIONS
from concentrator.presentation.todo.todo_view import TodoView

type TodoDataEvent = (
    TaskListChangedEvent
    | TaskCreatedEvent
    | TaskChangedEvent
    | TaskStateChangedEvent
    | TaskOccurrenceCompletedEvent
    | TaskDeletedEvent
)


class TodoRefresher:
    """Keeps the view consistent with the data (existing list, visible selection) and requests the renders."""

    def __init__(self, view: TodoView, renderer: RenderCoordinator) -> None:
        """Create the refresher.

        Args:
            view: Current list and selection.
            renderer: Receives the render requests.
        """
        self._view = view
        self._renderer = renderer

    def on_todo_changed(self, _event: TodoDataEvent) -> None:
        """A list or a task changed.

        Args:
            _event: Published by the TODO use cases.
        """
        self._refresh()

    def on_user_data_replaced(self, _event: UserDataReplacedEvent) -> None:
        """Another data file was opened or the file was reloaded.

        Args:
            _event: Published by the storage use cases.
        """
        self._view.state.select_tasks(())
        self._refresh()

    def reset_layout(self) -> None:
        """Back to the ``[todo]`` defaults once "Reset layout" removed the stored sort and toggles."""
        self._view.state.reset()
        self._refresh()

    def _refresh(self) -> None:
        """Follow the data at the next read (once for a bulk change) and request every TODO section."""
        self._view.mark_stale()
        self._renderer.request(*TODO_SECTIONS)
