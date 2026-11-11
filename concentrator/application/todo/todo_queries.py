"""Read use cases of the TODO manager."""

from collections import Counter
from dataclasses import dataclass
from datetime import datetime

from concentrator.application.ports.task_list_reader_port import TaskListReaderPort
from concentrator.application.ports.task_reader_port import TaskReaderPort
from concentrator.application.todo.task_query import TaskQuery
from concentrator.domain.common.data_result import DataResult
from concentrator.domain.todo.task import Task
from concentrator.domain.todo.task_list import TaskList
from concentrator.domain.todo.task_lists_collection import TaskListsCollection
from concentrator.domain.todo.tasks_collection import TasksCollection


@dataclass(frozen=True, slots=True, kw_only=True)
class ListOverview:
    """One tab: a list and its number of tasks.

    Attributes:
        task_list: The list.
        open_count: Its open tasks.
        task_count: All its tasks, whatever their state.
    """

    task_list: TaskList
    open_count: int
    task_count: int


class TodoQueries:
    """Lists in tab order with their open counts, and the tasks of a list for a ``TaskQuery``."""

    def __init__(self, lists: TaskListReaderPort, tasks: TaskReaderPort) -> None:
        """Create the queries.

        Args:
            lists: Lists reader.
            tasks: Tasks reader.
        """
        self._lists = lists
        self._tasks = tasks

    def lists(self) -> TaskListsCollection:
        """Return the lists in tab order.

        Returns:
            The lists (empty if the in-memory read ever failed).
        """
        return self._lists.all_items().value_or(TaskListsCollection()).ordered()

    def overviews(self) -> tuple[ListOverview, ...]:
        """Return the tabs: every list in tab order with its open tasks.

        Returns:
            The overviews.
        """
        tasks = self.all_tasks()
        open_counts = tasks.open_counts()
        task_counts = Counter(task.list_id for task in tasks)
        return tuple(
            ListOverview(task_list=item, open_count=open_counts[item.id], task_count=task_counts[item.id])
            for item in self.lists()
        )

    def task_list(self, list_id: str) -> DataResult[TaskList]:
        """Return one list.

        Args:
            list_id: Id of the list.

        Returns:
            The list, or ``ENTITY_NOT_FOUND``.
        """
        return self._lists.read_item(list_id)

    def all_tasks(self) -> TasksCollection:
        """Return every task, in stored order.

        Returns:
            The tasks (empty if the in-memory read ever failed).
        """
        return self._tasks.all_items().value_or(TasksCollection())

    def tasks(self, query: TaskQuery, now: datetime) -> TasksCollection:
        """Return the tasks a table shows: one list or all, some states, due date filter, sorted.

        Args:
            query: Scope, states, filters and order.
            now: Current local time (due date filters).

        Returns:
            The tasks in display order.
        """
        shown = self.in_scope(query).with_states(query.states)
        task_filter = query.task_filter
        if task_filter.is_active:
            shown = shown.filtered(lambda task: task_filter.matches(task, now))
        return shown.ordered_by(query.sort_key, descending=query.descending)

    def in_scope(self, query: TaskQuery) -> TasksCollection:
        """Return every task of the scope of a query, whatever its state (the total of the counter).

        Args:
            query: List and scope.

        Returns:
            The tasks, in stored order.
        """
        tasks = self.all_tasks()
        return tasks if query.all_lists else tasks.in_list(query.list_id)

    def task(self, task_id: str) -> DataResult[Task]:
        """Return one task.

        Args:
            task_id: Id of the task.

        Returns:
            The task, or ``ENTITY_NOT_FOUND``.
        """
        return self._tasks.read_item(task_id)

    def task_count(self, list_id: str) -> int:
        """Count every task of a list, whatever its state (the delete question of a list).

        Args:
            list_id: Id of the list.

        Returns:
            The number of tasks.
        """
        return len(self.all_tasks().in_list(list_id))
