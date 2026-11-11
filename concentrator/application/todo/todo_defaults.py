"""Values of the ``[todo]`` section used by the use cases, the read pipeline and the presentation."""

from dataclasses import dataclass
from typing import Self

from concentrator.application.common.app_config import TodoSection
from concentrator.domain.todo.priority_enum import PriorityEnum
from concentrator.domain.todo.task_sort_key_enum import TaskSortKeyEnum
from concentrator.domain.todo.todo_limits import TodoLimits


@dataclass(frozen=True, slots=True, kw_only=True)
class TodoDefaults:
    """Limits and defaults of the TODO manager.

    Attributes:
        limits: Bounds applied by the domain rules.
        list_priority: Priority of a new list and of the first list of a file (Inbox).
        sort_key: Task table order until the user clicks a column.
        sort_descending: Direction of that order.
        table_ratio_percent: Initial height share of the task table above the details pane.
        column_widths_px: Initial widths of the state, due, created and updated columns.
        recurrence_preview_count: Dates shown after the due date in the preview of the task editor.
    """

    limits: TodoLimits
    list_priority: PriorityEnum
    sort_key: TaskSortKeyEnum
    sort_descending: bool
    table_ratio_percent: int
    column_widths_px: tuple[int, ...]
    recurrence_preview_count: int

    @classmethod
    def from_section(cls, section: TodoSection) -> Self:
        """Build the values from the ``[todo]`` section.

        Args:
            section: Loaded section.

        Returns:
            The defaults.
        """
        limits = TodoLimits(
            max_task_text_length=section.max_task_text_length,
            max_list_name_length=section.max_list_name_length,
            max_list_description_length=section.max_list_description_length,
            max_history_events=section.max_history_events,
            max_recurrence_interval=section.max_recurrence_interval,
            max_recurrence_count=section.max_recurrence_count,
        )
        return cls(
            limits=limits,
            list_priority=section.default_list_priority,
            sort_key=section.default_sort,
            sort_descending=section.default_sort_descending,
            table_ratio_percent=section.default_table_ratio_percent,
            column_widths_px=section.default_column_widths_px,
            recurrence_preview_count=section.recurrence_preview_count,
        )
