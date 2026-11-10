"""Task actions shown by the toolbar and by the context menu of the table."""

from dataclasses import dataclass

from concentrator.presentation.common.button_snapshot import ButtonSnapshot


@dataclass(frozen=True, slots=True, kw_only=True)
class MoveTargetSnapshot:
    """One entry of the "Move to list" menu.

    Attributes:
        list_id: Target list sent back with ``TASK_MOVE``.
        text: Name of the list.
        enabled: Whether the selected tasks can move there.
    """

    list_id: str
    text: str
    enabled: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskMenuSnapshot:
    """The task actions, enabled from the selection.

    Attributes:
        buttons: New, Edit, Done, Reopen, Archive, Unarchive, Duplicate, Move to list, Delete.
        move_targets: Other lists, for the "Move to list" menu.
    """

    buttons: tuple[ButtonSnapshot, ...]
    move_targets: tuple[MoveTargetSnapshot, ...]
