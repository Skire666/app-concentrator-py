"""Snapshot of the task toolbar (``TODO_TOOLBAR``)."""

from dataclasses import dataclass

from concentrator.presentation.common.button_snapshot import ButtonSnapshot
from concentrator.presentation.todo.task_menu_snapshot import TaskMenuSnapshot


@dataclass(frozen=True, slots=True, kw_only=True)
class TodoToolbarSnapshot:
    """Everything the toolbar above the task table and the bar of toggles under it show.

    Attributes:
        menu: Task actions enabled from the selection, and the "Move to list" targets (toolbar).
        show_done: "Show done" toggle (``checked``), under the table.
        show_archived: "Show archived" toggle (``checked``), under the table.
    """

    menu: TaskMenuSnapshot
    show_done: ButtonSnapshot
    show_archived: ButtonSnapshot
