"""The lists and tasks the TODO manager shows now, read once per change of the data or of the view."""

from datetime import datetime

from concentrator.application.ports.clock_port import ClockPort
from concentrator.application.todo.task_query import TaskQuery
from concentrator.application.todo.todo_queries import ListOverview, TodoQueries
from concentrator.domain.todo.task import Task
from concentrator.domain.todo.task_list import TaskList
from concentrator.domain.todo.task_lists_collection import TaskListsCollection
from concentrator.domain.todo.tasks_collection import TasksCollection
from concentrator.presentation.todo.todo_view_state import TodoViewState


class TodoView:
    """Joins the queries and the view state; the tasks of the table are filtered and sorted once.

    The stored tasks are immutable: a new collection means new data, so the visible tasks are rebuilt
    only when the stored collection or the query changes (the tabs, toolbar, table and details panes all
    read them in the same render), or, with a due date filter that depends on the clock, when the local
    minute changes.

    After a change of the data, ``mark_stale`` defers the follow-up (show an existing list, drop vanished
    tasks from the selection) to the next read: a bulk change publishes one event per task, and following
    the data once per event would cost the square of the number of tasks (code review of phase 5).
    """

    def __init__(self, queries: TodoQueries, state: TodoViewState, clock: ClockPort) -> None:
        """Create the view.

        Args:
            queries: Lists and tasks.
            state: Current list, sort, filters and selection.
            clock: Local time of the due date filters.
        """
        self._queries = queries
        self._state = state
        self._clock = clock
        self._source: TasksCollection | None = None
        self._query: TaskQuery | None = None
        self._minute: datetime | None = None
        self._visible = TasksCollection()
        self._stale = True

    @property
    def state(self) -> TodoViewState:
        """Current list, sort, filters and selection (read ``list_id`` here once the data changed)."""
        return self._state

    @property
    def list_id(self) -> str:
        """Current list, an existing one once the data changed."""
        self._follow_data()
        return self._state.list_id

    def lists(self) -> TaskListsCollection:
        """Return the lists in tab order.

        Returns:
            The lists.
        """
        self._follow_data()
        return self._queries.lists()

    def overviews(self) -> tuple[ListOverview, ...]:
        """Return the tabs with their open tasks.

        Returns:
            The overviews.
        """
        self._follow_data()
        return self._queries.overviews()

    def current_list(self) -> TaskList | None:
        """Return the list shown.

        Returns:
            The list, ``None`` when it does not exist.
        """
        return self._queries.task_list(self.list_id).data

    def visible(self) -> TasksCollection:
        """Return the tasks of the table, in display order.

        Returns:
            The tasks of the current list, filtered and sorted.
        """
        self._follow_data()
        return self._current_tasks()

    def selected(self) -> tuple[Task, ...]:
        """Return the selected tasks that the table shows, in table order.

        Returns:
            The tasks.
        """
        visible = self.visible()
        selected = set(self._state.selected_ids)
        return tuple(task for task in visible if task.id in selected)

    def mark_stale(self) -> None:
        """The data changed: follow it at the next read."""
        self._stale = True

    def sync(self) -> None:
        """Follow the data now (startup)."""
        self._stale = True
        self._follow_data()

    def _follow_data(self) -> None:
        """Once after a change of the data: show an existing list and drop vanished tasks from the selection."""
        if not self._stale:
            return
        self._stale = False
        self._state.follow_lists(self._queries.lists())
        self._state.keep_visible(task.id for task in self._current_tasks())

    def _current_tasks(self) -> TasksCollection:
        """Filter and sort the tasks of the current list when the data or the query changed.

        Returns:
            The tasks of the table.
        """
        source = self._queries.all_tasks()
        query = self._state.query()
        now = self._clock.now_local()
        minute = now.replace(second=0, microsecond=0) if query.task_filter.depends_on_time else None
        if source is not self._source or query != self._query or minute != self._minute:
            self._source = source
            self._query = query
            self._minute = minute
            self._visible = self._queries.tasks(query, now)
        return self._visible
