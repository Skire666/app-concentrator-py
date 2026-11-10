"""Snapshot of the task table (``TODO_TABLE``)."""

from dataclasses import dataclass

from concentrator.presentation.common.table_snapshot import TableSnapshot
from concentrator.presentation.todo.task_menu_snapshot import TaskMenuSnapshot


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskTableSnapshot:
    """The table of the current list and its context menu.

    Attributes:
        table: Columns State (check box), Task, Due, Created, Updated; rows keyed by task id; the
            selected rows; the sort indicator.
        menu: The task actions of the context menu (same as the toolbar).
    """

    table: TableSnapshot
    menu: TaskMenuSnapshot
