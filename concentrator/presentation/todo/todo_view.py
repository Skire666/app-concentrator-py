"""The lists and tasks the TODO manager shows now, read once per change of the data or of the view."""

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
    read them in the same render).
    """

    def __init__(self, queries: TodoQueries, state: TodoViewState) -> None:
        """Create the view.

        Args:
            queries: Lists and tasks.
            state: Current list, sort, filters and selection.
        """
        self._queries = queries
        self._state = state
        self._source: TasksCollection | None = None
        self._query: TaskQuery | None = None
        self._visible = TasksCollection()

    @property
    def state(self) -> TodoViewState:
        """Current list, sort, filters and selection."""
        return self._state

    def lists(self) -> TaskListsCollection:
        """Return the lists in tab order.

        Returns:
            The lists.
        """
        return self._queries.lists()

    def overviews(self) -> tuple[ListOverview, ...]:
        """Return the tabs with their open tasks.

        Returns:
            The overviews.
        """
        return self._queries.overviews()

    def current_list(self) -> TaskList | None:
        """Return the list shown.

        Returns:
            The list, ``None`` when it does not exist.
        """
        return self._queries.task_list(self._state.list_id).data

    def visible(self) -> TasksCollection:
        """Return the tasks of the table, in display order.

        Returns:
            The tasks of the current list, filtered and sorted.
        """
        source = self._queries.all_tasks()
        query = self._state.query()
        if source is not self._source or query != self._query:
            self._source = source
            self._query = query
            self._visible = self._queries.tasks(query)
        return self._visible

    def selected(self) -> tuple[Task, ...]:
        """Return the selected tasks that the table shows, in table order.

        Returns:
            The tasks.
        """
        selected = set(self._state.selected_ids)
        return tuple(task for task in self.visible() if task.id in selected)

    def sync(self) -> None:
        """After a change of the data: show an existing list and drop vanished tasks from the selection."""
        self._state.follow_lists(self.lists())
        self._state.keep_visible(task.id for task in self.visible())
