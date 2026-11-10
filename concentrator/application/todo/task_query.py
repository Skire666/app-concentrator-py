"""What the task table of one list shows."""

from dataclasses import dataclass

from concentrator.domain.todo.task_sort_key_enum import TaskSortKeyEnum
from concentrator.domain.todo.task_state_enum import TaskStateEnum


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskQuery:
    """Selection and order of the tasks of a list (``TodoQueries.tasks``).

    Attributes:
        list_id: List shown.
        show_done: Whether done tasks are shown (open tasks always are).
        show_archived: Whether archived tasks are shown.
        sort_key: Column the tasks are sorted by.
        descending: Highest values first.
    """

    list_id: str
    show_done: bool
    show_archived: bool
    sort_key: TaskSortKeyEnum
    descending: bool

    @property
    def states(self) -> frozenset[TaskStateEnum]:
        """States of the tasks shown."""
        states = {TaskStateEnum.OPEN}
        if self.show_done:
            states.add(TaskStateEnum.DONE)
        if self.show_archived:
            states.add(TaskStateEnum.ARCHIVED)
        return frozenset(states)
