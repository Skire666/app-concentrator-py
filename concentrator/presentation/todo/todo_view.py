"""The lists and tasks the TODO manager shows now, read once per change of the data or of the view."""

from datetime import datetime

from concentrator.application.ports.clock_port import ClockPort
from concentrator.application.todo.task_query import TaskQuery
from concentrator.application.todo.todo_queries import ListOverview, TodoQueries
from concentrator.domain.common.multiline_text import MultilineText
from concentrator.domain.todo.task import Task
from concentrator.domain.todo.task_list import TaskList
from concentrator.domain.todo.task_lists_collection import TaskListsCollection
from concentrator.domain.todo.tasks_collection import TasksCollection
from concentrator.presentation.common.text_search import TextSearch, fold
from concentrator.presentation.todo.todo_view_state import TodoViewState


def _kept_in_place(tasks: TasksCollection, order: tuple[str, ...]) -> TasksCollection:
    """Keep the tasks already shown in the order they had; new tasks keep the place of the sort.

    The places the sort gives to tasks already shown are filled with those tasks in their previous order,
    so a task that changed (ticked, moved to its next date) does not jump, and a new task appears where
    the sort puts it (at the top for the newest first).

    Args:
        tasks: Tasks to show, filtered and sorted.
        order: Ids of the tasks shown before, in table order.

    Returns:
        The tasks in display order.
    """
    rank = {task_id: index for index, task_id in enumerate(order)}
    known = iter(sorted((task for task in tasks if task.id in rank), key=lambda task: rank[task.id]))
    return TasksCollection([next(known) if task.id in rank else task for task in tasks])


class TodoView:
    """Joins the queries and the view state; the tasks of the table are filtered and sorted once.

    The stored tasks are immutable: a new collection means new data, so the visible tasks are rebuilt
    only when the stored collection or the query changes (the tabs, toolbar, table and details panes all
    read them in the same render), or, with a due date filter that depends on the clock, when the local
    minute changes. The search runs on every line of the text, folded once per text (case and accents
    ignored).

    The rows keep their places while the user works on them (owner decision, phase 6 review): after a
    change of the data, the tasks already shown stay in the order they had, and only new tasks take the
    place the sort gives them. A new query (list, sort, filters, scope, search) sorts everything again.

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
        self._search = TextSearch()
        self._folded: dict[MultilineText, str] = {}
        self._order: tuple[str, ...] = ()
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

    def scope_total(self) -> int:
        """Count every task of the scope (the current list, or every list), whatever its state and filters.

        Returns:
            The total of the counter "12 of 87 tasks".
        """
        self._follow_data()
        return len(self._queries.in_scope(self._state.query()))

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

    def sort_again(self) -> None:
        """Forget the order shown: the next read sorts every task (another file, Reset layout)."""
        self._order = ()
        self._source = None

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
        search = self._state.search
        if source is not self._source or query != self._query or minute != self._minute or search != self._search:
            same_view = query == self._query and search == self._search
            self._source = source
            self._query = query
            self._minute = minute
            self._search = search
            visible = self._searched(self._queries.tasks(query, now), search)
            self._visible = _kept_in_place(visible, self._order) if same_view else visible
            self._order = tuple(task.id for task in self._visible)
        return self._visible

    def _searched(self, tasks: TasksCollection, search: TextSearch) -> TasksCollection:
        """Keep the tasks whose text holds every word of the search.

        Args:
            tasks: Filtered and sorted tasks.
            search: Search typed.

        Returns:
            The matching tasks, in the same order.
        """
        if search.is_empty:
            return tasks
        if len(self._folded) > 2 * len(tasks) + 1:
            self._folded.clear()
        return tasks.filtered(lambda task: search.matches(self._fold(task.text)))

    def _fold(self, text: MultilineText) -> str:
        """Folded form of a text, computed once per text.

        Args:
            text: Text of a task.

        Returns:
            The text without case and accents, its lines joined.
        """
        folded = self._folded.get(text)
        if folded is None:
            folded = fold(text.as_text())
            self._folded[text] = folded
        return folded
