"""The tasks of every list."""

from collections import Counter
from collections.abc import Callable, Collection
from datetime import date, datetime, time
from typing import Final, Self

from concentrator.domain.common.entity_collection import EntityCollection
from concentrator.domain.todo.task import Task
from concentrator.domain.todo.task_sort_key_enum import TaskSortKeyEnum
from concentrator.domain.todo.task_state_enum import TaskStateEnum

type _SortValue = int | str | datetime | tuple[date, time]


def _due(task: Task) -> tuple[date, time]:
    """Sort value of a due date; a date without time sorts as the end of that day.

    Args:
        task: A task with a due date.

    Returns:
        The date and time.
    """
    return (task.due_date or date.min, task.due_time or time.max)


_SORT_VALUES: Final[dict[TaskSortKeyEnum, Callable[[Task], _SortValue]]] = {
    TaskSortKeyEnum.STATE: lambda task: task.state.value,
    TaskSortKeyEnum.TEXT: lambda task: task.text.as_text().casefold(),
    TaskSortKeyEnum.DUE: _due,
    TaskSortKeyEnum.CREATED: lambda task: task.created_at,
    TaskSortKeyEnum.UPDATED: lambda task: task.updated_at,
}


class TasksCollection(EntityCollection[Task]):
    """Group logic of the tasks: per-list views, state filters and sorting."""

    def in_list(self, list_id: str) -> Self:
        """Keep the tasks of one list.

        Args:
            list_id: List id.

        Returns:
            Its tasks, in stored order.
        """
        return self.filtered(lambda task: task.list_id == list_id)

    def with_states(self, states: Collection[TaskStateEnum]) -> Self:
        """Keep the tasks in some states.

        Args:
            states: Accepted states.

        Returns:
            The matching tasks.
        """
        return self.filtered(lambda task: task.state in states)

    def open_counts(self) -> Counter[str]:
        """Count the open tasks of every list in one pass.

        Returns:
            Open tasks per list id (missing lists count 0).
        """
        return Counter(task.list_id for task in self if task.state is TaskStateEnum.OPEN)

    def ordered_by(self, key: TaskSortKeyEnum, *, descending: bool) -> Self:
        """Sort the tasks by a column; ties keep the id order (creation order of UUIDv7 ids).

        Tasks without a due date stay last when sorting by due date, in both orders. An unknown key sorts
        by creation instant.

        Args:
            key: Column.
            descending: Highest values first.

        Returns:
            The sorted tasks.
        """
        value = _SORT_VALUES.get(key, _SORT_VALUES[TaskSortKeyEnum.CREATED])
        if key is not TaskSortKeyEnum.DUE:
            return self.sorted_by(lambda task: (value(task), task.id), reverse=descending)
        dated = sorted((task for task in self if task.due_date is not None), key=lambda task: (_due(task), task.id))
        undated = sorted((task for task in self if task.due_date is None), key=lambda task: task.id)
        if descending:
            dated.reverse()
            undated.reverse()
        return self._with_items((*dated, *undated))
