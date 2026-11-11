"""What the task table shows."""

from dataclasses import dataclass, field

from concentrator.application.todo.task_filter import TaskFilter
from concentrator.application.todo.task_scope_enum import TaskScopeEnum
from concentrator.domain.todo.task_sort_key_enum import TaskSortKeyEnum
from concentrator.domain.todo.task_state_enum import TaskStateEnum


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskQuery:
    """Selection and order of the tasks of the table (``TodoQueries.tasks``).

    Attributes:
        list_id: List shown (the tab).
        show_done: Whether done tasks are shown (open tasks always are).
        show_archived: Whether archived tasks are shown.
        sort_key: Column the tasks are sorted by.
        descending: Highest values first.
        task_filter: Due date filter and "Recurring only".
        scope: The tasks of ``list_id`` only, or of every list.
    """

    list_id: str
    show_done: bool
    show_archived: bool
    sort_key: TaskSortKeyEnum
    descending: bool
    task_filter: TaskFilter = field(default_factory=TaskFilter)
    scope: TaskScopeEnum = TaskScopeEnum.THIS_LIST

    @property
    def states(self) -> frozenset[TaskStateEnum]:
        """States of the tasks shown."""
        states = {TaskStateEnum.OPEN}
        if self.show_done:
            states.add(TaskStateEnum.DONE)
        if self.show_archived:
            states.add(TaskStateEnum.ARCHIVED)
        return frozenset(states)

    @property
    def all_lists(self) -> bool:
        """Whether the tasks of every list are shown."""
        return self.scope is TaskScopeEnum.ALL_LISTS
