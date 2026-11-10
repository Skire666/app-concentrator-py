"""Snapshot of the task toolbar (``TODO_TOOLBAR``)."""

from dataclasses import dataclass

from concentrator.presentation.common.button_snapshot import ButtonSnapshot
from concentrator.presentation.todo.task_menu_snapshot import TaskMenuSnapshot


@dataclass(frozen=True, slots=True, kw_only=True)
class TodoToolbarSnapshot:
    """Everything the toolbar shows.

    Attributes:
        menu: Task actions enabled from the selection, and the "Move to list" targets.
        show_done: "Show done" toggle (``checked``).
        show_archived: "Show archived" toggle (``checked``).
    """

    menu: TaskMenuSnapshot
    show_done: ButtonSnapshot
    show_archived: ButtonSnapshot
