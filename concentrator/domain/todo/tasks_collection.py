"""The tasks of every list."""

from collections import Counter
from collections.abc import Callable, Collection, Iterable
from datetime import date, datetime, time
from typing import Final, Self

from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.entity_collection import EntityCollection
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.todo.task import Task
from concentrator.domain.todo.task_sort_key_enum import TaskSortKeyEnum
from concentrator.domain.todo.task_state_enum import TaskStateEnum

ID_FIELD: Final = "id"

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


def _not_found() -> ValidationResult:
    """Failure of an operation on a missing task.

    Returns:
        ``ENTITY_NOT_FOUND`` on ``id``.
    """
    return ValidationResult.failure(ErrorCodeEnum.ENTITY_NOT_FOUND, field=ID_FIELD)


class TasksCollection(EntityCollection[Task]):
    """Group logic of the tasks: per-list views, state filters, sorting and changes of several tasks at once."""

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

    def with_replaced_all(self, tasks: Iterable[Task]) -> DataResult[Self]:
        """Replace several tasks at once, all or nothing, keeping their positions.

        Args:
            tasks: New versions of existing tasks.

        Returns:
            The new collection, or ``ENTITY_NOT_FOUND`` when one of them does not exist (nothing changed).
        """
        changes = {task.id: task for task in tasks}
        if any(not self.contains(task_id) for task_id in changes):
            return DataResult.fail(_not_found())
        return DataResult.ok(self._with_items(changes.get(task.id, task) for task in self))

    def without_all(self, task_ids: Collection[str]) -> DataResult[Self]:
        """Remove several tasks at once, all or nothing.

        Args:
            task_ids: Ids of the tasks to remove.

        Returns:
            The new collection, or ``ENTITY_NOT_FOUND`` when one of them does not exist (nothing changed).
        """
        if any(not self.contains(task_id) for task_id in task_ids):
            return DataResult.fail(_not_found())
        removed = set(task_ids)
        return DataResult.ok(self.filtered(lambda task: task.id not in removed))
